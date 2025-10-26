'use client';

import { useState } from 'react';
import { Sparkles } from 'lucide-react';
import AudioUploader from '@/components/AudioUploader';
import ProcessingStatus from '@/components/ProcessingStatus';
import HighlightPreview from '@/components/HighlightPreview';
import { UploadResponse, ProcessingStatusResponse } from '@/types';

enum AppState {
  UPLOAD = 'upload',
  PROCESSING = 'processing',
  COMPLETE = 'complete',
}

export default function Home() {
  const [appState, setAppState] = useState<AppState>(AppState.UPLOAD);
  const [jobId, setJobId] = useState<string | null>(null);
  const [completedStatus, setCompletedStatus] = useState<ProcessingStatusResponse | null>(null);

  const handleUploadComplete = (response: UploadResponse) => {
    setJobId(response.job_id);
    setAppState(AppState.PROCESSING);
  };

  const handleProcessingComplete = (status: ProcessingStatusResponse) => {
    setCompletedStatus(status);
    setAppState(AppState.COMPLETE);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-3">
            <Sparkles className="w-8 h-8 text-blue-500" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                AI Podcast Highlights
              </h1>
              <p className="text-sm text-gray-600">
                Generate viral clips from your podcasts automatically
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {appState === AppState.UPLOAD && (
          <div>
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-gray-900 mb-3">
                Upload Your Podcast
              </h2>
              <p className="text-gray-600 max-w-2xl mx-auto">
                Our AI will analyze your audio, find the most engaging moments, 
                and create ready-to-share highlight videos for TikTok and Instagram Reels.
              </p>
            </div>
            <AudioUploader onUploadComplete={handleUploadComplete} />
          </div>
        )}

        {appState === AppState.PROCESSING && jobId && (
          <div>
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-gray-900 mb-3">
                Processing Your Podcast
              </h2>
              <p className="text-gray-600">
                Sit back and relax while our AI works its magic...
              </p>
            </div>
            <ProcessingStatus 
              jobId={jobId} 
              onComplete={handleProcessingComplete} 
            />
          </div>
        )}

        {appState === AppState.COMPLETE && completedStatus && (
          <HighlightPreview status={completedStatus} />
        )}
      </main>

      {/* Footer */}
      <footer className="mt-16 py-8 border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-gray-500 text-sm">
          <p>© 2025 AI Podcast Highlights. Built with Next.js & FastAPI.</p>
        </div>
      </footer>
    </div>
  );
}