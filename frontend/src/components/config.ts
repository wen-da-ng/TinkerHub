import { BiBrain } from 'react-icons/bi'
import { FaSearch, FaNewspaper, FaPlay, FaImage, FaNewspaper as NewsIcon, FaFolder } from 'react-icons/fa'
import { FiSend, FiSave, FiFolder, FiRefreshCw } from 'react-icons/fi'

export const ICONS = {
  brain: BiBrain,
  search: FaSearch,
  news: NewsIcon,
  play: FaPlay,
  image: FaImage,
  send: FiSend,
  save: FiSave,
  folder: FiFolder,
  folderOpen: FaFolder,
  refresh: FiRefreshCw
}

export const SEARCH_TYPES = ['text', 'news', 'images', 'videos'] as const

export const DEFAULT_SEARCH_SETTINGS = {
  webSearchEnabled: true,
  searchType: 'text' as const,
  showSummary: false,
  resultsCount: 3
}

export const CODE_THEME = {
  style: 'oneDark'
}

export const MESSAGES = {
  disconnected: 'Disconnected - Reconnecting...',
  generating: 'Generating response...',
  placeholder: 'Type your message...',
  savingChat: 'Saving chat...',
  savingSuccess: 'Chat saved successfully',
  savingError: 'Failed to save chat',
  loadingChat: 'Loading chat...',
  loadingSuccess: 'Chat loaded successfully',
  loadingError: 'Failed to load chat',
  invalidFile: 'Invalid .hub file format',
  selectFolder: 'Select a folder to use as knowledge base',
  folderNotFound: 'Selected folder not found',
  folderLoadError: 'Error loading folder',
  folderLoadSuccess: 'Folder loaded successfully',
  folderRefreshing: 'Refreshing folder contents...',
  noFilesFound: 'No supported files found in folder'
}

export const FILE_CONFIG = {
  version: '1.0',
  extension: '.hub',
  mimeType: 'application/json',
  fileNamePrefix: 'chat-'
}

export const FOLDER_PANEL_CONFIG = {
  maxFilePreviewLength: 1000,
  refreshInterval: 5000,
  width: 320,
  headerHeight: 48,
  footerHeight: 48,
  fileListMaxHeight: 'calc(100vh - 180px)'
}

export const UI_CONFIG = {
  notifications: {
    duration: 3000,
    position: {
      bottom: '1rem',
      right: '1rem'
    }
  },
  animations: {
    duration: 300,
    easing: 'cubic-bezier(0.4, 0, 0.2, 1)'
  },
  colors: {
    primary: 'blue',
    success: 'green',
    error: 'red',
    warning: 'yellow',
    info: 'blue'
  }
}

export const WEBSOCKET_CONFIG = {
  reconnectInterval: 3000,
  maxReconnectAttempts: 5
}