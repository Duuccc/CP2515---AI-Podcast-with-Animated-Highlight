'use client';

import { useEffect, useState } from 'react';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { getJobStatus, triggerProcessing } from '@/lib/api';
import { ProcessingStatusResponse, ProcessingStatus } from '@/types';

interface ProcessingStatusProps {
  jobId: string;
  onComplete: (status: ProcessingStatusResponse) => void;
}

export default function ProcessingStatusComponent({ jobId, onComplete }: ProcessingStatusProps) {
  const [status, setStatus] = useState<ProcessingStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Trigger processing start
    triggerProcessing(jobId).catch(console.error);

    // Poll for status updates
    const interval = setInterval(async () => {
      try {
        const response = await getJobStatus(jobId);
        setStatus(response);

        if (response.status === ProcessingStatus.COMPLETED) {
          clearInterval(interval);
          onComplete(response);
        } else if (response.status === ProcessingStatus.FAILED) {
          clearInterval(interval);
          setError(response.error || 'Processing failed');
        }
      } catch (err) {
        console.error('Status check failed:', err);
        setError('Failed to check status');
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [jobId, onComplete]);

  if (error) {
    return (
      <div className="w-full max-w-2xl mx-auto p-6 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center gap-3">
          <AlertCircle className="w-6 h-6 text-red-500" />
          <div>
            <h3 className="font-semibold text-red-900">Processing Failed</h3>
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="w-full max-w-2xl mx-auto p-6 text-center">
        <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-500" />
        <p className="mt-2 text-gray-600">Loading...</p>
      </div>
    );
  }

  const getStatusIcon = () => {
    if (status.status === ProcessingStatus.COMPLETED) {
      return <CheckCircle className="w-6 h-6 text-green-500" />;
    }
    return <Loader2 className="w-6 h-6 animate-spin text-blue-500" />;
  };

  const getStatusColor = () => {
    switch (status.status) {
      case ProcessingStatus.COMPLETED:
        return 'bg-green-50 border-green-200';
      case ProcessingStatus.FAILED:
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-blue-50 border-blue-200';
    }
  };

  return (
    <div className={`w-full max-w-2xl mx-auto p-6 border rounded-lg ${getStatusColor()}`}>
      <div className="flex items-center gap-3 mb-4">
        {getStatusIcon()}
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900">{status.message}</h3>
          <p className="text-sm text-gray-600">Status: {status.status}</p>
        </div>
        <span className="text-sm font-medium text-gray-700">{status.progress}%</span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
        <div
          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${status.progress}%` }}
        />
      </div>

      {/* Status Steps */}
      <div className="flex justify-between text-xs text-gray-500 mb-4">
        <span className={status.progress >= 25 ? 'text-blue-600 font-medium' : ''}>
          Transcribing
        </span>
        <span className={status.progress >= 50 ? 'text-blue-600 font-medium' : ''}>
          Analyzing
        </span>
        <span className={status.progress >= 75 ? 'text-blue-600 font-medium' : ''}>
          Generating
        </span>
        <span className={status.progress === 100 ? 'text-green-600 font-medium' : ''}>
          Complete
        </span>
      </div>
    </div>
  );
}