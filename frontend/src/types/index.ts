export enum ProcessingStatus {
  PENDING = 'pending',
  UPLOADING = 'uploading',
  TRANSCRIBING = 'transcribing',
  ANALYZING = 'analyzing',
  GENERATING = 'generating',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export interface Highlight {
  start_time: number;
  end_time: number;
  text: string;
  confidence: number;
  reason: string;
  ai_hook?: string;  // AI-generated viral hook (if enabled)
}

export interface UploadResponse {
  job_id: string;
  filename: string;
  file_size: number;
  message: string;
}

export interface ProcessingStatusResponse {
  job_id: string;
  status: ProcessingStatus;
  progress: number;
  message: string;
  highlights?: Highlight[];
  video_url?: string;          // Keep for backward compatibility
  video_urls?: string[];       // NEW: Array of video URLs
  error?: string;
  transcript?: string;         // NEW: Full transcript text
}

export interface ProcessRequest {
  job_id: string;
  highlight_duration?: number;
  style?: 'waveform' | 'captions' | 'animated';
}