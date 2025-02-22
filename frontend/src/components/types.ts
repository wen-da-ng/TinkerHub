// frontend/src/components/types.ts

export interface FileInfo {
  name: string;
  type: string;
  content: string;
  isImage?: boolean;
  imageData?: string;
  caption?: string;
}

export interface ModelInfo {
  name: string;
  size_gb: number;
  ram_requirement: number;
  details?: string;
  parameter_size?: string;
}

export interface GPUInfo {
  name: string;
  memory_total?: number;
  memory_free?: number;
}

export interface SystemSpecs {
  memory_gb: number;
  memory_available_gb: number;
  memory_percent: number;
  cpu_cores: number;
  cpu_threads: number;
  cpu_percent: number;
  platform: string;
  platform_version: string;
  processor: string;
  gpus: GPUInfo[];
  has_gpu: boolean;
  error?: string;
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
  model?: string;
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
  models?: ModelInfo[];
  specs?: SystemSpecs;
  message?: string; // For error messages
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
  model?: string;
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

export interface ModelsResponse {
  type: 'models';
  models: ModelInfo[];
}

export interface GetModelsRequest {
  type: 'get_models';
}

export interface SystemInfoResponse {
  type: 'system_info';
  specs: SystemSpecs;
}

export interface GetSystemInfoRequest {
  type: 'get_system_info';
}

export interface SystemCapabilities {
  memory: number;
  memory_available: number;
  gpu: boolean;
  gpuInfo?: string;
  cpu_cores: number;
  cpu_threads: number;
  platform: string;
  platform_version?: string;
  processor?: string;
}

export interface ModelCompatibility {
  compatible: boolean;
  warnings: string[];
  performance: 'good' | 'moderate' | 'poor';
}

export interface ErrorResponse {
  type: 'error';
  message: string;
}