export interface FileInfo {
  name: string;
  type: string;
  content: string;
  isImage?: boolean;
  imageData?: string;
  caption?: string;
  path?: string;
  language?: string;
}

export interface FolderContext {
  path: string;
  files: FileInfo[];
  timestamp: string;
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
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  files?: FileInfo[];
  searchResults?: SearchResult[];
  searchSummary?: string;
  thinkingContent?: string;
  audioId?: string;
  model?: string;
  metadata?: {
    [key: string]: any;
  };
  folder_context?: FolderContext;
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
  onImportHub?: (hubFile: HubFile) => void;
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
  message?: string;
  folder_scan_result?: {
    success: boolean;
    folder_path?: string;
    files?: FileInfo[];
    error?: string;
  };
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
  folder_files?: FileInfo[];
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

export interface HubFile {
  version: string;
  clientId: string;
  chatId: string;
  messages: Message[];
  folderContext?: FolderContext;
  settings: {
    model: string;
    search: SearchSettings;
  };
  metadata: {
    created: string;
    lastModified: string;
    title: string;
    messageCount: number;
  };
}

export interface ChatSession {
  id: string;
  name: string;
  created: Date;
  hubFile?: HubFile;
}

export interface Notification {
  type: 'success' | 'error' | 'info';
  message: string;
}

export interface HubImportRequest {
  type: 'hub_import';
  hubFile: HubFile;
  chatId: string;
}

export interface HubExportRequest {
  type: 'hub_export';
  chatId: string;
}

export interface HubImportResponse {
  type: 'hub_import_response';
  success: boolean;
  error?: string;
}

export interface HubExportResponse {
  type: 'hub_export_response';
  success: boolean;
  data?: HubFile;
  error?: string;
}

export interface ScanFolderRequest {
  type: 'scan_folder';
  folder_path: string;
}

export interface ScanFolderResponse {
  type: 'folder_scan_result';
  success: boolean;
  folder_path?: string;
  files?: FileInfo[];
  error?: string;
}

export interface FolderPanelProps {
  onFolderChange: (files: FileInfo[]) => void;
  sendMessage: (data: any) => void;
  isConnected: boolean;
  files?: FileInfo[];
  isLoading?: boolean;
}