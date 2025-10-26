'use client';

import { Download, Play } from 'lucide-react';
import { ProcessingStatusResponse } from '@/types';

interface HighlightPreviewProps {
  status: ProcessingStatusResponse;
}

export default function HighlightPreview({ status }: HighlightPreviewProps) {
  const handleDownload = () => {
    if (status.video_url) {
      window.open(status.video_url, '_blank');
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Your Highlights</h2>

      {/* Video Preview */}
      {status.video_url && (
        <div className="mb-6 bg-gray-900 rounded-lg overflow-hidden aspect-[9/16] max-w-sm mx-auto">
          <div className="w-full h-full flex items-center justify-center">
            <Play className="w-16 h-16 text-white opacity-50" />
            <p className="absolute text-white text-sm">Video preview (coming soon)</p>
          </div>
        </div>
      )}

      {/* Highlights List */}
      {status.highlights && status.highlights.length > 0 && (
        <div className="space-y-4 mb-6">
          <h3 className="text-lg font-semibold text-gray-800">Detected Highlights</h3>
          {status.highlights.map((highlight, index) => (
            <div
              key={index}
              className="p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start mb-2">
                <span className="text-sm font-medium text-blue-600">
                  {formatTime(highlight.start_time)} - {formatTime(highlight.end_time)}
                </span>
                <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                  {Math.round(highlight.confidence * 100)}% confidence
                </span>
              </div>
              <p className="text-gray-700 mb-2">{highlight.text}</p>
              <p className="text-xs text-gray-500 italic">{highlight.reason}</p>
            </div>
          ))}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-4">
        <button
          onClick={handleDownload}
          className="flex-1 flex items-center justify-center gap-2 bg-blue-500 hover:bg-blue-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
        >
          <Download className="w-5 h-5" />
          Download Video
        </button>
        <button
          onClick={() => window.location.reload()}
          className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold py-3 px-6 rounded-lg transition-colors"
        >
          Process Another
        </button>
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}