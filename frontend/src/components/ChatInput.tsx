// frontend/src/components/ChatInput.tsx
import { useState, useRef, useEffect, KeyboardEvent, DragEvent, useCallback } from 'react'
import { FiUpload } from 'react-icons/fi'
import { ICONS, MESSAGES } from './config'
import { FileInfo } from './types'
import { supportedFileTypes } from '../config/fileTypes.config'

export const ChatInput = ({
  onSend,
  disabled
}: {
  onSend: (message: string, files?: FileInfo[]) => void
  disabled: boolean
}) => {
  const [input, setInput] = useState('')
  const [files, setFiles] = useState<FileInfo[]>([])
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const adjustHeight = () => {
      if (inputRef.current) {
        inputRef.current.style.height = 'auto'
        inputRef.current.style.height = `${inputRef.current.scrollHeight}px`
      }
    }
    adjustHeight()
  }, [input])

  const handleKeyPress = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSend = () => {
    if (input.trim() || files.length > 0) {
      onSend(input.trim(), files)
      setInput('')
      setFiles([])
    }
  }

  const handleFileUpload = useCallback(async (uploadedFiles: FileList) => {
    const newFiles: FileInfo[] = []
    
    for (const file of uploadedFiles) {
      if (file.type.startsWith('image/')) {
        try {
          const reader = new FileReader()
          const imageData = await new Promise<string>((resolve, reject) => {
            reader.onload = () => resolve(reader.result as string)
            reader.onerror = reject
            reader.readAsDataURL(file)
          })
          
          newFiles.push({
            name: file.name,
            type: file.type,
            content: 'Image file uploaded for OCR processing',
            isImage: true,
            imageData
          })
        } catch (error) {
          console.error(`Error reading image ${file.name}:`, error)
        }
      } else {
        const extension = '.' + file.name.split('.').pop()?.toLowerCase()
        
        if (file.type.startsWith('text/') || supportedFileTypes.extensions.includes(extension)) {
          try {
            const content = await file.text()
            newFiles.push({
              name: file.name,
              type: file.type || 'text/plain',
              content: content
            })
          } catch (error) {
            console.error(`Error reading file ${file.name}:`, error)
          }
        }
      }
    }

    setFiles(prev => [...prev, ...newFiles])
  }, [])

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (e.dataTransfer.files) {
      handleFileUpload(e.dataTransfer.files)
    }
  }

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-2">
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2 p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
          {files.map((file, index) => (
            <div 
              key={index}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full"
            >
              {file.isImage && file.imageData && (
                <img 
                  src={file.imageData} 
                  alt={file.name}
                  className="w-6 h-6 rounded object-cover"
                />
              )}
              <span className="text-sm truncate max-w-[200px]">{file.name}</span>
              <button
                onClick={() => removeFile(index)}
                className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
                title="Remove file"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
      
      <div className="flex gap-2">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          className="flex-1 min-h-[44px] max-h-[200px] px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 resize-none"
          placeholder={files.length > 0 ? "Add a message or send files directly..." : MESSAGES.placeholder}
          disabled={disabled}
        />
        
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={`${supportedFileTypes.extensions.join(',')},text/*,image/*`}
          className="hidden"
          onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
        />
        
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center justify-center w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300"
          title="Upload files"
        >
          <FiUpload className="w-5 h-5" />
        </button>

        <button
          onClick={handleSend}
          disabled={disabled || (!input.trim() && files.length === 0)}
          className={`flex items-center justify-center w-10 h-10 rounded-lg transition-colors ${
            !disabled && (input.trim() || files.length > 0)
              ? 'bg-blue-600 hover:bg-blue-700 text-white'
              : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
          }`}
        >
          <ICONS.send className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}