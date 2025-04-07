import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadedFile } from '@/api/chat';

interface FilePanelProps {
  files: UploadedFile[];
  onFileUpload: (files: File[]) => void;
  isUploading: boolean;
  onAnalyze: (filenames: string[]) => void;
  onAnalyzeWithCode: (filenames: string[]) => void;
  onDeepAnalyze: (filenames: string[]) => void;
  onViewChunks: (filename: string) => void;
}

export const FilePanel = ({ 
  files, 
  onFileUpload, 
  isUploading,
  onAnalyze,
  onAnalyzeWithCode,
  onDeepAnalyze,
  onViewChunks
}: FilePanelProps) => {
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        onFileUpload(acceptedFiles);
      }
    },
    [onFileUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop,
    multiple: true // Allow multiple files
  });
  
  const toggleFileSelection = (fileId: string) => {
    const newSelection = new Set(selectedFiles);
    if (newSelection.has(fileId)) {
      newSelection.delete(fileId);
    } else {
      newSelection.add(fileId);
    }
    setSelectedFiles(newSelection);
  };
  
  const getSelectedFilenames = (): string[] => {
    return files
      .filter(file => selectedFiles.has(file.id))
      .map(file => file.name);
  };
  
  const handleAnalyze = () => {
    const filenames = getSelectedFilenames();
    if (filenames.length > 0) {
      onAnalyze(filenames);
    }
  };
  
  const handleAnalyzeWithCode = () => {
    const filenames = getSelectedFilenames();
    if (filenames.length > 0) {
      onAnalyzeWithCode(filenames);
    }
  };

  const handleDeepAnalyze = () => {
    const filenames = getSelectedFilenames();
    if (filenames.length > 0) {
      onDeepAnalyze(filenames);
    }
  };


  return (
    <div className="h-full flex flex-col bg-white dark:bg-neutral-800 border-l border-gray-200 dark:border-neutral-700">
      <div className="p-4 border-b border-gray-200 dark:border-neutral-700">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Documents</h2>
        
        {/* Drag & Drop Area */}
        <div
          {...getRootProps()}
          className={`
            border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-colors
            ${isDragActive 
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
              : 'border-gray-300 dark:border-neutral-600 hover:border-blue-400 dark:hover:border-blue-500 bg-gray-50 dark:bg-neutral-700'}
          `}
        >
          <input {...getInputProps()} />
          {isDragActive ? (
            <p className="text-blue-500 dark:text-blue-400">Drop files here...</p>
          ) : (
            <div>
              <p className="mb-2 text-gray-600 dark:text-neutral-300">Drag & drop files here, or click to select</p>
              <button
                className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1.5 rounded-full text-sm font-medium transition-colors"
                onClick={(e) => e.stopPropagation()}
              >
                Select Files
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Upload Status */}
      {isUploading && (
        <div className="mx-4 mt-4 bg-yellow-50 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 p-2.5 rounded-lg text-sm border border-yellow-100 dark:border-yellow-800/30">
          <div className="flex items-center">
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Uploading files...
          </div>
        </div>
      )}

      {/* Analysis Action Buttons - only show if files are selected */}
      {selectedFiles.size > 0 && (
        <div className="px-4 pt-3 pb-2 flex flex-wrap gap-2">
            <button
            onClick={handleAnalyze}
            className="flex-1 bg-blue-500 hover:bg-blue-600 text-white py-2 rounded-lg text-sm font-medium transition-colors"
            >
            Analyze Selected
            </button>
            <button
            onClick={handleAnalyzeWithCode}
            className="flex-1 bg-purple-500 hover:bg-purple-600 text-white py-2 rounded-lg text-sm font-medium transition-colors"
            >
            Code Analysis
            </button>
            <button
            onClick={handleDeepAnalyze}
            className="flex-1 bg-green-500 hover:bg-green-600 text-white py-2 rounded-lg text-sm font-medium transition-colors"
            >
            Deep Analysis
            </button>
        </div>
      )}

      {/* File List */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-medium text-sm text-gray-600 dark:text-neutral-400">
            Files
          </h3>
          {selectedFiles.size > 0 && (
            <span className="text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full">
              {selectedFiles.size} selected
            </span>
          )}
        </div>
        
        {files.length === 0 ? (
          <p className="text-gray-500 dark:text-neutral-400 text-sm">No files uploaded yet</p>
        ) : (
          <ul className="space-y-2">
            {files.map((file) => (
              <li
                key={file.id}
                className="bg-white dark:bg-neutral-700 rounded-lg border border-gray-200 dark:border-neutral-600 overflow-hidden shadow-sm"
              >
                <div className="p-3">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={selectedFiles.has(file.id)}
                      onChange={() => toggleFileSelection(file.id)}
                      className="h-4 w-4 text-blue-600 rounded border-gray-300 dark:border-neutral-500 focus:ring-blue-500"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate text-gray-900 dark:text-white">{file.name}</p>
                      <div className="mt-1 flex items-center">
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            file.processed
                              ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300 border border-green-100 dark:border-green-800/30'
                              : 'bg-yellow-50 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 border border-yellow-100 dark:border-yellow-800/30'
                          }`}
                        >
                          {file.processed ? 'Ready' : 'Processing'}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Individual file actions */}
                  {file.processed && (
                    <div className="mt-2 flex flex-wrap gap-2">
                        <button 
                        onClick={() => onAnalyze([file.name])}
                        className="text-xs px-2 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-100 dark:hover:bg-blue-800/30 transition-colors border border-blue-100 dark:border-blue-800/30"
                        >
                        Quick analyze
                        </button>
                        <button 
                        onClick={() => onAnalyzeWithCode([file.name])}
                        className="text-xs px-2 py-1 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded hover:bg-purple-100 dark:hover:bg-purple-800/30 transition-colors border border-purple-100 dark:border-purple-800/30"
                        >
                        With code
                        </button>
                        <button 
                        onClick={() => onDeepAnalyze([file.name])}
                        className="text-xs px-2 py-1 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded hover:bg-green-100 dark:hover:bg-green-800/30 transition-colors border border-green-100 dark:border-green-800/30"
                        >
                        Deep analysis
                        </button>
                        <button 
                        onClick={() => onViewChunks(file.name)}
                        className="text-xs px-2 py-1 bg-gray-50 dark:bg-gray-900/30 text-gray-700 dark:text-gray-300 rounded"
                      >
                        View chunks
                      </button>
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};