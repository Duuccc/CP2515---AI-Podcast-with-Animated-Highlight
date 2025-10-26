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
  video_url?: string;
  error?: string;
}

export interface ProcessRequest {
  job_id: string;
  highlight_duration?: number;
  style?: 'waveform' | 'captions' | 'animated';
}