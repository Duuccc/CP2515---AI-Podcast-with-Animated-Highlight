'use client';

import { useState } from 'react';
import { Download, Play, ExternalLink, AlertCircle, Loader2 } from 'lucide-react';
import { ProcessingStatusResponse } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface HighlightPreviewProps {
  status: ProcessingStatusResponse;
}

export default function HighlightPreview({ status }: HighlightPreviewProps) {
  const [loadingVideos, setLoadingVideos] = useState<Set<number>>(new Set());
  const [videoErrors, setVideoErrors] = useState<Set<number>>(new Set());

  // Debug: Log the status to see what we're receiving
  console.log('HighlightPreview - Status:', status);
  console.log('HighlightPreview - Video URLs:', status.video_urls);
  console.log('HighlightPreview - Highlights:', status.highlights);

  const handleDownload = (videoUrl: string, index: number) => {
    // Create download link
    const link = document.createElement('a');
    link.href = `${API_URL}${videoUrl}`;
    link.download = `highlight_${index + 1}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadAll = () => {
    if (status.video_urls) {
      status.video_urls.forEach((url, index) => {
        setTimeout(() => handleDownload(url, index), index * 500);
      });
    }
  };

  // Check if we have videos or highlights
  const hasVideos = status.video_urls && status.video_urls.length > 0;
  const hasHighlights = status.highlights && status.highlights.length > 0;

  return (
    <div className="w-full max-w-4xl mx-auto">
      <h2 className="text-3xl font-bold text-gray-900 mb-6">Your Highlight Videos</h2>

      {/* Error or Empty State */}
      {!hasVideos && !hasHighlights && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-6 h-6 text-yellow-600" />
            <div>
              <h3 className="font-semibold text-yellow-900">No highlights found</h3>
              <p className="text-sm text-yellow-700">
                The processing completed but no highlight videos were generated. 
                This might happen if the audio was too short or no interesting segments were detected.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Video Grid */}
      {hasVideos && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {status.video_urls.map((videoUrl, index) => (
            <div
              key={index}
              className="bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow"
            >
              {/* Video Player */}
              <div className="bg-gray-900 aspect-[9/16] relative group">
                {loadingVideos.has(index) && (
                  <div className="absolute inset-0 flex items-center justify-center z-10">
                    <Loader2 className="w-12 h-12 text-white animate-spin" />
                  </div>
                )}
                {videoErrors.has(index) ? (
                  <div className="absolute inset-0 flex items-center justify-center bg-gray-800">
                    <div className="text-center text-white p-4">
                      <AlertCircle className="w-12 h-12 mx-auto mb-2 text-red-400" />
                      <p className="text-sm">Video failed to load</p>
                      <a
                        href={`${API_URL}${videoUrl}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-400 hover:underline text-xs mt-2 inline-block"
                      >
                        Open in new tab
                      </a>
                    </div>
                  </div>
                ) : (
                  <video
                    controls
                    className="w-full h-full object-contain"
                    src={`${API_URL}${videoUrl}`}
                    preload="metadata"
                    playsInline
                    onLoadStart={() => {
                      setLoadingVideos(prev => new Set(prev).add(index));
                    }}
                    onCanPlay={() => {
                      setLoadingVideos(prev => {
                        const newSet = new Set(prev);
                        newSet.delete(index);
                        return newSet;
                      });
                    }}
                    onError={() => {
                      setLoadingVideos(prev => {
                        const newSet = new Set(prev);
                        newSet.delete(index);
                        return newSet;
                      });
                      setVideoErrors(prev => new Set(prev).add(index));
                    }}
                  >
                    Your browser does not support video playback.
                  </video>
                )}
                
                {/* Overlay on hover */}
                {!videoErrors.has(index) && (
                  <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100 pointer-events-none">
                    <Play className="w-16 h-16 text-white" />
                  </div>
                )}
              </div>

              {/* Video Info */}
              <div className="p-4">
                <h3 className="font-semibold text-gray-900 mb-2">
                  Highlight #{index + 1}
                </h3>
                {status.highlights && status.highlights[index] && (
                  <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                    {status.highlights[index].text}
                  </p>
                )}
                
                {/* Download Button */}
                <button
                  onClick={() => handleDownload(videoUrl, index)}
                  className="w-full flex items-center justify-center gap-2 bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Download
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Highlights Text List */}
      {hasHighlights && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h3 className="text-xl font-semibold text-gray-800 mb-4">Highlight Details</h3>
          <div className="space-y-4">
            {status.highlights!.map((highlight, index) => (
              <div
                key={index}
                className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors"
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="text-sm font-medium text-blue-600">
                    {formatTime(highlight.start_time)} - {formatTime(highlight.end_time)}
                  </span>
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                    {Math.round((highlight.confidence || 0) * 100)}% confidence
                  </span>
                </div>
                <p className="text-gray-700 mb-2">{highlight.text}</p>
                {highlight.reason && (
                  <p className="text-xs text-gray-500 italic">{highlight.reason}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Transcript Section */}
      {status.transcript && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h3 className="text-xl font-semibold text-gray-800 mb-4">Full Transcript</h3>
          <div className="max-h-64 overflow-y-auto">
            <p className="text-gray-700 whitespace-pre-wrap text-sm leading-relaxed">
              {status.transcript}
            </p>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-4">
        {hasVideos && status.video_urls!.length > 1 && (
          <button
            onClick={handleDownloadAll}
            className="flex-1 flex items-center justify-center gap-2 bg-green-500 hover:bg-green-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
          >
            <Download className="w-5 h-5" />
            Download All ({status.video_urls!.length} videos)
          </button>
        )}
        <button
          onClick={() => window.location.reload()}
          className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold py-3 px-6 rounded-lg transition-colors"
        >
          Process Another Podcast
        </button>
      </div>

      {/* Share Tips */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h4 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
          <ExternalLink className="w-5 h-5" />
          Ready to Share!
        </h4>
        <p className="text-sm text-blue-700">
          Your videos are optimized for:
        </p>
        <ul className="mt-2 text-sm text-blue-700 space-y-1">
          <li>✅ TikTok (9:16 vertical format)</li>
          <li>✅ Instagram Reels (perfect dimensions)</li>
          <li>✅ YouTube Shorts (ready to upload)</li>
        </ul>
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}