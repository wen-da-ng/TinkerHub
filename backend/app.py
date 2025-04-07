import asyncio
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import tempfile

from mcp.context import Context, MessageRole, Message
from mcp.providers import ProviderFactory
from mcp.utils import truncate_context_if_needed
from mcp.memory import ConversationMemory, generate_conversation_summary, extract_key_facts

from document_processing.loaders import load_documents, Document
from document_processing.splitters import CharacterTextSplitter
from document_processing.store import DocumentStore

from retrieval.embeddings import get_embedding_generator
from retrieval.vectordb import get_vector_database, InMemoryVectorDB

from code_interpreter.generator import generate_analysis_code, explain_analysis_results, fix_code_errors
from code_interpreter.executor import execute_code, install_packages

from data_preprocessing.normalizer import preprocess_data_file

from retrieval_enhancement.query_enhancer import rewrite_query, generate_hyde_document



# Initialize document store and vector database
document_store = DocumentStore()
embedding_generator = get_embedding_generator(embedding_type="dummy")  # Using dummy embeddings to avoid ONNX issues
vector_db = InMemoryVectorDB()  # Using in-memory DB to avoid ChromaDB issues

print("Using in-memory vector database for stability")

async def process_document(file_path: str) -> None:
    """Process a document and add it to the document store and vector database."""
    try:
        print(f"Loading document: {file_path}")
        
        # Load the document
        documents = load_documents(file_path)
        print(f"Loaded {len(documents)} document sections")
        
        # Split the document into chunks
        splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        split_documents = splitter.split_documents(documents)
        print(f"Split into {len(split_documents)} chunks")
        
        # Add to document store
        document_store.add_documents(split_documents)
        print(f"Added to document store. Total documents: {len(document_store.documents)}")
        
        # Generate embeddings
        texts = [doc.content for doc in split_documents]
        metadatas = [doc.metadata for doc in split_documents]
        print("Generating embeddings...")
        
        try:
            embeddings = embedding_generator.generate(texts, metadatas)
            print(f"Generated {len(embeddings)} embeddings")
            
            # Add to vector database
            print("Adding embeddings to vector database...")
            vector_db.add_embeddings(embeddings)
            print("Successfully added embeddings to vector database")
        except Exception as e:
            print(f"Error during embedding or database operations: {e}")
            import traceback
            traceback.print_exc()
        
        # Print the first chunk for verification
        if split_documents:
            print("\nFirst chunk sample:")
            print("-" * 40)
            print(split_documents[0].content[:200] + "..." if len(split_documents[0].content) > 200 else split_documents[0].content)
            print("-" * 40)
        
        print("Document processing complete!")
        return True
    except Exception as e:
        print(f"Error processing document: {e}")
        import traceback
        traceback.print_exc()
        return False


async def list_documents() -> None:
    """List all documents in the store."""
    if not document_store.documents:
        print("No documents in store")
        return
    
    # Group documents by source
    sources = {}
    for doc in document_store.documents:
        source = doc.metadata.get("source", "unknown")
        if source not in sources:
            sources[source] = 0
        sources[source] += 1
    
    print("\nDocuments in store:")
    print("-" * 40)
    for source, count in sources.items():
        print(f"{Path(source).name}: {count} chunks")
    print("-" * 40)


def retrieve_relevant_documents(query: str, top_k: int = 5) -> List[str]:
    """Retrieve documents relevant to the query using vector search."""
    if not document_store.documents:
        return []
        
    try:
        # Search vector database
        search_results = vector_db.search(query, embedding_generator, top_k=top_k)
        
        # Format results
        relevant_docs = []
        for result in search_results:
            text = result["text"]
            metadata = result["metadata"]
            source = metadata.get("source", "unknown")
            filename = Path(source).name
            
            # Format document with metadata
            doc_info = f"Document: {filename}\n"
            
            # Add additional metadata if available
            if "page" in metadata:
                doc_info += f"Page: {metadata['page']}\n"
            if "chunk" in metadata:
                doc_info += f"Chunk: {metadata['chunk']}/{metadata.get('chunk_of', '?')}\n"
            
            # Add the content
            doc_info += f"{text}\n\n"
            
            relevant_docs.append(doc_info)
        
        return relevant_docs
    except Exception as e:
        print(f"Error during document retrieval: {e}")
        # In case of error, return empty list
        return []


def retrieve_complete_document(document_name: str) -> List[str]:
    """Retrieve all chunks of a specific document."""
    matching_docs = []
    
    for doc in document_store.documents:
        source = doc.metadata.get("source", "unknown")
        filename = Path(source).name.lower()
        
        # Check if this document matches the requested name
        if document_name.lower() in filename:
            # Format document information
            doc_info = f"Document: {Path(source).name}\n"
            if "page" in doc.metadata:
                doc_info += f"Page: {doc.metadata['page']}\n"
            if "chunk" in doc.metadata:
                doc_info += f"Chunk: {doc.metadata['chunk']}/{doc.metadata.get('chunk_of', '?')}\n"
            doc_info += f"{doc.content}\n\n"
            matching_docs.append(doc_info)
    
    return matching_docs

async def analyze_with_code(provider, data_filepath: str, analysis_question: str, max_attempts: int = 5) -> str:
    """Analyze document using code generation and execution."""
    attempt = 0
    installed_packages = []
    last_output = ""
    
    # Read a sample of the data file for the LLM
    with open(data_filepath, 'r') as f:
        data_sample = f.read(2000)  # Read first 2000 chars as sample
    
    print(f"\nData file: {data_filepath}")
    print(f"Data sample:\n{data_sample[:500]}...\n")
    
    while attempt < max_attempts:
        attempt += 1
        print(f"\nAttempt {attempt} of {max_attempts}")
        
        # Generate code that reads from the file
        if attempt == 1:
            # First attempt - generate initial code
            code = await generate_analysis_code(provider, data_sample, data_filepath, analysis_question)
        else:
            # Subsequent attempts - fix the code based on previous error
            print(f"Fixing code based on previous error...")
            code = await fix_code_errors(
                provider, 
                code, 
                last_output, 
                analysis_question,
                data_filepath,  # Pass the file path to the fix function 
                missing_packages
            )
        
        print(f"\nGenerated code (attempt {attempt}):")
        print("-" * 40)
        print(code)
        print("-" * 40)
        
        # Execute code with access to the data file
        success, output, missing_packages = execute_code(code)
        last_output = output  # Store the output for potential next attempt
        
        if success:
            # Code executed successfully
            print("Code execution successful!")
            
            # Generate explanation of results
            explanation = await explain_analysis_results(provider, analysis_question, output)
            
            # Return the complete analysis
            return (
                f"{explanation}\n\n"
                f"**Technical Details**\n\n"
                f"```python\n{code}\n```\n\n"
                f"```\n{output}\n```"
            )
        
        elif missing_packages:
            # Missing packages detected
            packages_to_install = [p for p in missing_packages if p not in installed_packages]
            
            if packages_to_install:
                print(f"Installing missing packages: {', '.join(packages_to_install)}")
                install_success, install_message = install_packages(packages_to_install)
                
                if install_success:
                    print(install_message)
                    installed_packages.extend(packages_to_install)
                    # Continue to next attempt with packages installed
                    continue
                else:
                    print(f"Package installation failed: {install_message}")
        
        # If we reach here, execution failed - print the error and continue the loop
        print(f"Code execution failed: {output}")
        # The loop will continue to the next attempt
    
    # If we've reached max attempts without success
    return (
        "I wasn't able to generate working code to analyze this data after "
        f"{max_attempts} attempts. Here's the last error encountered:\n\n"
        f"```\n{last_output}\n```\n\n"
        "You might try rephrasing your question or providing the data in a different format."
    )

async def main():
    print("MCP-based Chatbot with Ollama")
    print("Type 'exit' to quit")
    print("Commands:")
    print("  /load <file_path> - Load a document")
    print("  /list - List loaded documents")
    print("  /analyze <document_name> - Analyze a complete document")
    print("  /analyze_with_code <document_name> - Analyze using generated Python code")
    print("  /memory - Show memory status")
    print("  /recall <topic> - Recall information about a topic")
    print("  /summary - Show latest conversation summary")
    print("  /help - Show this help message")
    print()
    
    # Initialize context with base system prompt
    base_system_prompt = "You are a helpful assistant. Provide clear and concise answers."
    context = Context(system_prompt=base_system_prompt)
    
    # Create provider
    provider = ProviderFactory.create_provider(
        "ollama", 
        model="gemma3:12b"
    )
    
    # Initialize memory
    memory = ConversationMemory(max_short_term_messages=20)
    message_count = 0
    
    # Main chat loop
    while True:
        try:
            # Get user input
            user_input = input("\nYou: ")
            
            # Check for commands
            if user_input.lower() in ["exit", "quit"]:
                break
            elif user_input.lower() == "/help":
                print("\nCommands:")
                print("  /load <file_path> - Load a document")
                print("  /list - List loaded documents")
                print("  /analyze <document_name> - Analyze a complete document")
                print("  /analyze_with_code <document_name> - Analyze using generated Python code")
                print("  /memory - Show memory status")
                print("  /recall <topic> - Recall information about a topic")
                print("  /summary - Show latest conversation summary")
                print("  /help - Show this help message")
                continue
            elif user_input.lower().startswith("/load "):
                file_path = user_input[6:].strip()
                await process_document(file_path)
                continue
            elif user_input.lower() == "/list":
                await list_documents()
                continue
            elif user_input.lower().startswith("/analyze "):
                # Extract document name from command
                doc_name = user_input[9:].strip()
                print(f"Retrieving all chunks of document: {doc_name}")
                
                # Get all chunks of the specified document
                complete_doc = retrieve_complete_document(doc_name)
                
                if not complete_doc:
                    print(f"No document matching '{doc_name}' found.")
                    continue
                
                print(f"Retrieved {len(complete_doc)} chunks. Sending for analysis...")
                
                # Get user's analysis question
                print("\nWhat specific analysis would you like on this document?")
                analysis_question = input("Analysis question: ")
                
                # Create context with complete document
                analysis_context = Context(
                    system_prompt=(
                        f"{base_system_prompt}\n\n"
                        f"You have access to the complete document '{doc_name}'. "
                        f"Analyze it thoroughly to answer the user's question.\n\n"
                        f"{''.join(complete_doc)}"
                    )
                )
                
                # Add analysis question
                analysis_context.add_message(
                    MessageRole.USER, 
                    analysis_question
                )
                
                # Generate response
                print("\nAssistant: ", end="")
                response = await provider.generate_response(analysis_context)
                print(response)

                # Add to conversation history
                context.add_message(MessageRole.USER, f"Analyze {doc_name} with this question: {analysis_question}")
                context.add_message(MessageRole.ASSISTANT, response)
                
                # Add to memory system
                user_message = Message(role=MessageRole.USER, content=f"Analyze {doc_name} with this question: {analysis_question}")
                assistant_message = Message(role=MessageRole.ASSISTANT, content=response)
                memory.add_message(user_message)
                memory.add_message(assistant_message)
                message_count += 2
                
                # Extract facts from both messages in background
                asyncio.create_task(process_facts_in_background(provider, memory, user_message))
                asyncio.create_task(process_facts_in_background(provider, memory, assistant_message))
                
                continue
            
            elif user_input.lower().startswith("/analyze_with_code "):
                # Extract document name from command
                doc_name = user_input[19:].strip()
                print(f"Retrieving all chunks of document: {doc_name}")
                
                # Get all chunks of the specified document
                complete_doc = retrieve_complete_document(doc_name)
                
                if not complete_doc:
                    print(f"No document matching '{doc_name}' found.")
                    continue
                
                print(f"Retrieved {len(complete_doc)} chunks for code analysis...")
                
                # Get user's analysis question
                print("\nWhat specific analysis would you like on this document?")
                analysis_question = input("Analysis question: ")
                
                # Create a temporary data file containing the document content
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_data_file:
                    for chunk in complete_doc:
                        temp_data_file.write(chunk)
                    data_filepath = temp_data_file.name
                
                print(f"\nCreated temporary data file: {data_filepath}")
                
                # Pass file location to analyze_with_code
                print("\nAnalyzing with code generation and execution...")
                result = await analyze_with_code(provider, data_filepath, analysis_question)
                
                # Clean up
                try:
                    os.unlink(data_filepath)
                except:
                    pass
                
                # Display results
                print("\nAssistant: ")
                print(result)

                # Add the analysis to the conversation history
                context.add_message(MessageRole.USER, f"Analyze {doc_name} with this question: {analysis_question}")
                context.add_message(MessageRole.ASSISTANT, result)
                
                # Add to memory system
                user_message = Message(role=MessageRole.USER, content=f"Analyze {doc_name} with this question: {analysis_question}")
                assistant_message = Message(role=MessageRole.ASSISTANT, content=result)
                memory.add_message(user_message)
                memory.add_message(assistant_message)
                message_count += 2
                
                # Extract facts from both messages in background
                asyncio.create_task(process_facts_in_background(provider, memory, user_message))
                asyncio.create_task(process_facts_in_background(provider, memory, assistant_message))
                
                continue
            
            elif user_input.lower() == "/memory":
                print("\nMemory Status:")
                print(f"Short-term memory: {len(memory.short_term_memory)} messages")
                print(f"Long-term memory topics: {list(memory.long_term_memory.keys())}")
                print(f"Conversation summaries: {len(memory.summaries)}")
                continue
            elif user_input.lower().startswith("/recall "):
                topic = user_input[8:].strip()
                if topic in memory.long_term_memory:
                    print(f"\nRecalled information about '{topic}':")
                    for i, info in enumerate(memory.long_term_memory[topic], 1):
                        print(f"{i}. {info}")
                else:
                    print(f"\nNo information about '{topic}' in long-term memory.")
                continue
            elif user_input.lower() == "/summary":
                if memory.summaries:
                    print("\nLatest conversation summary:")
                    print(memory.summaries[-1])
                else:
                    print("\nNo conversation summaries available yet.")
                continue
            
            # Create user message and add to memory
            user_message = Message(role=MessageRole.USER, content=user_input)
            memory.add_message(user_message)
            message_count += 1
            
            # Extract facts from user message (in background to not slow down response)
            asyncio.create_task(process_facts_in_background(provider, memory, user_message))
            
            # Check if we should create a summary (every 10 messages)
            if message_count % 3 == 0:
                # Schedule summary generation in background
                asyncio.create_task(generate_summary_in_background(provider, memory))
                
            # Check if documents are loaded and update system prompt accordingly
            current_system_prompt = base_system_prompt
            if document_store.documents:
                # Enhance the query for better retrieval
                print("Enhancing query for better retrieval...")
                
                try:
                    # Use query rewriting to expand the query
                    enhanced_query = await rewrite_query(provider, user_input, "expansion")
                    print(f"Enhanced query: {enhanced_query}")
                    
                    # Option: Use HyDE approach 
                    # hyde_document = await generate_hyde_document(provider, user_input)
                    # print(f"Generated HyDE document for retrieval")
                    
                    # Retrieve documents using the enhanced query
                    relevant_docs = retrieve_relevant_documents(enhanced_query, top_k=3)
                    
                    # Alternative: HyDE approach
                    # relevant_docs = retrieve_relevant_documents(hyde_document, top_k=3)
                except Exception as e:
                    print(f"Error enhancing query: {e}. Using original query.")
                    relevant_docs = retrieve_relevant_documents(user_input, top_k=3)
                
                if relevant_docs:
                    # Create a new context with updated system prompt that includes document info
                    current_system_prompt = (
                        f"{base_system_prompt}\n\n"
                        f"You have access to the following documents that may be relevant to the user's question: "
                        f"\"{user_input}\"\n\n"
                        f"{' '.join(relevant_docs)}"
                    )
            
            # Get relevant context from memory
            memory_context = memory.get_context_for_query(user_input)
            
            # Create a new context with the current system prompt
            augmented_context = Context(system_prompt=current_system_prompt)
            
            # Add memory context messages
            for msg in memory_context:
                augmented_context.add_message(msg.role, msg.content, **msg.metadata)
            
            # Add current user message
            augmented_context.add_message(MessageRole.USER, user_input)
            
            # Truncate context if needed to fit within token limit
            optimized_context = truncate_context_if_needed(augmented_context)
            
            # Generate response
            print("\nAssistant: ", end="")
            response = await provider.generate_response(optimized_context)
            
            # Create assistant message and add to memory
            assistant_message = Message(role=MessageRole.ASSISTANT, content=response)
            memory.add_message(assistant_message)
            
            # Extract facts from assistant response in background
            asyncio.create_task(process_facts_in_background(provider, memory, assistant_message))
            
            # Also add to the regular context for backward compatibility
            context.add_message(MessageRole.USER, user_input)
            context.add_message(MessageRole.ASSISTANT, response)
            
        except Exception as e:
            print(f"Error during conversation: {e}")
            print("Please try again.")


async def process_facts_in_background(provider, memory, message):
    """Extract and store facts from messages in the background."""
    facts = await extract_key_facts(provider, message)
    for topic, fact_list in facts.items():
        for fact in fact_list:
            memory.add_to_long_term(topic, fact)


async def generate_summary_in_background(provider, memory):
    """Generate a conversation summary in the background."""
    summary = await generate_conversation_summary(provider, memory.short_term_memory)
    memory.add_summary(summary)


if __name__ == "__main__":
    asyncio.run(main())