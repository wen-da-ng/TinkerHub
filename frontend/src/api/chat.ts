export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: number;
  }
  
  export interface UploadedFile {
    id: string;
    name: string;
    processed: boolean;
  }
  
  const API_URL = 'http://localhost:5000/api';
  
  export const sendMessage = async (message: string, sessionId: string, enhanceQuery: boolean = true): Promise<string> => {
    try {
      // Send the message
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          session_id: sessionId,
          enhance_query: enhanceQuery,
        }),
      });
  
      if (!response.ok) {
        throw new Error('Failed to send message');
      }
  
      const data = await response.json();
      return data.message_id;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  };
  
  export const pollForResponse = async (messageId: string): Promise<string> => {
    try {
      const response = await fetch(`${API_URL}/response?message_id=${messageId}`);
      
      if (!response.ok) {
        throw new Error('Failed to get response');
      }
      
      const data = await response.json();
      
      if (data.status === 'completed') {
        return data.response;
      } else if (data.status === 'error') {
        throw new Error(data.response || 'An error occurred');
      } else {
        // Still processing, wait and poll again
        await new Promise(resolve => setTimeout(resolve, 1000));
        return pollForResponse(messageId);
      }
    } catch (error) {
      console.error('Error polling for response:', error);
      throw error;
    }
  };
  
  export const uploadFile = async (file: File, sessionId: string): Promise<UploadedFile> => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('session_id', sessionId);
      
      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Failed to upload file');
      }
      
      const data = await response.json();
      
      return {
        id: data.file_id,
        name: data.filename,
        processed: false,
      };
    } catch (error) {
      console.error('Error uploading file:', error);
      throw error;
    }
  };
  
  export const getFiles = async (sessionId: string): Promise<UploadedFile[]> => {
    try {
      const response = await fetch(`${API_URL}/files?session_id=${sessionId}`);
      
      if (!response.ok) {
        throw new Error('Failed to get files');
      }
      
      const data = await response.json();
      return data.files;
    } catch (error) {
      console.error('Error getting files:', error);
      return [];
    }
  };

  export const getMemory = async (sessionId: string): Promise<any> => {
  try {
    console.log('Fetching memory data...');
    const response = await fetch(`${API_URL}/memory?session_id=${sessionId}`);
    
    if (!response.ok) {
      throw new Error('Failed to get memory');
    }
    
    const data = await response.json();
    console.log('Memory data:', data);
    return data;
  } catch (error) {
    console.error('Error getting memory:', error);
    return null;
  }
};

    export const getSummary = async (sessionId: string): Promise<string> => {
    try {
        console.log('Fetching summary data...');
        const response = await fetch(`${API_URL}/summary?session_id=${sessionId}`);
        
        if (!response.ok) {
        throw new Error('Failed to get summary');
        }
        
        const data = await response.json();
        console.log('Summary data:', data);
        return data.summary || '';
    } catch (error) {
        console.error('Error getting summary:', error);
        return '';
    }
};

// Model interfaces
export interface Model {
    name: string;
    size: string;
    raw_size: number;
  }
  
  // Get available models
  export const getModels = async (): Promise<Model[]> => {
    try {
      const response = await fetch(`${API_URL}/models`);
      
      if (!response.ok) {
        throw new Error('Failed to get models');
      }
      
      const data = await response.json();
      return data.models || [];
    } catch (error) {
      console.error('Error getting models:', error);
      return [];
    }
  };
  
  // Set model for a session
  export const setModel = async (modelName: string, sessionId: string): Promise<boolean> => {
    try {
      const response = await fetch(`${API_URL}/model`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: modelName,
          session_id: sessionId,
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to set model');
      }
      
      const data = await response.json();
      return data.success;
    } catch (error) {
      console.error('Error setting model:', error);
      return false;
    }
  };

  export interface Chunk {
    id: string;
    content: string;
    metadata: {
      source?: string;
      page?: number;
      chunk?: number;
      chunk_of?: number;
      relevance?: number;
    };
  }
  
  // Add this function to your chat.ts file
  export const getDocumentChunks = async (documentName: string, sessionId: string): Promise<{document_name: string, chunks: Chunk[]}> => {
    try {
      const response = await fetch(
        `${API_URL}/document/chunks?document_name=${encodeURIComponent(documentName)}&session_id=${sessionId}`
      );
      
      if (!response.ok) {
        throw new Error('Failed to get document chunks');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error getting document chunks:', error);
      return { document_name: documentName, chunks: [] };
    }
  };