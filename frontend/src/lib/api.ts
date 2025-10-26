import axios from 'axios';
import { UploadResponse, ProcessingStatusResponse, ProcessRequest } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadAudio = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<UploadResponse>('/api/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const startProcessing = async (request: ProcessRequest): Promise<ProcessingStatusResponse> => {
  const response = await api.post<ProcessingStatusResponse>('/api/process', request);
  return response.data;
};

export const getJobStatus = async (jobId: string): Promise<ProcessingStatusResponse> => {
  const response = await api.get<ProcessingStatusResponse>(`/api/status/${jobId}`);
  return response.data;
};

export const triggerProcessing = async (jobId: string): Promise<void> => {
  await api.get(`/api/process/${jobId}/start`);
};

export default api;