# C:\Users\L\Desktop\Dev\MCP_learnings\mySecondAdvancedLLM\web_app.py

import asyncio
import os
from pathlib import Path
import tempfile
import json
from typing import List, Dict, Any, Optional
import threading
import time
import uuid

from flask import Flask, request, jsonify, send_from_directory, Response
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

# Server-sent events support
def stream_template(template):
    def streamer(**context):
        yield "data: " + json.dumps({"type": "start"}) + "\n\n"
        for chunk in context.get('chunks', []):
            yield "data: " + json.dumps({"type": "chunk", "content": chunk}) + "\n\n"
            time.sleep(0.01)  # Small delay to simulate streaming
        yield "data: " + json.dumps({"type": "end"}) + "\n\n"
    return streamer

# Initialize chat components
document_store = DocumentStore()
embedding_generator = get_embedding_generator(embedding_type="dummy")
vector_db = InMemoryVectorDB()
base_system_prompt = "You are a helpful assistant. Provide clear and concise answers."

# Store user sessions
sessions = {}

def get_or_create_session(session_id):
    """Get existing session or create a new one"""
    if session_id not in sessions:
        provider = ProviderFactory.create_provider("ollama", model="gemma3:12b")
        sessions[session_id] = {
            "memory": ConversationMemory(max_short_term_messages=20),
            "provider": provider,
            "context": Context(system_prompt=base_system_prompt),
            "message_count": 0,
            "uploaded_files": {}
        }
    return sessions[session_id]

# Background task handling
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
    
    # Start a new thread for async processing
    response = Response(mimetype='text/event-stream')
    
    # Create a background task
    threading.Thread(
        target=lambda: asyncio.run(process_chat_message(message, session_id))
    ).start()
    
    # Return an immediate response with message received confirmation
    return jsonify({
        "success": True,
        "message": "Message received, processing started",
        "message_id": str(uuid.uuid4())
    })

@app.route('/api/stream', methods=['GET'])
def stream():
    """Stream the response for a chat message"""
    session_id = request.args.get('session_id', 'default')
    message = request.args.get('message', '')
    
    def generate():
        for chunk in process_chat_message_stream(message, session_id):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: {\"done\": true}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

def process_chat_message_stream(message, session_id):
    """Process a chat message and yield chunks for streaming"""
    session = get_or_create_session(session_id)
    memory = session["memory"]
    provider = session["provider"]
    
    # Create user message and add to memory
    user_message = Message(role=MessageRole.USER, content=message)
    memory.add_message(user_message)
    session["message_count"] += 1
    
    # Create special commands for analyzing documents
    if message.startswith("/analyze "):
        doc_name = message[9:].strip()
        yield f"Retrieving document: {doc_name}..."
        
        # Get all chunks of the specified document
        complete_doc = retrieve_complete_document(doc_name)
        
        if not complete_doc:
            yield f"No document matching '{doc_name}' found."
            return
            
        yield f"Retrieved {len(complete_doc)} chunks. Analyzing..."
        
        current_system_prompt = (
            f"{base_system_prompt}\n\n"
            f"You have access to the complete document '{doc_name}'. "
            f"Analyze it thoroughly to answer the user's question.\n\n"
            f"{''.join(complete_doc)}"
        )
        
        analysis_context = Context(system_prompt=current_system_prompt)
        analysis_context.add_message(MessageRole.USER, message)
        
        # This is simplified - would need to modify OllamaProvider to support streaming
        response = asyncio.run(provider.generate_response(analysis_context))
        
        for i in range(0, len(response), 10):
            chunk = response[i:i+10]
            yield chunk
            
        # Add to memory system
        assistant_message = Message(role=MessageRole.ASSISTANT, content=response)
        memory.add_message(assistant_message)
        
        return
            
    # Regular chat interaction
    # Check if documents are loaded
    if document_store.documents:
        # Enhance the query for better retrieval
        try:
            # We'd need to modify this for streaming
            enhanced_query = asyncio.run(rewrite_query(provider, message, "expansion"))
            relevant_docs = retrieve_relevant_documents(enhanced_query, top_k=3)
        except Exception as e:
            print(f"Error enhancing query: {e}. Using original query.")
            relevant_docs = retrieve_relevant_documents(message, top_k=3)
        
        current_system_prompt = base_system_prompt
        if relevant_docs:
            current_system_prompt = (
                f"{base_system_prompt}\n\n"
                f"You have access to the following documents that may be relevant to the user's question: "
                f"\"{message}\"\n\n"
                f"{' '.join(relevant_docs)}"
            )
    else:
        current_system_prompt = base_system_prompt
        
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
    response = asyncio.run(provider.generate_response(optimized_context))
    
    # Stream the response in chunks
    for i in range(0, len(response), 10):
        chunk = response[i:i+10]
        yield chunk
        
    # Add to memory
    assistant_message = Message(role=MessageRole.ASSISTANT, content=response)
    memory.add_message(assistant_message)
    
    # Update context
    session["context"].add_message(MessageRole.USER, message)
    session["context"].add_message(MessageRole.ASSISTANT, response)
    
    # Background processing (moved to a thread)
    threading.Thread(
        target=lambda: asyncio.run(process_facts_in_background(provider, memory, user_message))
    ).start()
    
    threading.Thread(
        target=lambda: asyncio.run(process_facts_in_background(provider, memory, assistant_message))
    ).start()
    
    if session["message_count"] % 3 == 0:
        threading.Thread(
            target=lambda: asyncio.run(generate_summary_in_background(provider, memory))
        ).start()

async def process_chat_message(message, session_id):
    """Process a chat message (non-streaming version)"""
    session = get_or_create_session(session_id)
    memory = session["memory"]
    provider = session["provider"]
    context = session["context"]
    
    # Create user message and add to memory
    user_message = Message(role=MessageRole.USER, content=message)
    memory.add_message(user_message)
    session["message_count"] += 1
    
    # Check if documents are loaded
    if document_store.documents:
        try:
            enhanced_query = await rewrite_query(provider, message, "expansion") 
            relevant_docs = retrieve_relevant_documents(enhanced_query, top_k=3)
        except Exception as e:
            print(f"Error enhancing query: {e}. Using original query.")
            relevant_docs = retrieve_relevant_documents(message, top_k=3)
        
        current_system_prompt = base_system_prompt
        if relevant_docs:
            current_system_prompt = (
                f"{base_system_prompt}\n\n"
                f"You have access to the following documents that may be relevant to the user's question: "
                f"\"{message}\"\n\n"
                f"{' '.join(relevant_docs)}"
            )
    else:
        current_system_prompt = base_system_prompt
    
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
    response = await provider.generate_response(optimized_context)
    
    # Add to memory
    assistant_message = Message(role=MessageRole.ASSISTANT, content=response)
    memory.add_message(assistant_message)
    
    # Update context
    context.add_message(MessageRole.USER, message)
    context.add_message(MessageRole.ASSISTANT, response)
    
    # Background processing
    asyncio.create_task(process_facts_in_background(provider, memory, user_message))
    asyncio.create_task(process_facts_in_background(provider, memory, assistant_message))
    
    if session["message_count"] % 3 == 0:
        asyncio.create_task(generate_summary_in_background(provider, memory))
    
    return response

# Helper functions from app.py
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

# Serve static files
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    # Create a directory for static files if it doesn't exist
    os.makedirs('static', exist_ok=True)
    
    # Create a basic HTML file if it doesn't exist
    if not os.path.exists('index.html'):
        with open('index.html', 'w') as f:
            f.write("""
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>MCP Advanced Chatbot</title>
                        <link rel="stylesheet" href="static/styles.css">
                    </head>
                    <body>
                        <div class="app-container">
                            <div class="sidebar">
                                <div class="brand">
                                    <h1>MCP Chatbot</h1>
                                </div>
                                <div class="file-upload">
                                    <h3>Upload Document</h3>
                                    <form id="uploadForm">
                                        <input type="file" id="fileInput" />
                                        <button type="submit">Upload</button>
                                    </form>
                                </div>
                                <div class="uploaded-files">
                                    <h3>Your Documents</h3>
                                    <ul id="filesList"></ul>
                                </div>
                            </div>
                            <div class="main-content">
                                <div class="chat-container">
                                    <div class="messages" id="messages"></div>
                                    <div class="input-area">
                                        <textarea id="userInput" placeholder="Ask me anything..."></textarea>
                                        <button id="sendButton">Send</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <script src="static/app.js"></script>
                    </body>
                    </html>
                                """)
    
    # Create CSS file
    if not os.path.exists('static/styles.css'):
        os.makedirs('static', exist_ok=True)
        with open('static/styles.css', 'w') as f:
            f.write("""
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

body {
    background-color: #f7f7f7;
}

.app-container {
    display: flex;
    height: 100vh;
}

.sidebar {
    width: 300px;
    background-color: #2c3e50;
    color: white;
    padding: 1rem;
    display: flex;
    flex-direction: column;
}

.brand h1 {
    font-size: 1.5rem;
    margin-bottom: 2rem;
}

.file-upload {
    margin-bottom: 1.5rem;
}

.file-upload h3 {
    margin-bottom: 0.5rem;
    font-size: 1rem;
}

#uploadForm {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

#fileInput {
    padding: 0.5rem;
    background-color: #34495e;
    border: none;
    border-radius: 4px;
    color: white;
}

button {
    padding: 0.5rem 1rem;
    background-color: #3498db;
    border: none;
    border-radius: 4px;
    color: white;
    cursor: pointer;
    transition: background-color 0.3s;
}

button:hover {
    background-color: #2980b9;
}

.uploaded-files h3 {
    margin-bottom: 0.5rem;
    font-size: 1rem;
}

#filesList {
    list-style: none;
}

#filesList li {
    padding: 0.5rem;
    background-color: #34495e;
    margin-bottom: 0.5rem;
    border-radius: 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.chat-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
    background-color: white;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
}

.messages {
    flex: 1;
    padding: 1rem;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.message {
    padding: 1rem;
    border-radius: 8px;
    max-width: 80%;
}

.user-message {
    background-color: #3498db;
    color: white;
    align-self: flex-end;
}

.bot-message {
    background-color: #f2f2f2;
    color: #333;
    align-self: flex-start;
}

.input-area {
    padding: 1rem;
    display: flex;
    gap: 0.5rem;
    border-top: 1px solid #eee;
}

#userInput {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #ccc;
    border-radius: 4px;
    resize: none;
    font-size: 1rem;
}

#sendButton {
    align-self: flex-end;
}

.processing-indicator {
    display: inline-block;
    margin-left: 0.5rem;
    font-style: italic;
    color: #7f8c8d;
}

.file-processing {
    font-style: italic;
    color: #e67e22;
}

.file-ready {
    color: #27ae60;
}

code {
    background-color: #f8f8f8;
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.9rem;
}

pre {
    background-color: #f8f8f8;
    padding: 1rem;
    border-radius: 4px;
    overflow-x: auto;
    margin: 0.5rem 0;
}
            """)
    
    # Create JavaScript file
    if not os.path.exists('static/app.js'):
        with open('static/app.js', 'w') as f:
            f.write("""
document.addEventListener('DOMContentLoaded', function() {
    // Generate a unique session ID
    const sessionId = 'session_' + Math.random().toString(36).substring(2, 15);
    
    // Get DOM elements
    const messagesContainer = document.getElementById('messages');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const filesList = document.getElementById('filesList');
    
    // Function to add a message to the chat
    function addMessage(message, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(sender === 'user' ? 'user-message' : 'bot-message');
        
        // Convert markdown to HTML (basic implementation)
        let formattedText = message;
        
        // Handle code blocks
        formattedText = formattedText.replace(/```(.+?)```/gs, function(match, p1) {
            return `<pre><code>${p1}</code></pre>`;
        });
        
        // Handle inline code
        formattedText = formattedText.replace(/`(.+?)`/g, '<code>$1</code>');
        
        // Handle bold text
        formattedText = formattedText.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        
        // Handle italic text
        formattedText = formattedText.replace(/\*(.+?)\*/g, '<em>$1</em>');
        
        // Handle newlines
        formattedText = formattedText.replace(/\\n/g, '<br>');
        
        messageDiv.innerHTML = formattedText;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    // Function to send a message
    async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addMessage(message, 'user');
    userInput.value = '';
    
    // Add temporary bot message
    const botMessageDiv = document.createElement('div');
    botMessageDiv.classList.add('message', 'bot-message');
    botMessageDiv.innerHTML = '<div class="processing-indicator">Thinking...</div>';
    messagesContainer.appendChild(botMessageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    try {
        // Send message to API using regular request (not streaming for now)
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            }),
        });
        
        const data = await response.json();
        
        // Start polling for response
        pollForResponse(data.message_id, botMessageDiv);
        
    } catch (error) {
        console.error('Error sending message:', error);
        botMessageDiv.innerHTML = 'Sorry, I encountered an error. Please try again.';
    }
}
    async function pollForResponse(messageId, messageDiv) {
    try {
        const response = await fetch(`/api/response?message_id=${messageId}&session_id=${sessionId}`);
        const data = await response.json();
        
        if (data.status === 'completed') {
            messageDiv.innerHTML = formatMarkdown(data.response);
        } else if (data.status === 'processing') {
            // Keep polling
            setTimeout(() => pollForResponse(messageId, messageDiv), 1000);
        } else {
            messageDiv.innerHTML = 'Sorry, I encountered an error. Please try again.';
        }
    } catch (error) {
        console.error('Error polling for response:', error);
        messageDiv.innerHTML = 'Sorry, I encountered an error. Please try again.';
    }
}
    
    function formatMarkdown(text) {
        // Convert markdown to HTML (basic implementation)
        let formattedText = text;
        
        // Handle code blocks
        formattedText = formattedText.replace(/```(.+?)```/gs, function(match, p1) {
            return `<pre><code>${p1}</code></pre>`;
        });
        
        // Handle inline code
        formattedText = formattedText.replace(/`(.+?)`/g, '<code>$1</code>');
        
        // Handle bold text
        formattedText = formattedText.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        
        // Handle italic text
        formattedText = formattedText.replace(/\*(.+?)\*/g, '<em>$1</em>');
        
        // Handle newlines
        formattedText = formattedText.replace(/\\n/g, '<br>');
        
        return formattedText;
    }
    
    // Upload a file
    async function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('session_id', sessionId);
        
        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData,
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Add a system message about the upload
                addMessage(`File uploaded: ${file.name}. Processing started.`, 'bot');
                // Refresh file list
                loadFilesList();
            } else {
                addMessage(`Error uploading file: ${data.error}`, 'bot');
            }
        } catch (error) {
            console.error('Error uploading file:', error);
            addMessage('Sorry, there was an error uploading your file.', 'bot');
        }
    }
    
    // Load the list of uploaded files
    async function loadFilesList() {
        try {
            const response = await fetch(`/api/files?session_id=${sessionId}`);
            const data = await response.json();
            
            filesList.innerHTML = '';
            
            data.files.forEach(file => {
                const li = document.createElement('li');
                const status = file.processed ? 
                    '<span class="file-ready">Ready</span>' : 
                    '<span class="file-processing">Processing...</span>';
                
                li.innerHTML = `
                    <span>${file.name}</span>
                    ${status}
                `;
                
                // Add click event to analyze file
                li.addEventListener('click', function() {
                    const analysisPrompt = `/analyze ${file.name}`;
                    userInput.value = analysisPrompt;
                    userInput.focus();
                });
                
                filesList.appendChild(li);
            });
        } catch (error) {
            console.error('Error loading files list:', error);
        }
    }
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        if (fileInput.files.length > 0) {
            uploadFile(fileInput.files[0]);
        }
    });
    
    // Initial welcome message
    addMessage('Hello! I\'m your MCP-powered assistant. You can upload documents and ask me questions about them.', 'bot');
    
    // Load files list on startup
    loadFilesList();
    
    // Poll for file status updates
    setInterval(loadFilesList, 5000);
});
            """)
    # Run the Flask app
    
    print("Starting Flask server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)