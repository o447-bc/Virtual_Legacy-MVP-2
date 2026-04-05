
import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { videoStorageService } from "@/services/videoService";
import { useAuth } from "@/contexts/AuthContext";
import { ArrowRight } from "lucide-react";

interface VideoRecorderProps {
  onSkipQuestion?: () => void;
  canSkip?: boolean;
  currentQuestionId?: string;
  currentQuestionType?: string;
  currentQuestionText?: string;
  onRecordingSubmitted?: () => void;
}

const VideoRecorder: React.FC<VideoRecorderProps> = ({ 
  onSkipQuestion, 
  canSkip = true, 
  currentQuestionId, 
  currentQuestionType, 
  currentQuestionText,
  onRecordingSubmitted
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [permissionDenied, setPermissionDenied] = useState(false);
  const [recordingSaved, setRecordingSaved] = useState(false);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  
  const { user } = useAuth();

  // Clean up camera stream
  const cleanupCamera = () => {
    try {
      // Stop all tracks immediately
      if (stream) {
        stream.getTracks().forEach(track => {
          track.stop();
        });
      }
      
      // Clear video element
      if (videoRef.current) {
        videoRef.current.srcObject = null;
        videoRef.current.pause();
      }
      
      // Clear React state
      setStream(null);
      
    } catch (error) {
      console.error('Error stopping camera:', error);
    }
  };

  // Request camera and microphone access
  const requestMediaAccess = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: true, 
        audio: true 
      });
      setStream(mediaStream);
      setPermissionDenied(false);
      
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        videoRef.current.play();
      }
    } catch (err) {
      console.error("Error accessing media devices:", err);
      setPermissionDenied(true);
    }
  };

  // Initialize media access on component mount
  useEffect(() => {
    requestMediaAccess();
    
    // Clean up on unmount
    return () => {
      cleanupCamera();
    };
  }, []);

  // Start recording
  const startRecording = () => {
    if (!stream) {
      return;
    }
    
    setRecordingSaved(false);
    
    chunksRef.current = [];
    const mediaRecorder = new MediaRecorder(stream);
    
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        chunksRef.current.push(e.data);
      }
    };

    mediaRecorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: 'video/webm' });
      setRecordedBlob(blob);
    };

    mediaRecorder.start();
    mediaRecorderRef.current = mediaRecorder;
    setIsRecording(true);
  };

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // Submit recording
  const submitRecording = async () => {
    if (!recordedBlob || !user) {
      return;
    }

    setIsUploading(true);
    try {
      // Split composite questionId for instanced questions (e.g., "marriage-00001#got_married:1")
      let actualQuestionId = currentQuestionId;
      let instanceKey: string | undefined;
      if (currentQuestionId && currentQuestionId.includes('#')) {
        const parts = currentQuestionId.split('#');
        actualQuestionId = parts[0];
        instanceKey = parts[1];
      }

      await videoStorageService.storeVideo({
        id: '',
        questionId: actualQuestionId,
        questionType: currentQuestionType,
        questionText: currentQuestionText,
        videoBlob: recordedBlob,
        timestamp: new Date(),
        userId: user.userId,
        instanceKey,
      });
      
      setRecordingSaved(true);
      setRecordedBlob(null);
      
      // Turn off camera after successful submission
      cleanupCamera();
      
      // Call the submission handler to update progress
      if (onRecordingSubmitted) {
        onRecordingSubmitted();
      }
      
      // Auto-advance after showing success message
      setTimeout(() => {
        setRecordingSaved(false);
        // Move to next question (camera stays off)
        // Move to next question but don't restart camera
        if (onSkipQuestion) {
          onSkipQuestion();
        }
      }, 2000);
    } catch (error) {
      console.error("Error submitting video:", error);
    } finally {
      setIsUploading(false);
    }
  };

  // Skip current question
  const skipQuestion = () => {
    setRecordedBlob(null);
    // Restart camera stream for next question
    requestMediaAccess();
    
    if (onSkipQuestion) {
      onSkipQuestion();
    }
  };

  // Retry recording
  const retryRecording = () => {
    setRecordedBlob(null);
    // Restart camera stream
    requestMediaAccess();
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      {permissionDenied ? (
        <div className="text-center p-6 border border-red-300 rounded-lg bg-red-50">
          <h3 className="text-lg font-medium text-red-800">Camera Access Required</h3>
          <p className="mt-2 text-red-600">
            To record your responses, please allow access to your camera and microphone.
          </p>
          <Button 
            onClick={requestMediaAccess} 
            className="mt-4 bg-legacy-purple hover:bg-legacy-navy"
          >
            Request Access
          </Button>
        </div>
      ) : (
        <>
          <div className="aspect-video w-full bg-black rounded-lg overflow-hidden relative">
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
            
            {isRecording && (
              <div className="absolute top-4 right-4 flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-red-500 animate-pulse" />
                <span className="text-white font-medium">Recording</span>
              </div>
            )}
            
            {recordingSaved && (
              <div className="absolute inset-0 bg-black bg-opacity-75 flex items-center justify-center">
                <div className="text-white text-2xl font-semibold">Recording Saved</div>
              </div>
            )}
          </div>

          <div className="flex flex-wrap justify-between gap-4 mt-6">
            {!isRecording && !recordedBlob ? (
              <>
                <Button 
                  onClick={startRecording} 
                  className="flex-1 bg-legacy-purple hover:bg-legacy-navy"
                >
                  Start Recording
                </Button>
                {canSkip && (
                  <Button 
                    onClick={skipQuestion}
                    variant="outline"
                    className="flex-1 border-legacy-purple text-legacy-purple hover:bg-legacy-lightPurple"
                  >
                    Skip Question <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                )}
              </>
            ) : isRecording ? (
              <Button 
                onClick={stopRecording} 
                variant="destructive"
                className="w-full"
              >
                Stop Recording
              </Button>
            ) : (
              <>
                <Button 
                  onClick={submitRecording} 
                  className="flex-1 bg-legacy-purple hover:bg-legacy-navy"
                  disabled={isUploading}
                >
                  {isUploading ? "Submitting..." : "Submit Response"}
                </Button>
                <Button 
                  onClick={retryRecording}
                  variant="outline"
                  className="flex-1"
                >
                  Record Again
                </Button>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default VideoRecorder;
