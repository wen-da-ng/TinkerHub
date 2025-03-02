import { useState, useEffect } from 'react'
import { FiFolder, FiRefreshCw, FiAlertCircle, FiFile } from 'react-icons/fi'
import { supportedFileTypes } from '../config/fileTypes.config'
import { FileInfo } from './types'

interface FolderPanelProps {
    onFolderChange: (files: FileInfo[]) => void;
    sendMessage: (data: any) => void;
    isConnected: boolean;
    files?: FileInfo[];
    isLoading?: boolean;
}

export const FolderPanel: React.FC<FolderPanelProps> = ({ 
    onFolderChange,
    sendMessage,
    isConnected,
    files = [],
    isLoading = false
}) => {
    const [folderPath, setFolderPath] = useState<string>("")
    const [manualPath, setManualPath] = useState<string>("")
    const [error, setError] = useState<string>("")
    const [helpText, setHelpText] = useState<string>("")

    const handleFolderSelect = async () => {
        try {
            const dirHandle = await window.showDirectoryPicker()
            
            // Using just the folder name could lead to path resolution issues
            const folderName = dirHandle.name
            setFolderPath(folderName)
            setHelpText(
                "Browser security prevents getting the full folder path. " +
                "If the folder isn't found, please use the text input to enter the full path manually."
            )
            scanFolder(folderName)
        } catch (error) {
            console.error('Error selecting folder:', error)
            setError('Failed to select folder')
        }
    }

    const handleManualPathSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (manualPath) {
            setFolderPath(manualPath)
            setHelpText("")
            scanFolder(manualPath)
        }
    }

    const scanFolder = async (path: string, forceRefresh: boolean = false) => {
        if (!isConnected) return
        
        setError("")
        
        sendMessage({
            type: 'scan_folder',
            folder_path: path,
            force_refresh: forceRefresh
        })
    }

    // Update folderPath when files change (to handle initial file loading)
    useEffect(() => {
        if (files.length > 0 && files[0].path) {
            // Extract folder path from file path if available
            const filePath = files[0].path
            const folderPathFromFile = filePath.includes('/') 
                ? filePath.substring(0, filePath.lastIndexOf('/'))
                : filePath.includes('\\')
                ? filePath.substring(0, filePath.lastIndexOf('\\'))
                : ""
                
            if (folderPathFromFile && !folderPath) {
                setFolderPath(folderPathFromFile)
            }
        }
    }, [files, folderPath])

    const handleRefresh = () => {
        if (folderPath) {
            scanFolder(folderPath, true)
        }
    }

    return (
        <div className="w-64 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
            <div className="p-4">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Knowledge Base</h2>
                    <button
                        onClick={handleRefresh}
                        disabled={!folderPath || isLoading}
                        className={`p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors ${
                            !folderPath || isLoading ? 'opacity-50 cursor-not-allowed' : ''
                        }`}
                        title="Refresh folder"
                    >
                        <FiRefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                    </button>
                </div>

                <button
                    onClick={handleFolderSelect}
                    disabled={!isConnected}
                    className={`w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-lg mb-4 transition-colors ${
                        !isConnected ? 'opacity-50 cursor-not-allowed' : ''
                    }`}
                >
                    <FiFolder className="w-4 h-4" />
                    <span>Select Folder</span>
                </button>

                <form onSubmit={handleManualPathSubmit} className="mb-4">
                    <input
                        type="text"
                        value={manualPath}
                        onChange={(e) => setManualPath(e.target.value)}
                        placeholder="Or enter full path..."
                        className="w-full p-2 mb-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                    />
                    <button
                        type="submit"
                        disabled={!manualPath || isLoading}
                        className={`w-full flex items-center justify-center gap-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 p-2 rounded-lg transition-colors ${
                            !manualPath || isLoading ? 'opacity-50 cursor-not-allowed' : ''
                        }`}
                    >
                        <FiFolder className="w-4 h-4" />
                        <span>Load Path</span>
                    </button>
                </form>

                {helpText && (
                    <div className="flex items-center gap-2 text-yellow-500 mb-4 p-2 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
                        <FiAlertCircle className="w-4 h-4 flex-shrink-0" />
                        <span className="text-sm">{helpText}</span>
                    </div>
                )}

                {error && (
                    <div className="flex items-center gap-2 text-red-500 mb-4 p-2 bg-red-100 dark:bg-red-900 rounded-lg">
                        <FiAlertCircle className="w-4 h-4 flex-shrink-0" />
                        <span className="text-sm">{error}</span>
                    </div>
                )}

                {folderPath && (
                    <div className="mb-4 p-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            Current Folder:
                        </div>
                        <div className="text-sm text-gray-600 dark:text-gray-400 break-all">
                            {folderPath}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            {files.length} files loaded
                        </div>
                    </div>
                )}

                <div className="space-y-2 max-h-[calc(100vh-350px)] overflow-y-auto">
                    {files.map((file, index) => (
                        <div
                            key={index}
                            className="flex items-center gap-2 p-2 bg-gray-50 dark:bg-gray-700 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                            title={`${file.path}\n${file.content.slice(0, 100)}...`}
                        >
                            <FiFile className="w-4 h-4 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                                <div className="truncate font-medium">
                                    {file.name}
                                </div>
                                <div className="truncate text-xs text-gray-500 dark:text-gray-400">
                                    {file.path}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}

export default FolderPanel