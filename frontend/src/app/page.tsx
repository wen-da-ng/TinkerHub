'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { PanelRightOpen, PanelLeftOpen } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';
import { ChatMessage } from '@/components/Chat/ChatMessage';
import { ChatInput } from '@/components/Chat/ChatInput';
import { FilePanel } from '@/components/Chat/FilePanel';
import { MemoryModal } from '@/components/Chat/MemoryModal';
import { SummaryPanel } from '@/components/Chat/SummaryPanel';
import { ThemeToggle } from "@/components/ThemeToggle";
import { sendMessage, pollForResponse, uploadFile, getFiles, getMemory, getSummary, ChatMessage as ChatMessageType, UploadedFile, Chunk, getDocumentChunks } from '@/api/chat';
import { ModelSelector } from "@/components/Chat/ModelSelector";
import { DocumentVisualization } from '@/components/Chat/DocumentVisualization';

export default function Home() {
  const [sessionId] = useState(() => `session_${uuidv4()}`);
  const [messages, setMessages] = useState<ChatMessageType[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: "👋 Hello! How can I help you today!",
      timestamp: Date.now(),
    },
  ]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [showMemoryModal, setShowMemoryModal] = useState(false);
  const [showSummary, setShowSummary] = useState(false);
  const [memoryData, setMemoryData] = useState<any>(null);
  const [summaryData, setSummaryData] = useState<string>('');
  const [memoryBadge, setMemoryBadge] = useState(0);
  const [summaryBadge, setSummaryBadge] = useState(0);
  const [selectedAnalysisType, setSelectedAnalysisType] = useState<'normal' | 'analyze' | 'analyze_with_code'>('normal');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [enhanceQueries, setEnhanceQueries] = useState<boolean>(false);
  const [showFilePanel, setShowFilePanel] = useState<boolean>(false);
  const [currentModel, setCurrentModel] = useState<string>('gemma3:12b');

  const [showChunkVisualization, setShowChunkVisualization] = useState<boolean>(false);
  const [documentChunks, setDocumentChunks] = useState<{
    document_name: string;
    chunks: Chunk[];
  }>({ document_name: '', chunks: [] });
  const [activeChunks, setActiveChunks] = useState<string[]>([]);

  // Add this handler function
  const handleViewChunks = async (documentName: string) => {
    setShowChunkVisualization(true); // Set state to true to show the modal
    try {
      // Use the imported function from '@/api/chat'
      const chunks = await getDocumentChunks(documentName, sessionId);
      setDocumentChunks(chunks);
    } catch (error) {
      console.error("Error fetching document chunks:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: uuidv4(),
          role: 'system',
          content: `Error loading chunks for ${documentName}`,
          timestamp: Date.now(),
        },
      ]);
      setShowChunkVisualization(false); // Close modal on error
    }
  };

  // Add a handler for model changes
  const handleModelChange = (model: string) => {
    setCurrentModel(model);
    
    // Add a system message to indicate the model change
    setMessages((prev) => [
      ...prev,
      {
        id: uuidv4(),
        role: 'system',
        content: `Model changed to ${model}`,
        timestamp: Date.now(),
      },
    ]);
  };

  const toggleSidebar = () => {
    setShowFilePanel(!showFilePanel);
  };

  // Handle responsive sidebar
  useEffect(() => {
    setShowFilePanel(window.innerWidth >= 1024); // Default show on larger screens (lg breakpoint)

    const handleResize = () => {
      // Optional: You could automatically show/hide based on resize,
      // but the user toggle provides more control.
      // Example: if (window.innerWidth < 1024) setShowFilePanel(false);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Poll for files periodically
  useEffect(() => {
    const fetchFiles = async () => {
      const updatedFiles = await getFiles(sessionId);
      setFiles(updatedFiles);
    };

    fetchFiles();
    const interval = setInterval(fetchFiles, 5000);
    return () => clearInterval(interval);
  }, [sessionId]);

  const handleSendMessage = async (content: string) => {
    // Modify content based on selected analysis type
    let finalContent = content;
    if (selectedAnalysisType === 'analyze') {
      finalContent = `/analyze ${content}`;
    } else if (selectedAnalysisType === 'analyze_with_code') {
      finalContent = `/analyze_with_code ${content}`;
    }
  
    // Add user message to chat
    const userMessage: ChatMessageType = {
      id: uuidv4(),
      role: 'user',
      content: finalContent,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMessage]);
  
    // Reset analysis type after sending
    setSelectedAnalysisType('normal');
  
    // Set processing state
    setIsProcessing(true);
  
    try {
      // Add temporary bot message
      const tempId = `temp_${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        {
          id: tempId,
          role: 'assistant',
          content: '...',
          timestamp: Date.now(),
        },
      ]);
  
      // Send message to API with query enhancement preference
      const messageId = await sendMessage(finalContent, sessionId, enhanceQueries);
  
      // Poll for response
      const response = await pollForResponse(messageId);
  
      // Replace temporary message with actual response
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === tempId
            ? {
                id: messageId,
                role: 'assistant',
                content: response,
                timestamp: Date.now(),
              }
            : msg
        )
      );
    } catch (error) {
      console.error('Error in chat flow:', error);
      // Update with error message
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id.startsWith('temp_')
            ? {
                ...msg,
                content: 'Sorry, I encountered an error processing your request.',
              }
            : msg
        )
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFileUpload = async (files: File[]) => {
    setIsUploading(true);
    
    try {
      // Upload each file sequentially
      for (const file of files) {
        await uploadFile(file, sessionId);
        
        // Add system message about upload
        setMessages((prev) => [
          ...prev,
          {
            id: uuidv4(),
            role: 'system',
            content: `File "${file.name}" uploaded successfully and is being processed.`,
            timestamp: Date.now(),
          },
        ]);
      }
      
      // Refresh file list
      const updatedFiles = await getFiles(sessionId);
      setFiles(updatedFiles);
    } catch (error) {
      console.error('Error uploading files:', error);
      setMessages((prev) => [
        ...prev,
        {
          id: uuidv4(),
          role: 'system',
          content: `Error uploading files.`,
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setIsUploading(false);
    }
  };

  const handleRecall = async (topic: string) => {
    // Handle the recall function (reply to a message)
    setIsProcessing(true);
    try {
      // Send the recall command
      const recallCommand = `/recall ${topic}`;
      const messageId = await sendMessage(recallCommand, sessionId);
      const response = await pollForResponse(messageId);
      
      // Add the response as a system message
      setMessages((prev) => [
        ...prev,
        {
          id: uuidv4(),
          role: 'system',
          content: `Recalled information about "${topic}":\n\n${response}`,
          timestamp: Date.now(),
        },
      ]);
    } catch (error) {
      console.error('Error recalling information:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  useEffect(() => {
    const checkMemoryUpdates = async () => {
      try {
        const memory = await getMemory(sessionId);
        const summary = await getSummary(sessionId);
        
        // Update badges
        const topicCount = memory ? Object.keys(memory.facts).length : 0;
        setMemoryBadge(topicCount);
        
        // Only set the badge if we have a summary and haven't viewed it yet
        setSummaryBadge(summary && !showSummary ? 1 : 0);
      } catch (error) {
        console.error('Error checking memory updates:', error);
      }
    };
    
    // Check every 10 seconds
    const interval = setInterval(checkMemoryUpdates, 10000);
    return () => clearInterval(interval);
  }, [sessionId, showSummary]);
  
  // Keep the existing handlers
  const handleShowMemory = async () => {
    try {
      const memory = await getMemory(sessionId);
      setMemoryData(memory);
      setShowMemoryModal(true);
      setMemoryBadge(0); // Clear badge when viewing
    } catch (error) {
      console.error('Error fetching memory:', error);
    }
  };
  
  const handleShowSummary = async () => {
    try {
      const summary = await getSummary(sessionId);
      setSummaryData(summary);
      setShowSummary(true);
      setSummaryBadge(0); // Clear badge when viewing
    } catch (error) {
      console.error('Error fetching summary:', error);
    }
  };

  
  const handleAnalyzeFile = (filenames: string[]) => {
    // Show a prompt for the analysis question
    const filesText = filenames.length > 1 
      ? `${filenames.length} files (${filenames.join(', ')})` 
      : filenames[0];
      
    const question = prompt(`What specific analysis would you like on ${filesText}?`);
    if (!question) return;
    
    // Add user message showing the documents and question
    const userMessage: ChatMessageType = {
      id: uuidv4(),
      role: 'user',
      content: `/analyze_multi ${filenames.join('|')}\nQuestion: ${question}`,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMessage]);
    
    // Process the message
    processMultiFileAnalysisRequest(filenames, question, 'analyze');
  };

  const handleAnalyzeWithCode = (filenames: string[]) => {
    // Show a prompt for the analysis question
    const filesText = filenames.length > 1 
      ? `${filenames.length} files (${filenames.join(', ')})` 
      : filenames[0];
      
    const question = prompt(`What specific analysis would you like on ${filesText}? (Using code generation)`);
    if (!question) return;
    
    // Add user message showing the documents and question
    const userMessage: ChatMessageType = {
      id: uuidv4(),
      role: 'user',
      content: `/analyze_multi_code ${filenames.join('|')}\nQuestion: ${question}`,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMessage]);
    
    // Process the message
    processMultiFileAnalysisRequest(filenames, question, 'analyze_with_code');
  };
  
  // Add a new function to handle processing the multi-file analysis request
  const processMultiFileAnalysisRequest = async (
    filenames: string[], 
    question: string, 
    type: 'analyze' | 'analyze_with_code'
  ) => {
    setIsProcessing(true);
    
    // Add temporary bot message
    const tempId = `temp_${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      {
        id: tempId,
        role: 'assistant',
        content: `Analyzing ${filenames.length} document(s)...`,
        timestamp: Date.now(),
      },
    ]);
  
    try {
      const command = type === 'analyze' ? '/analyze_multi' : '/analyze_multi_code';
      const messageId = await sendMessage(`${command} ${filenames.join('|')}\n${question}`, sessionId, enhanceQueries);
      const response = await pollForResponse(messageId);
      
      // Replace temporary message with actual response
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === tempId
            ? {
                id: messageId,
                role: 'assistant',
                content: response,
                timestamp: Date.now(),
              }
            : msg
        )
      );
    } catch (error) {
      console.error('Error during multi-file analysis:', error);
      // Update with error message
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === tempId
            ? {
                ...msg,
                content: 'Sorry, I encountered an error analyzing these documents.',
              }
            : msg
        )
      );
    } finally {
      setIsProcessing(false);
    }
  };

const processAnalysisRequest = async (filename: string, question: string, type: 'analyze' | 'analyze_with_code') => {
  setIsProcessing(true);
  
  // Add temporary bot message
  const tempId = `temp_${Date.now()}`;
  setMessages((prev) => [
    ...prev,
    {
      id: tempId,
      role: 'assistant',
      content: 'Analyzing document...',
      timestamp: Date.now(),
    },
  ]);

  try {
    const command = type === 'analyze' ? '/analyze' : '/analyze_with_code';
    const messageId = await sendMessage(`${command} ${filename}\n${question}`, sessionId);
    const response = await pollForResponse(messageId);
    
    // Replace temporary message with actual response
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === tempId
          ? {
              id: messageId,
              role: 'assistant',
              content: response,
              timestamp: Date.now(),
            }
          : msg
      )
    );
  } catch (error) {
    console.error('Error during analysis:', error);
    // Update with error message
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === tempId
          ? {
              ...msg,
              content: 'Sorry, I encountered an error analyzing this document.',
            }
          : msg
      )
    );
  } finally {
    setIsProcessing(false);
  }
};

const handleDeepAnalyze = (filenames: string[]) => {
  // Show a prompt for the analysis question
  const filesText = filenames.length > 1 
    ? `${filenames.length} files (${filenames.join(", ")})` 
    : filenames[0];
    
  const question = prompt(`What deep analysis would you like on ${filesText}?`);
  if (!question) return;
  
  // Add user message showing the documents and question
  const userMessage: ChatMessageType = {
    id: uuidv4(),
    role: "user",
    content: `/deep_analyze ${filenames.join("|")}\nQuestion: ${question}`,
    timestamp: Date.now(),
  };
  setMessages((prev) => [...prev, userMessage]);
  
  // Process the message
  processDeepAnalysisRequest(filenames, question);
};

const processDeepAnalysisRequest = async (filenames: string[], question: string) => {
  setIsProcessing(true);
  
  // Add temporary bot message
  const tempId = `temp_${Date.now()}`;
  setMessages((prev) => [
    ...prev,
    {
      id: tempId,
      role: "assistant",
      content: `Performing deep analysis of ${filenames.length} document(s)...`,
      timestamp: Date.now(),
    },
  ]);

  try {
    const command = "/deep_analyze";
    const messageId = await sendMessage(`${command} ${filenames.join("|")}\n${question}`, sessionId, enhanceQueries);
    const response = await pollForResponse(messageId);
    
    // Replace temporary message with actual response
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === tempId
          ? {
              id: messageId,
              role: "assistant",
              content: response,
              timestamp: Date.now(),
            }
          : msg
      )
    );
  } catch (error) {
    console.error("Error during deep document analysis:", error);
    // Update with error message
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === tempId
          ? {
              ...msg,
              content: "Sorry, I encountered an error performing deep analysis on these documents.",
            }
          : msg
      )
    );
  } finally {
    setIsProcessing(false);
  }
};

return (
  <main className="flex flex-col min-h-screen max-h-screen bg-white dark:bg-neutral-900 text-gray-900 dark:text-white">
    {/* Top Bar */}
    <div className="flex-shrink-0 bg-white dark:bg-neutral-800 shadow-sm border-b border-gray-200 dark:border-neutral-700 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center">
        <button
          onClick={() => setShowFilePanel(!showFilePanel)}
          className="md:hidden p-2 rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-700 mr-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
        <h1 className="text-lg font-medium">TinkerHub 0.4</h1>
      </div>
      <div className="flex items-center gap-3">
        <ModelSelector 
          sessionId={sessionId} 
          onModelChange={handleModelChange} 
        />
        <button 
          onClick={handleShowMemory}
          className="text-sm px-3 py-1.5 rounded-full bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-colors"
        >
          Memory
        </button>
        <button 
          onClick={handleShowSummary}
          className="text-sm px-3 py-1.5 rounded-full bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-colors"
        >
          Summary
        </button>
        <button
              onClick={toggleSidebar}
              className="p-2 rounded-full bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-colors"
              aria-label={showFilePanel ? "Hide document panel" : "Show document panel"}
              title={showFilePanel ? "Hide document panel" : "Show document panel"}
            >
              {showFilePanel ? (
                 <PanelLeftOpen className="h-5 w-5" /> // Icon when panel is open
              ) : (
                 <PanelRightOpen className="h-5 w-5" /> // Icon when panel is closed
              )}
           </button>
        {/* <ThemeToggle /> */}
      </div>
    </div>

    {/* Main Content */}
    <div className="flex flex-1 overflow-hidden">
      {/* Chat Area */}
      <div className="flex-1 flex flex-col bg-white dark:bg-neutral-900 transition-all duration-300 ease-in-out">
        {/* Messages */}
        <div className="flex-1 p-4 overflow-y-auto">
          <div className="max-w-3xl mx-auto space-y-4">
            {messages.map((message) => (
              <ChatMessage 
                key={message.id}
                message={message} 
                onReply={() => {}} // We can implement this later
              />
            ))}
            <div ref={messagesEndRef} className="h-0" />
          </div>
        </div>

        {/* Analysis Options */}
        <div className="flex-shrink-0 border-t border-gray-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 py-2 px-4">
          <div className="max-w-3xl mx-auto flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-3">
              <label className="inline-flex items-center cursor-pointer">
                <input
                  type="radio"
                  name="analysisType"
                  checked={selectedAnalysisType === 'normal'}
                  onChange={() => setSelectedAnalysisType('normal')}
                  className="sr-only"
                />
                <span className={`text-sm px-3 py-1 rounded-full ${selectedAnalysisType === 'normal' ? 'bg-blue-50 dark:bg-blue-900 text-blue-700 dark:text-blue-300' : 'bg-gray-100 dark:bg-neutral-700'}`}>
                  Normal
                </span>
              </label>
              <label className="inline-flex items-center cursor-pointer">
                <input
                  type="radio"
                  name="analysisType"
                  checked={selectedAnalysisType === 'analyze'}
                  onChange={() => setSelectedAnalysisType('analyze')}
                  className="sr-only"
                />
                <span className={`text-sm px-3 py-1 rounded-full ${selectedAnalysisType === 'analyze' ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300' : 'bg-neutral-100 dark:bg-neutral-700'}`}>
                  Analyze Document
                </span>
              </label>
              <label className="inline-flex items-center cursor-pointer">
                <input
                  type="radio"
                  name="analysisType"
                  checked={selectedAnalysisType === 'analyze_with_code'}
                  onChange={() => setSelectedAnalysisType('analyze_with_code')}
                  className="sr-only"
                />
                <span className={`text-sm px-3 py-1 rounded-full ${selectedAnalysisType === 'analyze_with_code' ? 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300' : 'bg-neutral-100 dark:bg-neutral-700'}`}>
                  Analyze with Code
                </span>
              </label>
            </div>
            
            {/* Query Enhancement Toggle */}
            <div className="flex items-center">
              <label className="inline-flex items-center cursor-pointer">
                <span className="mr-2 text-xs font-medium text-gray-700 dark:text-gray-300">
                  Query Enhancement
                </span>
                <div className="relative">
                  <input 
                    type="checkbox" 
                    className="sr-only"
                    checked={enhanceQueries}
                    onChange={() => setEnhanceQueries(!enhanceQueries)}
                  />
                  <div className={`block w-8 h-5 rounded-full transition ${enhanceQueries ? 'bg-blue-500 dark:bg-blue-600' : 'bg-gray-300 dark:bg-neutral-600'}`}></div>
                  <div className={`dot absolute left-0.5 top-0.5 bg-white w-4 h-4 rounded-full transition-transform ${enhanceQueries ? 'transform translate-x-3' : ''}`}></div>
                </div>
              </label>
            </div>
          </div>
        </div>

        {/* Input Area */}
        <div className="flex-shrink-0 border-t border-gray-200 dark:border-neutral-700 p-4 bg-white dark:bg-neutral-800">
          <div className="max-w-3xl mx-auto">
            <ChatInput 
              onSendMessage={handleSendMessage} 
              isProcessing={isProcessing} 
              selectedAnalysisType={selectedAnalysisType}
            />
          </div>
        </div>
      </div>

      {/* Right Side Panel */}
      <div
          className={`
            flex-shrink-0 bg-white dark:bg-neutral-800
            border-l border-gray-200 dark:border-neutral-700
            shadow-sm
            overflow-hidden // Important to hide content during transition
            transition-all duration-300 ease-in-out // The transition classes
            ${showFilePanel ? 'w-full md:w-80 lg:w-96' : 'w-0 border-l-0'} // Conditional width and border
          `}
        >
      {showFilePanel && (
             <div className="h-full w-full md:w-80 lg:w-96"> {/* Ensure inner div has explicit width */}
                 <FilePanel
                    files={files}
                    onFileUpload={handleFileUpload}
                    isUploading={isUploading}
                    onAnalyze={handleAnalyzeFile}
                    onAnalyzeWithCode={handleAnalyzeWithCode}
                    onDeepAnalyze={handleDeepAnalyze}
                    onViewChunks={handleViewChunks}
                 />
             </div>
          )}
          </div>
    </div>

    {/* Memory Modal */}
    {showMemoryModal && (
      <MemoryModal 
        memory={memoryData} 
        onClose={() => setShowMemoryModal(false)} 
      />
    )}

    {/* Summary Panel */}
    {showSummary && (
      <SummaryPanel 
        summary={summaryData} 
        onClose={() => setShowSummary(false)} 
      />
    )}
    
    {/* Chunk Visualization */}
    {showChunkVisualization && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"> {/* Overlay */}
          <div className="bg-white dark:bg-neutral-800 rounded-2xl w-full max-w-4xl max-h-[85vh] overflow-hidden flex flex-col shadow-xl"> {/* Modal Container */}

            {/* Modal Header */}
            <div className="p-4 border-b border-neutral-200 dark:border-neutral-700 flex justify-between items-center flex-shrink-0">
              <h2 className="text-xl font-medium truncate pr-4">
                Document Visualization
              </h2>
              <button
                onClick={() => setShowChunkVisualization(false)}
                className="p-2 rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
                aria-label="Close document visualization"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>

            {/* Modal Body (Scrollable) */}
            {/* Note: Removed p-4 from this div, assuming DocumentVisualization provides its own padding */}
            <div className="overflow-y-auto flex-1">
              {documentChunks.chunks.length > 0 ? (
                 <DocumentVisualization
                    documentName={documentChunks.document_name}
                    chunks={documentChunks.chunks}
                    activeChunks={activeChunks} // Pass down if needed later
                    onChunkClick={(chunkId) => {
                      console.log("Chunk clicked in modal:", chunkId);
                      // Add any interaction logic here if needed, like highlighting
                    }}
                  />
              ) : (
                <div className="p-10 text-center text-neutral-500">Loading chunks or no chunks found...</div>
              )}
            </div>

          </div>
        </div>
      )}
  </main>
);
}