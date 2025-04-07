import React from 'react';
import { UploadedFile } from '@/api/chat';

interface FileListProps {
  files: UploadedFile[];
  onFileSelect: (filename: string) => void;
}

export const FileList = ({ files, onFileSelect }: FileListProps) => {
  if (files.length === 0) {
    return null;
  }

  return (
    <div className="bg-gray-100 p-4 rounded-lg mb-4">
      <h3 className="font-bold mb-2">Uploaded Documents</h3>
      <ul className="space-y-2">
        {files.map((file) => (
          <li
            key={file.id}
            className="flex justify-between items-center p-2 bg-white rounded cursor-pointer hover:bg-gray-50"
            onClick={() => onFileSelect(file.name)}
          >
            <span className="truncate">{file.name}</span>
            <span
              className={`text-sm px-2 py-1 rounded ${
                file.processed
                  ? 'bg-green-100 text-green-800'
                  : 'bg-yellow-100 text-yellow-800'
              }`}
            >
              {file.processed ? 'Ready' : 'Processing'}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
};