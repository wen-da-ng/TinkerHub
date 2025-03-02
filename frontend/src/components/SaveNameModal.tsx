// frontend/src/components/SaveNameModal.tsx
import { FC, useState } from 'react'

interface SaveNameModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (name: string) => void;
}

export const SaveNameModal: FC<SaveNameModalProps> = ({ isOpen, onClose, onSave }) => {
  const [name, setName] = useState('');
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-96 max-w-full">
        <h2 className="text-xl font-semibold mb-4">Name Your Conversation</h2>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Enter a name for this conversation"
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg mb-4 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          autoFocus
        />
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              if (name.trim()) {
                onSave(name.trim());
                onClose();
              }
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg"
            disabled={!name.trim()}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
};