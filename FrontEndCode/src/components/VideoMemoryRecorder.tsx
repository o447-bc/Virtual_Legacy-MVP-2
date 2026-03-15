import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { videoStorageService } from "@/services/videoService";
import { useAuth } from "@/contexts/AuthContext";

interface VideoMemoryRecorderProps {
  audioDetailedSummary: string;
  questionId: string;
  questionType: string;
  onComplete: () => void;
  onSkip: () => void;
  onDashboard: () => void;
}

type RecordingState = 'prompt' | 'preparing' | 'ready' | 'recording' | 'preview' | 'uploading';

const MAX_RECORDING_TIME = 120; // 2 minutes in seconds

const VideoMemoryRecorder: React.FC<VideoMemoryRecorderProps> = ({
  audioDetailedSummary,
  questionId,
  questionType,
  onComplete,
  onSkip,
  onDashboard
}) => {
  const [state, setState] = useState<RecordingState>('prompt');
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [error, setError] = useState<string | null>(null);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  
  const { user } = useAuth();

  // Cleanup camera on unmount
  useEffect(() => {
    return () => {
      cleanupCamera();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // Set video srcObject when stream changes
  useEffect(() => {
    if (stream && videoRef.current && !recordedBlob) {
      videoRef.current.srcObject = stream;
      videoRef.current.play();
    }
  }, [stream, recordedBlob]);

  const cleanupCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setStream(null);
  };

  const requestCameraAccess = async () => {
    setState('preparing');
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: true, 
        audio: true 
      });
      setStream(mediaStream);
      setError(null);
      setState('ready');
    } catch (err) {
      console.error("Camera access error:", err);
      setError("Camera access denied. Please allow camera and microphone access.");
      setState('prompt');
    }
  };

  const startRecording = () => {
    if (!stream) return;
    
    chunksRef.current = [];
    setRecordingTime(0);
    
    const mediaRecorder = new MediaRecorder(stream);
    
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        chunksRef.current.push(e.data);
      }
    };

    mediaRecorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: 'video/webm' });
      setRecordedBlob(blob);
      cleanupCamera();
      setState('preview');
    };

    mediaRecorder.start();
    mediaRecorderRef.current = mediaRecorder;
    setState('recording');
    
    // Start timer
    timerRef.current = setInterval(() => {
      setRecordingTime(prev => {
        if (prev >= MAX_RECORDING_TIME - 1) {
          stopRecording();
          return MAX_RECORDING_TIME;
        }
        return prev + 1;
      });
    }, 1000);
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && state === 'recording') {
      mediaRecorderRef.current.stop();
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  const startOver = () => {
    setRecordedBlob(null);
    setRecordingTime(0);
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    requestCameraAccess();
  };

  const redoRecording = () => {
    setRecordedBlob(null);
    setRecordingTime(0);
    requestCameraAccess();
  };

  const deleteAndSkip = () => {
    setRecordedBlob(null);
    cleanupCamera();
    onSkip();
  };

  const submitRecording = async () => {
    if (!recordedBlob || !user) return;

    setState('uploading');
    try {
      await videoStorageService.storeVideo({
        id: '',
        questionId,
        questionType,
        questionText: '',
        videoBlob: recordedBlob,
        timestamp: new Date(),
        userId: user.userId
      }, true); // isVideoMemory = true
      
      onComplete();
    } catch (error) {
      console.error("Error uploading video memory:", error);
      setError("Failed to upload video. Please try again.");
      setState('preview');
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // PROMPT STATE
  if (state === 'prompt') {
    return (
      <Card>
        <CardContent className="pt-6">
          <h3 className="text-xl font-semibold mb-4 text-center">
            Would you like to capture those thoughts in a video Memory?
          </h3>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}
          <div className="flex flex-col gap-3">
            <Button 
              onClick={requestCameraAccess}
              className="bg-legacy-purple hover:bg-legacy-navy"
            >
              Yes, let's record for prosperity
            </Button>
            <Button 
              onClick={onSkip}
              variant="outline"
            >
              No, next question
            </Button>
            <Button 
              onClick={onDashboard}
              variant="outline"
            >
              Back to Dashboard
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // PREPARING STATE
  if (state === 'preparing') {
    return (
      <Card>
        <CardContent className="pt-6 text-center">
          <p className="text-gray-600">Requesting camera access...</p>
        </CardContent>
      </Card>
    );
  }

  // READY, RECORDING, PREVIEW, UPLOADING STATES
  return (
    <div className="space-y-4">
      {/* Summary Text Box */}
      {(state === 'ready' || state === 'recording') && (
        <Card>
          <CardContent className="pt-6">
            <h4 className="font-medium mb-2">Your conversation summary:</h4>
            <div className="bg-gray-50 p-4 rounded max-h-32 overflow-y-auto text-sm">
              {audioDetailedSummary}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Video Display */}
      <Card>
        <CardContent className="pt-6">
          <div className="aspect-video w-full max-w-md mx-auto bg-black rounded-lg overflow-hidden relative">
            {!recordedBlob ? (
              <video 
                ref={videoRef} 
                autoPlay 
                playsInline 
                muted 
                className="w-full h-full object-cover flipped-video"
              />
            ) : (
              <video 
                src={URL.createObjectURL(recordedBlob)} 
                controls 
                className="w-full h-full object-cover"
              />
            )}
            
            {state === 'recording' && (
              <div className="absolute top-4 right-4 flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-red-500 animate-pulse" />
                <span className="text-white font-medium">Recording</span>
              </div>
            )}
            
            {state === 'uploading' && (
              <div className="absolute inset-0 bg-black bg-opacity-75 flex items-center justify-center">
                <div className="text-white text-2xl font-semibold">Uploading...</div>
              </div>
            )}
          </div>

          {/* Timer Progress Bar */}
          {state === 'recording' && (
            <div className="mt-4">
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>{formatTime(recordingTime)}</span>
                <span>{formatTime(MAX_RECORDING_TIME)}</span>
              </div>
              <Progress value={(recordingTime / MAX_RECORDING_TIME) * 100} />
            </div>
          )}

          {/* Buttons */}
          <div className="flex flex-wrap gap-3 mt-4">
            {state === 'ready' && (
              <>
                <Button 
                  onClick={startRecording}
                  className="flex-1 bg-legacy-purple hover:bg-legacy-navy"
                >
                  Start Recording
                </Button>
                <Button 
                  onClick={onSkip}
                  variant="outline"
                  className="flex-1"
                >
                  Go to next question
                </Button>
              </>
            )}

            {state === 'recording' && (
              <>
                <Button 
                  onClick={stopRecording}
                  className="flex-1 bg-green-600 hover:bg-green-700"
                >
                  Done
                </Button>
                <Button 
                  onClick={startOver}
                  variant="outline"
                  className="flex-1"
                >
                  Start Over
                </Button>
              </>
            )}

            {state === 'preview' && (
              <>
                <Button 
                  onClick={submitRecording}
                  className="flex-1 bg-legacy-purple hover:bg-legacy-navy"
                  disabled={state === 'uploading'}
                >
                  Submit
                </Button>
                <Button 
                  onClick={redoRecording}
                  variant="outline"
                  className="flex-1"
                >
                  Redo
                </Button>
                <Button 
                  onClick={deleteAndSkip}
                  variant="outline"
                  className="flex-1"
                >
                  Delete video, next question
                </Button>
              </>
            )}
          </div>

          {error && state === 'preview' && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mt-4">
              {error}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default VideoMemoryRecorder;
