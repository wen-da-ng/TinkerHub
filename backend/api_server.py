import asyncio
import os
from pathlib import Path
import re
import tempfile
import json
from typing import List, Dict, Any, Optional
import threading
import uuid
import pickle
import logging
import traceback
import requests

from flask import Flask, request, jsonify, Response
from flask_cors import CORS

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

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize chat components
document_store = DocumentStore()
embedding_generator = get_embedding_generator(embedding_type="dummy")
vector_db = InMemoryVectorDB()
base_system_prompt = "You are a helpful assistant. Provide clear and concise answers."

# Store user sessions
sessions = {}
responses = {}

RESPONSES_FILE = os.path.join(tempfile.gettempdir(), "mcp_responses.pkl")

# Load existing responses if available
try:
    if os.path.exists(RESPONSES_FILE):
        with open(RESPONSES_FILE, 'rb') as f:
            responses = pickle.load(f)
    else:
        responses = {}
except:
    responses = {}
    
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mcp_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_or_create_session(session_id):
    """Get existing session or create a new one"""
    if session_id not in sessions:
        default_model = "gemma3:12b"
        provider = ProviderFactory.create_provider("ollama", model=default_model)
        sessions[session_id] = {
            "memory": ConversationMemory(max_short_term_messages=20),
            "provider": provider,
            "context": Context(system_prompt=base_system_prompt),
            "message_count": 0,
            "uploaded_files": {},
            "model": default_model
        }
    return sessions[session_id]

# Background task handling
async def process_facts_in_background(provider, memory, message):
    """Extract and store facts from messages in the background."""
    try:
        logger.info(f"Starting fact extraction for message: {message.content[:50]}...")
        facts = await extract_key_facts(provider, message)
        
        if not facts:
            logger.info("No facts extracted from message")
            return
            
        logger.info(f"Extracted {sum(len(v) for v in facts.values())} facts across {len(facts)} topics")
        
        for topic, fact_list in facts.items():
            for fact in fact_list:
                memory.add_to_long_term(topic, fact)
                logger.info(f"Added fact to memory: {topic} - {fact}")
    except Exception as e:
        logger.error(f"Error in fact extraction: {e}")
        logger.error(traceback.format_exc())

async def generate_summary_in_background(provider, memory):
    """Generate a conversation summary in the background."""
    try:
        logger.info("Starting summary generation...")
        summary = await generate_conversation_summary(provider, memory.short_term_memory)
        
        if not summary:
            logger.warning("Generated empty summary")
            return
            
        memory.add_summary(summary)
        logger.info(f"Added summary to memory: {summary[:100]}...")
    except Exception as e:
        logger.error(f"Error in summary generation: {e}")
        logger.error(traceback.format_exc())

# Document processing routes
@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file uploads"""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    session_id = request.form.get('session_id', 'default')
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Save the file temporarily
    temp_dir = os.path.join(tempfile.gettempdir(), "mcp_chatbot")
    os.makedirs(temp_dir, exist_ok=True)
    
    file_path = os.path.join(temp_dir, file.filename)
    file.save(file_path)
    
    # Store the file path in session
    session = get_or_create_session(session_id)
    file_id = str(uuid.uuid4())
    session["uploaded_files"][file_id] = {
        "path": file_path,
        "name": file.filename,
        "processed": False
    }
    
    # Start processing in background
    threading.Thread(
        target=lambda: asyncio.run(process_document(file_path, session_id, file_id))
    ).start()
    
    return jsonify({
        "success": True,
        "file_id": file_id,
        "filename": file.filename,
        "message": "File uploaded successfully. Processing started."
    })

async def process_document(file_path, session_id, file_id):
    """Process a document and add it to the document store and vector database."""
    try:
        print(f"Loading document: {file_path}")
        
        # Load the document
        documents = load_documents(file_path)
        
        # Split the document into chunks
        splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        split_documents = splitter.split_documents(documents)
        
        # Add to document store
        document_store.add_documents(split_documents)
        
        # Generate embeddings
        texts = [doc.content for doc in split_documents]
        metadatas = [doc.metadata for doc in split_documents]
        
        embeddings = embedding_generator.generate(texts, metadatas)
        
        # Add to vector database
        vector_db.add_embeddings(embeddings)
        
        # Mark as processed
        session = sessions.get(session_id)
        if session and file_id in session["uploaded_files"]:
            session["uploaded_files"][file_id]["processed"] = True
            
        print(f"Document {file_path} processing complete!")
        return True
    except Exception as e:
        print(f"Error processing document: {e}")
        import traceback
        traceback.print_exc()
        return False
    
async def analyze_with_code(provider, data_filepath: str, analysis_question: str, max_attempts: int = 5) -> str:
    """Analyze document using code generation and execution."""
    attempt = 0
    installed_packages = []
    last_output = ""
    
    # Read a sample of the data file for the LLM
    try:
        with open(data_filepath, 'r', encoding='utf-8') as f:
            data_sample = f.read(2000)  # Read first 2000 chars as sample
    except Exception as e:
        logger.error(f"Error reading data file: {e}")
        data_sample = f"Error reading file: {str(e)}"
    
    logger.info(f"\nData file: {data_filepath}")
    logger.info(f"Data sample length: {len(data_sample)}")
    
    while attempt < max_attempts:
        attempt += 1
        logger.info(f"\nAttempt {attempt} of {max_attempts}")
        
        # Generate code that reads from the file
        if attempt == 1:
            # First attempt - generate initial code
            code = await generate_analysis_code(provider, data_sample, data_filepath, analysis_question)
        else:
            # Subsequent attempts - fix the code based on previous error
            logger.info(f"Fixing code based on previous error...")
            code = await fix_code_errors(
                provider, 
                code, 
                last_output, 
                analysis_question,
                data_filepath,  # Pass the file path to the fix function 
                missing_packages
            )
        
        logger.info(f"\nGenerated code (attempt {attempt}):")
        logger.info("-" * 40)
        logger.info(code)
        logger.info("-" * 40)
        
        # Execute code with access to the data file
        success, output, missing_packages = execute_code(code)
        last_output = output  # Store the output for potential next attempt
        
        if success:
            # Code executed successfully
            logger.info("Code execution successful!")
            
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
                logger.info(f"Installing missing packages: {', '.join(packages_to_install)}")
                install_success, install_message = install_packages(packages_to_install)
                
                if install_success:
                    logger.info(install_message)
                    installed_packages.extend(packages_to_install)
                    # Continue to next attempt with packages installed
                    continue
                else:
                    logger.error(f"Package installation failed: {install_message}")
        
        # If we reach here, execution failed - print the error and continue the loop
        logger.error(f"Code execution failed: {output}")
        # The loop will continue to the next attempt
    
    # If we've reached max attempts without success
    return (
        "I wasn't able to generate working code to analyze this data after "
        f"{max_attempts} attempts. Here's the last error encountered:\n\n"
        f"```\n{last_output}\n```\n\n"
        "You might try rephrasing your question or providing the data in a different format."
    )

@app.route('/api/files', methods=['GET'])
def list_files():
    """List all uploaded files for a session"""
    session_id = request.args.get('session_id', 'default')
    session = get_or_create_session(session_id)
    
    files = []
    for file_id, file_info in session["uploaded_files"].items():
        files.append({
            "id": file_id,
            "name": file_info["name"],
            "processed": file_info["processed"]
        })
    
    return jsonify({"files": files})

# Chat routes
@app.route('/api/chat', methods=['POST'])
def chat():
    """Process a chat message"""
    data = request.json
    message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    enhance_query = data.get('enhance_query', True)  # Default to True for backward compatibility
    
    # Generate a message ID
    message_id = str(uuid.uuid4())
    
    # Store an empty response
    responses[message_id] = {
        'status': 'processing',
        'response': None
    }
    
    # Start a new thread for async processing
    threading.Thread(
        target=lambda: process_chat_message_background(message, session_id, message_id, enhance_query)
    ).start()
    
    # Return an immediate response with message ID
    return jsonify({
        'success': True,
        'message': 'Message received, processing started',
        'message_id': message_id
    })

def save_response(message_id, response_data):
    responses[message_id] = response_data
    try:
        with open(RESPONSES_FILE, 'wb') as f:
            pickle.dump(responses, f)
    except Exception as e:
        print(f"Error saving responses: {e}")

# Modify your @app.route('/api/response') function
@app.route('/api/response', methods=['GET'])
def get_response():
    """Get a response by message ID"""
    message_id = request.args.get('message_id')
    
    if not message_id:
        return jsonify({
            'status': 'error',
            'message': 'Missing message ID'
        }), 400
    
    # Try to get from memory first
    if message_id in responses:
        return jsonify(responses[message_id])
    
    # If not in memory, try to load from disk
    try:
        if os.path.exists(RESPONSES_FILE):
            with open(RESPONSES_FILE, 'rb') as f:
                saved_responses = pickle.load(f)
                if message_id in saved_responses:
                    # Update in-memory cache
                    responses[message_id] = saved_responses[message_id]
                    return jsonify(saved_responses[message_id])
    except Exception as e:
        print(f"Error loading saved responses: {e}")
    
    return jsonify({
        'status': 'error',
        'message': 'Response not found'
    }), 404

def process_chat_message_background(message, session_id, message_id, enhance_query=True):
    """Process a chat message in the background"""
    try:
        session = get_or_create_session(session_id)
        memory = session["memory"]
        provider = session["provider"]
        context = session["context"]
        
        # Multi-file analysis command
        if message.startswith("/analyze_multi "):
            # Extract filenames and question
            parts = message.split("\n", 1)
            files_part = parts[0][14:].strip()
            filenames = files_part.split("|")
            
            # Get the question part
            question = parts[1].replace("Question: ", "") if len(parts) > 1 else "Analyze these documents."
            
            try:
                # Create a new event loop just for this task
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Run the analysis
                result = loop.run_until_complete(analyze_multiple_documents(provider, filenames, question))
                loop.close()
                
                # Update status
                response_data = {
                    'status': 'completed',
                    'response': result
                }
                responses[message_id] = response_data
                if 'save_response' in globals():
                    save_response(message_id, response_data)
                
                # Add to memory
                user_message = Message(role=MessageRole.USER, content=message)
                assistant_message = Message(role=MessageRole.ASSISTANT, content=result)
                memory.add_message(user_message)
                memory.add_message(assistant_message)
                
            except Exception as e:
                logger.error(f"Error in multi-file analysis: {e}")
                logger.error(traceback.format_exc())
                responses[message_id] = {
                    'status': 'error',
                    'response': f"Error analyzing multiple documents: {str(e)}"
                }
                if 'save_response' in globals():
                    save_response(message_id, responses[message_id])
            
            return
        
        elif message.startswith("/deep_analyze "):
            # Extract document name and question
            parts = message.split("\n", 1)
            doc_name = parts[0][14:].strip()
            
            # Get the question part
            question = parts[1].replace("Question: ", "") if len(parts) > 1 else "Analyze this document thoroughly."
            
            try:
                # Create a new event loop just for this task
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Run the hierarchical analysis
                result = loop.run_until_complete(analyze_hierarchical(provider, doc_name, question))
                loop.close()
                
                # Update status
                response_data = {
                    'status': 'completed',
                    'response': result
                }
                responses[message_id] = response_data
                if 'save_response' in globals():
                    save_response(message_id, response_data)
                
                # Add to memory
                user_message = Message(role=MessageRole.USER, content=message)
                assistant_message = Message(role=MessageRole.ASSISTANT, content=result)
                memory.add_message(user_message)
                memory.add_message(assistant_message)
                
            except Exception as e:
                logger.error(f"Error in deep document analysis: {e}")
                logger.error(traceback.format_exc())
                responses[message_id] = {
                    'status': 'error',
                    'response': f"Error performing deep analysis: {str(e)}"
                }
                if 'save_response' in globals():
                    save_response(message_id, responses[message_id])
            
            return
            
        elif message.startswith("/analyze_multi_code "):
            # Extract filenames and question
            parts = message.split("\n", 1)
            files_part = parts[0][19:].strip()
            filenames = files_part.split("|")
            
            # Get the question part
            question = parts[1].replace("Question: ", "") if len(parts) > 1 else "Analyze these documents with code."
            
            try:
                # Use the improved code-based multi-document analysis
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(analyze_multiple_documents_with_code(provider, filenames, question))
                
                # Update status
                response_data = {
                    'status': 'completed',
                    'response': result
                }
                responses[message_id] = response_data
                save_response(message_id, response_data)
                
                # Add to memory
                user_message = Message(role=MessageRole.USER, content=message)
                assistant_message = Message(role=MessageRole.ASSISTANT, content=result)
                memory.add_message(user_message)
                memory.add_message(assistant_message)
            except Exception as e:
                logger.error(f"Error in multi-file code analysis: {e}")
                logger.error(traceback.format_exc())
                responses[message_id] = {
                    'status': 'error',
                    'response': f"Error analyzing multiple documents with code: {str(e)}"
                }
                save_response(message_id, responses[message_id])
            
            return
            
        # Create user message and add to memory
        user_message = Message(role=MessageRole.USER, content=message)
        memory.add_message(user_message)
        session["message_count"] += 1
        
        # Check if documents are loaded
        current_system_prompt = base_system_prompt
        if document_store.documents:
            try:
                # Only enhance the query if the feature is enabled
                if enhance_query:
                    # Convert async to sync for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    enhanced_query = loop.run_until_complete(rewrite_query(provider, message, "expansion"))
                    relevant_docs = retrieve_relevant_documents(enhanced_query, top_k=3)
                    logger.info(f"Query enhanced: {message} -> {enhanced_query}")
                else:
                    # Use the original query without enhancement
                    relevant_docs = retrieve_relevant_documents(message, top_k=3)
                    logger.info("Using original query without enhancement")
                
                if relevant_docs:
                    current_system_prompt = (
                        f"{base_system_prompt}\n\n"
                        f"You have access to the following documents that may be relevant to the user's question: "
                        f"\"{message}\"\n\n"
                        f"{' '.join(relevant_docs)}"
                    )
            except Exception as e:
                logger.error(f"Error enhancing query: {e}. Using original query.")
                relevant_docs = retrieve_relevant_documents(message, top_k=3)
        
        # Get relevant context from memory
        memory_context = memory.get_context_for_query(message)
        
        # Create a new context with the current system prompt
        augmented_context = Context(system_prompt=current_system_prompt)
        
        # Add memory context messages
        for msg in memory_context:
            augmented_context.add_message(msg.role, msg.content, **msg.metadata)
        
        # Add current user message
        augmented_context.add_message(MessageRole.USER, message)
        
        # Truncate context if needed to fit within token limit
        optimized_context = truncate_context_if_needed(augmented_context)
        
        # Generate response
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(provider.generate_response(optimized_context))
        
        # Add to memory
        assistant_message = Message(role=MessageRole.ASSISTANT, content=response)
        memory.add_message(assistant_message)
        
        # Update context
        context.add_message(MessageRole.USER, message)
        context.add_message(MessageRole.ASSISTANT, response)
        
        # Store the completed response
        responses[message_id] = {
            'status': 'completed',
            'response': response
        }
        
        # Background processing
                
        try:
            # Process facts from user message
            logger.info("Processing facts from user message")
            loop.run_until_complete(process_facts_in_background(provider, memory, user_message))
            
            # Process facts from assistant message
            logger.info("Processing facts from assistant message")
            loop.run_until_complete(process_facts_in_background(provider, memory, assistant_message))
            
            # Generate summary every 2 messages
            if session["message_count"] % 2 == 0:
                logger.info(f"Generating summary (message count: {session['message_count']})")
                loop.run_until_complete(generate_summary_in_background(provider, memory))
        except Exception as e:
            logger.error(f"Error in background tasks: {e}")
            logger.error(traceback.format_exc())
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error processing message: {e}")
        
        # Store the error response
        responses[message_id] = {
            'status': 'error',
            'response': f"Sorry, I encountered an error: {str(e)}"
        }

# Helper functions
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
        return []

def retrieve_complete_document(document_name: str) -> List[str]:
    """Retrieve all chunks of a specific document."""
    matching_docs = []
    
    for doc in document_store.documents:
        source = doc.metadata.get("source", "unknown")
        filename = Path(source).name.lower()
        
        if document_name.lower() in filename:
            doc_info = f"Document: {Path(source).name}\n"
            if "page" in doc.metadata:
                doc_info += f"Page: {doc.metadata['page']}\n"
            if "chunk" in doc.metadata:
                doc_info += f"Chunk: {doc.metadata['chunk']}/{doc.metadata.get('chunk_of', '?')}\n"
            doc_info += f"{doc.content}\n\n"
            matching_docs.append(doc_info)
    
    return matching_docs

async def analyze_multiple_documents(provider, filenames: List[str], question: str) -> str:
    """Analyze multiple documents by using a multi-stage approach."""
    logger.info(f"Starting analysis of documents: {filenames}")
    
    # Step 1: Gather initial summaries of each document
    document_summaries = []
    for doc_name in filenames:
        complete_doc = retrieve_complete_document(doc_name)
        if complete_doc:
            # Create a summary of this document
            doc_content = "".join(complete_doc)
            
            # Limit the content to a reasonable size for summarization
            if len(doc_content) > 10000:  # If document is large
                doc_content = doc_content[:10000] + "...[content truncated for length]"
                
            summary_context = Context(
                system_prompt=(
                    "You are a document summarizer. Create a concise summary of the following document. "
                    "Focus on the key points and information that would be most relevant for analysis."
                )
            )
            summary_context.add_message(MessageRole.USER, f"Document: {doc_name}\n\n{doc_content}")
            
            # Use await directly - don't create another event loop
            summary = await provider.generate_response(summary_context)
            logger.info(f"Generated summary for document: {doc_name}")
            
            document_summaries.append({
                "name": doc_name,
                "summary": summary
            })
    
    # Step 2: Create a plan for analysis based on the question and document summaries
    plan_context = Context(
        system_prompt=(
            "You are an analysis planning expert. You need to create a plan for analyzing multiple documents "
            "to answer a user's question. Based on the document summaries provided, determine which documents "
            "are most relevant to the question and how they should be analyzed together."
        )
    )
    
    summaries_text = "\n\n".join([
        f"Document: {doc['name']}\nSummary: {doc['summary']}" for doc in document_summaries
    ])
    
    plan_context.add_message(
        MessageRole.USER,
        f"Question: {question}\n\nAvailable documents:\n{summaries_text}\n\n"
        f"Create a plan for how to analyze these documents to answer the question. "
        f"Identify which documents are most relevant and what specific information to look for."
    )
    
    # Use await directly - don't create another event loop
    analysis_plan = await provider.generate_response(plan_context)
    logger.info("Generated analysis plan")
    
    # Step 3: Perform the actual analysis based on the plan
    analysis_context = Context(
        system_prompt=(
            f"You are a document analysis expert. You have been given the following documents:\n"
            f"{', '.join(filenames)}.\n\n"
            f"You also have a plan for analyzing these documents to answer a specific question. "
            f"Follow this plan and provide a comprehensive analysis."
        )
    )
    
    # Include relevant document content based on the plan
    relevant_content = []
    for doc_name in filenames:
        complete_doc = retrieve_complete_document(doc_name)
        if complete_doc:
            doc_content = "".join(complete_doc)
            relevant_content.append(f"Document: {doc_name}\n\n{doc_content}")
    
    analysis_context.add_message(
        MessageRole.USER,
        f"Question: {question}\n\n"
        f"Analysis Plan:\n{analysis_plan}\n\n"
        f"Documents:\n\n{'==='*20}\n\n".join(relevant_content)
    )
    
    # Use await directly - don't create another event loop
    final_analysis = await provider.generate_response(analysis_context)
    logger.info("Generated final analysis")
    
    return f"# Multi-Document Analysis\n\n## Question\n{question}\n\n## Analysis\n{final_analysis}"

async def analyze_hierarchical(provider, document_name: str, question: str) -> str:
    """Analyze a document using a hierarchical approach"""
    logger.info(f"Starting hierarchical analysis of document: {document_name}")
    
    # Step 1: Retrieve all document chunks
    complete_doc_chunks = retrieve_complete_document(document_name)
    if not complete_doc_chunks:
        return f"No document matching '{document_name}' found."
    
    # Step 2: Create a high-level summary
    all_content = "".join(complete_doc_chunks)
    
    # For very large documents, summarize in chunks first
    summaries = []
    if len(all_content) > 20000:
        # Split into manageable chunks (e.g., ~10k characters)
        content_chunks = [all_content[i:i+10000] for i in range(0, len(all_content), 10000)]
        
        for i, chunk in enumerate(content_chunks):
            summary_context = Context(
                system_prompt="Summarize this document section concisely."
            )
            summary_context.add_message(
                MessageRole.USER, 
                f"Document section {i+1}/{len(content_chunks)}:\n\n{chunk}"
            )
            section_summary = await provider.generate_response(summary_context)
            summaries.append(section_summary)
            
        combined_summary = "\n\n".join(summaries)
    else:
        # Document is small enough, create a single summary
        summary_context = Context(
            system_prompt="Create a comprehensive summary of this document."
        )
        summary_context.add_message(MessageRole.USER, f"Document: {document_name}\n\n{all_content}")
        combined_summary = await provider.generate_response(summary_context)
    
    # Step 3: Use RAG to retrieve relevant sections based on question
    enhanced_query = await rewrite_query(provider, question, "expansion")
    relevant_chunks = retrieve_relevant_documents(enhanced_query, top_k=5)
    
    # Step 4: Create a combined analysis with both the summary and relevant chunks
    analysis_context = Context(
        system_prompt=(
            f"You are analyzing document: {document_name}. "
            f"You have a comprehensive summary of the document AND specific relevant sections. "
            f"Use both to provide a complete and accurate analysis."
        )
    )
    
    analysis_context.add_message(
        MessageRole.USER,
        f"Question: {question}\n\n"
        f"Document Summary:\n{combined_summary}\n\n"
        f"Relevant Sections:\n{''.join(relevant_chunks)}\n\n"
        f"Please provide a comprehensive analysis that answers the question."
    )
    
    final_analysis = await provider.generate_response(analysis_context)
    
    return f"# Deep Document Analysis: {document_name}\n\n## Question\n{question}\n\n## Analysis\n{final_analysis}"

async def analyze_multiple_documents_with_code(provider, filenames: List[str], question: str) -> str:
    """Analyze multiple documents using code generation and execution."""
    logger.info(f"Starting multi-document code analysis with files: {filenames}")
    
    # Create a temporary directory for the analysis
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"Created temporary directory: {temp_dir}")
        
        # Simple approach: concatenate all docs into a single file
        # Each document section is clearly marked with headers
        combined_file_path = os.path.join(temp_dir, "combined_documents.txt")
        
        with open(combined_file_path, 'w', encoding='utf-8') as combined_file:
            # Write file metadata at the top
            combined_file.write(f"# Combined Document Analysis\n")
            combined_file.write(f"# Number of documents: {len(filenames)}\n")
            combined_file.write(f"# Analysis question: {question}\n")
            combined_file.write(f"# Document list: {', '.join(filenames)}\n\n")
            
            # Write each document with clear section markers
            for i, doc_name in enumerate(filenames):
                complete_doc = retrieve_complete_document(doc_name)
                if complete_doc:
                    doc_content = "".join(complete_doc)
                    
                    # Add clear section delimiter
                    combined_file.write(f"## DOCUMENT {i+1}: {doc_name}\n")
                    combined_file.write("=" * 80 + "\n\n")
                    combined_file.write(doc_content)
                    combined_file.write("\n\n" + "=" * 80 + "\n\n")
        
        logger.info(f"Created combined document file at {combined_file_path}")
        
        # Read a small sample to include in the instructions
        with open(combined_file_path, 'r', encoding='utf-8') as f:
            combined_sample = f.read(1000)  # First 1000 chars as sample
        
        # Create a clearer instruction for the code generation
        multi_file_question = (
            f"Analyze these {len(filenames)} documents to answer: {question}\n\n"
            f"The combined file contains all documents with clear headers and separators.\n"
            f"Each document is marked with '## DOCUMENT X: [filename]' and separated by '===='.\n\n"
            f"Your analysis should consider all documents together to answer the question."
        )
        
        # Use the existing analyze_with_code function which has proven more reliable
        # Just passing the combined file and our enhanced question
        return await analyze_with_code(provider, combined_file_path, multi_file_question)

@app.route('/api/test', methods=['GET'])
def test_api():
    """Test if the API is working"""
    return jsonify({
        'status': 'ok',
        'message': 'API is working properly'
    })

@app.route('/api/memory', methods=['GET'])
def get_memory():
    """Get memory status for a session"""
    session_id = request.args.get('session_id', 'default')
    session = get_or_create_session(session_id)
    memory = session["memory"]
    
    # Format memory data for the frontend
    memory_data = {
        "shortTermCount": len(memory.short_term_memory),
        "longTermTopics": list(memory.long_term_memory.keys()),
        "facts": memory.long_term_memory,
        "summaryCount": len(memory.summaries)
    }
    
    return jsonify(memory_data)

@app.route('/api/summary', methods=['GET'])
def get_summary():
    """Get the latest conversation summary"""
    session_id = request.args.get('session_id', 'default')
    session = get_or_create_session(session_id)
    memory = session["memory"]
    
    if memory.summaries:
        return jsonify({"summary": memory.summaries[-1]})
    else:
        return jsonify({"summary": ""})

@app.route('/api/debug/memory-diagnostics', methods=['GET'])
def memory_diagnostics():
    """Get diagnostic info about memory systems"""
    session_id = request.args.get('session_id', 'default')
    session = get_or_create_session(session_id)
    memory = session["memory"]
    
    # Get raw extraction example
    raw_extraction = None
    if memory.short_term_memory:
        last_message = memory.short_term_memory[-1]
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            provider = session["provider"]
            
            # Create specialized system prompt
            from mcp.context import Context, MessageRole
            context = Context(
                system_prompt=(
                    "You are a fact extraction specialist. Return a JSON object with topics "
                    "and facts from the message. Format: {\"topic1\": [\"fact1\"], \"topic2\": [\"fact2\"]}"
                )
            )
            context.add_message(
                MessageRole.USER,
                f"Extract facts from: {last_message.content[:200]}"
            )
            
            # Get raw response
            raw_extraction = loop.run_until_complete(provider.generate_response(context))
        except Exception as e:
            raw_extraction = f"Error: {str(e)}"
    
    diagnostic_data = {
        "short_term_count": len(memory.short_term_memory),
        "long_term_topics": list(memory.long_term_memory.keys()),
        "long_term_facts": {k: v for k, v in memory.long_term_memory.items()},
        "summaries_count": len(memory.summaries),
        "latest_summary": memory.summaries[-1] if memory.summaries else None,
        "raw_extraction_example": raw_extraction
    }
    
    return jsonify(diagnostic_data)

@app.route('/api/models', methods=['GET'])
def get_models():
    """Get a list of available Ollama models"""
    try:
        # Make a request to Ollama API to get available models
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models_data = response.json()
            # Format the response with relevant model info
            models = []
            for model in models_data.get('models', []):
                name = model.get('name')
                size = model.get('size', 0)
                # Convert size to human-readable format (GB or MB)
                if size > 1_000_000_000:  # If greater than 1GB
                    size_str = f"{size / 1_000_000_000:.1f}GB"
                else:
                    size_str = f"{size / 1_000_000:.1f}MB"
                
                models.append({
                    "name": name,
                    "size": size_str,
                    "raw_size": size
                })
            
            # Sort by name
            models.sort(key=lambda x: x['name'])
            
            return jsonify({"models": models})
        else:
            return jsonify({"error": "Failed to fetch models from Ollama", "models": []}), 500
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        # Return some default models in case of error
        return jsonify({
            "models": [
                {"name": "gemma3:12b", "size": "unknown", "raw_size": 0},
                {"name": "llama3:8b", "size": "unknown", "raw_size": 0},
                {"name": "mistral:7b", "size": "unknown", "raw_size": 0},
            ]
        })

@app.route('/api/model', methods=['POST'])
def set_model():
    """Set the model to use for a session"""
    data = request.json
    model_name = data.get('model')
    session_id = data.get('session_id', 'default')
    
    if not model_name:
        return jsonify({"error": "No model name provided"}), 400
    
    session = get_or_create_session(session_id)
    
    try:
        # Create a new provider with the selected model
        provider = ProviderFactory.create_provider("ollama", model=model_name)
        
        # Update the session
        session["provider"] = provider
        session["model"] = model_name
        
        return jsonify({
            "success": True,
            "message": f"Model changed to {model_name}",
            "model": model_name
        })
    except Exception as e:
        logger.error(f"Error changing model: {e}")
        return jsonify({"error": f"Failed to change model: {str(e)}"}), 500
    
@app.route('/api/document/chunks', methods=['GET'])
def get_document_chunks():
    """Get chunks for a document"""
    document_name = request.args.get('document_name')
    session_id = request.args.get('session_id', 'default')
    
    if not document_name:
        return jsonify({"error": "No document name provided"}), 400
    
    # Find all chunks for this document
    chunks = []
    for idx, doc in enumerate(document_store.documents):
        source = doc.metadata.get("source", "unknown")
        filename = Path(source).name
        
        if document_name.lower() in filename.lower():
            # Create a chunk representation
            chunk = {
                "id": str(idx),  # Use the index as a simple ID
                "content": doc.content,
                "metadata": {
                    "source": source,
                    "filename": filename,
                    "chunk": doc.metadata.get("chunk", idx + 1),
                    "chunk_of": doc.metadata.get("chunk_of", 0),
                    "page": doc.metadata.get("page", 0)
                }
            }
            chunks.append(chunk)
    
    return jsonify({"document_name": document_name, "chunks": chunks})

if __name__ == '__main__':
    print("Starting Flask API server on http://localhost:5000")
    
    # Create a directory for temporary files that won't trigger reload
    temp_dir = os.path.join(tempfile.gettempdir(), "mcp_code_exec")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Run the app with specific settings
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=True,
        use_reloader=True,
        extra_files=[],
    )