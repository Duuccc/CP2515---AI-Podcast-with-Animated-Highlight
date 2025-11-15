'use client';

import { useState, useRef } from 'react';
import { Upload, FileAudio } from 'lucide-react';
import { uploadAudio } from '@/lib/api';
import { UploadResponse } from '@/types';

interface AudioUploaderProps {
  onUploadComplete: (response: UploadResponse) => void;
}

export default function AudioUploader({ onUploadComplete }: AudioUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file && isAudioFile(file)) {
      setSelectedFile(file);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const isAudioFile = (file: File) => {
    const audioExtensions = ['.mp3', '.wav', '.m4a', '.ogg', '.flac'];
    return audioExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    try {
      const response = await uploadAudio(selectedFile);
      onUploadComplete(response);
    } catch (error: any) {
      console.error('Upload failed:', error);
      
      // Extract error message from response
      let errorMessage = 'Upload failed. Please try again.';
      if (error?.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error?.message) {
        errorMessage = error.message;
      } else if (error?.response?.status === 0) {
        errorMessage = 'Cannot connect to server. Please make sure the backend is running.';
      }
      
      alert(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
          transition-all duration-200
          ${isDragging 
            ? 'border-blue-500 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400 bg-white'
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".mp3,.wav,.m4a,.ogg,.flac"
          onChange={handleFileSelect}
          className="hidden"
        />
        
        <div className="flex flex-col items-center gap-4">
          {selectedFile ? (
            <FileAudio className="w-16 h-16 text-blue-500" />
          ) : (
            <Upload className="w-16 h-16 text-gray-400" />
          )}
          
          <div>
            {selectedFile ? (
              <>
                <p className="text-lg font-semibold text-gray-700">{selectedFile.name}</p>
                <p className="text-sm text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </>
            ) : (
              <>
                <p className="text-lg font-semibold text-gray-700">
                  Drop your audio file here
                </p>
                <p className="text-sm text-gray-500">
                  or click to browse
                </p>
                <p className="text-xs text-gray-400 mt-2">
                  Supports MP3, WAV, M4A, OGG, FLAC (max 100MB)
                </p>
              </>
            )}
          </div>
        </div>
      </div>

      {selectedFile && (
        <button
          onClick={handleUpload}
          disabled={isUploading}
          className="
            mt-6 w-full bg-blue-500 hover:bg-blue-600 text-white
            font-semibold py-3 px-6 rounded-lg transition-colors
            disabled:bg-gray-400 disabled:cursor-not-allowed
          "
        >
          {isUploading ? 'Uploading...' : 'Upload & Process'}
        </button>
      )}
    </div>
  );
}