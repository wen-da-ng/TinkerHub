// frontend\src\components\config.ts
import { BiBrain } from 'react-icons/bi'
import { FaSearch, FaNewspaper, FaPlay, FaImage, FaNewspaper as NewsIcon } from 'react-icons/fa'
import { FiSend } from 'react-icons/fi'

export const ICONS = {
  brain: BiBrain,
  search: FaSearch,
  news: NewsIcon,
  play: FaPlay,
  image: FaImage,
  send: FiSend
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
  placeholder: 'Type your message...'
}