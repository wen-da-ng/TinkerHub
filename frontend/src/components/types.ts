// frontend/src/components/types.ts

export interface FileInfo {
  name: string;
  type: string;
  content: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  files?: FileInfo[];
  searchResults?: SearchResult[];
  searchSummary?: string;
  thinkingContent?: string;
  audioId?: string;
}

export interface SearchResult {
  type: 'text' | 'news' | 'image' | 'video';
  title: string;
  link: string;
  snippet?: string;
  image?: string;
  thumbnail?: string;
  duration?: string;
  source?: string;
  date?: string;
}

export interface ChatProps {
  chatId: string;
  clientId: string;
  isSidebarOpen: boolean;
}

export interface SearchSettings {
  webSearchEnabled: boolean;
  searchType: 'text' | 'news' | 'images' | 'videos';
  showSummary: boolean;
  resultsCount: number;
}

export interface WebSocketMessage {
  type: string;
  content?: string;
  message_id?: string;
  success?: boolean;
  search_results?: SearchResult[];
  search_summary?: string;
  audio_id?: string;
}

export interface AudioPlaybackRequest {
  type: 'play_audio';
  message_id: string;
}

export interface AudioPlaybackResponse {
  type: 'audio_complete';
  message_id: string;
  success: boolean;
}

export interface MessageRequest {
  message: string;
  files?: FileInfo[];
  webSearchEnabled?: boolean;
  searchType?: string;
  resultsCount?: number;
  showSummary?: boolean;
}

export interface StreamResponse {
  type: 'stream';
  content: string;
}

export interface CompleteResponse {
  type: 'complete';
  content: string;
  search_results: SearchResult[];
  search_summary: string;
  audio_id?: string;
}