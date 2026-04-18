import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Mic, Square, Volume2 } from 'lucide-react';
import { fetchAuthSession } from 'aws-amplify/auth';
import { AudioVisualizer } from './AudioVisualizer';
import { UpgradePromptDialog } from './UpgradePromptDialog';
import { reportError } from '@/services/errorReporter';

const WS_URL = (import.meta.env.VITE_WS_URL || 'wss://tfdjq4d1r6.execute-api.us-east-1.amazonaws.com/prod').trim();

interface ConversationInterfaceProps {
  questionId: string;
  questionText: string;
  onComplete: (finalScore: number, audioTranscriptUrl: string, audioDetailedSummary: string) => void;
}

export const ConversationInterface: React.FC<ConversationInterfaceProps> = ({
  questionId,
  questionText,
  onComplete
}) => {
  const navigate = useNavigate();
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [status, setStatus] = useState<'idle' | 'connecting' | 'ready' | 'listening' | 'processing' | 'complete'>('idle');
  const [aiText, setAiText] = useState('');
  const [score, setScore] = useState(0);
  const [scoreGoal, setScoreGoal] = useState(12);
  const [turnNumber, setTurnNumber] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visualizerAudioUrl, setVisualizerAudioUrl] = useState<string | null>(null);
  const [isVisualizerPlaying, setIsVisualizerPlaying] = useState(false);
  const [isButtonDisabled, setIsButtonDisabled] = useState(false);
  const [showUpgradeDialog, setShowUpgradeDialog] = useState(false);
  const [upgradeMessage, setUpgradeMessage] = useState('');
  
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const uploadUrlRef = useRef<string | null>(null);
  const s3KeyRef = useRef<string | null>(null);

  const handleAudioEnd = useCallback(() => setIsVisualizerPlaying(false), []);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (ws) {
        ws.close();
        setWs(null);
      }
      if (mediaRecorderRef.current) mediaRecorderRef.current.stop();
    };
  }, []);

  const connectWebSocket = async () => {
    try {
      setStatus('connecting');
      const session = await fetchAuthSession();
      const token = session.tokens?.accessToken?.toString();
      
      if (!token) {
        setError('No authentication token');
        return;
      }

      const websocket = new WebSocket(`${WS_URL}?token=${token}`);
      
      websocket.onopen = () => {
        setStatus('ready');
        setWs(websocket);
        startConversation(websocket);
      };

      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleMessage(data);
        } catch (parseErr) {
          console.error('[WEBSOCKET] Failed to parse message, raw data:', event.data);
          setError('Received unexpected response from server. Please try again.');
          setStatus('ready');
          reportError({
            errorMessage: 'Failed to parse WebSocket message',
            component: 'ConversationInterface',
            url: window.location.href,
            errorType: 'WebSocketParseError',
          });
        }
      };

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('WebSocket connection error');
        setStatus('idle');
        reportError({
          errorMessage: 'WebSocket connection error',
          component: 'ConversationInterface',
          url: window.location.href,
          errorType: 'WebSocketError',
        });
      };

      websocket.onclose = (event) => {
        setStatus('idle');
        if (event.code !== 1000) {
          setError(`Connection closed unexpectedly (${event.code})`);
          reportError({
            errorMessage: `Connection closed unexpectedly (${event.code})`,
            component: 'ConversationInterface',
            url: window.location.href,
            errorType: 'WebSocketClose',
            metadata: { closeCode: event.code, closeReason: event.reason },
          });
        }
      };
    } catch (err) {
      setError('Failed to connect');
      setStatus('idle');
    }
  };

  const startConversation = (websocket: WebSocket) => {
    websocket.send(JSON.stringify({
      action: 'start_conversation',
      questionId,
      questionText
    }));
  };

  const handleMessage = (data: any) => {
    // Handle raw API Gateway error envelope (no 'type' field)
    if (!data.type && data.message) {
      console.error('[WEBSOCKET] Server error (no type):', data.message, data);
      setError(`Server error: ${data.message}. Please try again.`);
      setStatus('ready');
      return;
    }
    
    switch (data.type) {
      case 'upload_url':
        uploadUrlRef.current = data.uploadUrl;
        s3KeyRef.current = data.s3Key;
        break;
      
      case 'ai_speaking':
        setAiText(data.text);
        setScore(data.cumulativeScore || 0);
        setScoreGoal(data.scoreGoal || 12);
        setTurnNumber(data.turnNumber || 0);
        if (data.audioUrl) playAudioFromUrl(data.audioUrl);
        setStatus('ready');
        break;
      
      case 'score_update':
        setScore(data.cumulativeScore);
        setTurnNumber(data.turnNumber);
        setStatus('processing');
        break;
      
      case 'conversation_complete':
        setStatus('complete');
        onComplete(data.finalScore, data.audioTranscriptUrl, data.audioDetailedSummary || '');
        break;
      
      case 'conversation_ended':
        setStatus('complete');
        onComplete(data.finalScore, data.audioTranscriptUrl, data.audioDetailedSummary || '');
        break;
      
      case 'error':
        setError(data.message);
        setStatus('ready');
        break;
      
      case 'limit_reached':
        setUpgradeMessage(data.message || 'Upgrade to Premium to continue.');
        setShowUpgradeDialog(true);
        setStatus('ready');
        break;
    }
  };

  const playAudioFromUrl = async (audioUrl: string) => {
    try {
      setVisualizerAudioUrl(audioUrl);
      setIsVisualizerPlaying(true);
    } catch (err) {
      console.error('Error playing audio:', err);
    }
  };

  const startRecording = async () => {
    if (isButtonDisabled) return;
    
    try {
      // Disable button for 1 second to prevent double-clicks
      setIsButtonDisabled(true);
      setTimeout(() => setIsButtonDisabled(false), 1000);
      
      // Request upload URL first
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'get_upload_url' }));
      }
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await sendAudioResponse(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setStatus('listening');
    } catch (err) {
      setError('Microphone access denied');
      setIsButtonDisabled(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording && !isButtonDisabled) {
      // Disable button for 1 second to prevent double-clicks
      setIsButtonDisabled(true);
      setTimeout(() => setIsButtonDisabled(false), 1000);
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setStatus('processing');
    }
  };

  const sendAudioResponse = async (audioBlob: Blob) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not ready:', ws?.readyState);
      setError('Connection lost');
      setStatus('ready');
      return;
    }
    
    try {
      // Wait for upload URL if not ready yet (up to 10 seconds)
      let attempts = 0;
      while (!uploadUrlRef.current && attempts < 50) {
        await new Promise(resolve => setTimeout(resolve, 200));
        attempts++;
      }
      
      if (!uploadUrlRef.current || !s3KeyRef.current) {
        console.error('Upload URL not available');
        setError('Failed to get upload URL');
        setStatus('ready');
        return;
      }
      
      // Upload directly to S3
      const uploadResponse = await fetch(uploadUrlRef.current, {
        method: 'PUT',
        body: audioBlob,
        headers: {
          'Content-Type': 'audio/webm'
        }
      });
      
      if (!uploadResponse.ok) {
        throw new Error(`S3 upload failed: ${uploadResponse.status}`);
      }
      
      // Send S3 key to backend for processing
      ws.send(JSON.stringify({
        action: 'audio_response',
        s3Key: s3KeyRef.current
      }));
      
      // Clear refs for next recording
      uploadUrlRef.current = null;
      s3KeyRef.current = null;
      
    } catch (err) {
      console.error('Send audio error:', err);
      setError('Failed to upload audio');
      setStatus('ready');
    }
  };

  const endConversation = () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'end_conversation' }));
    }
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-6">
          {/* Score Progress */}
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">Conversation Depth</span>
            <span className="text-sm font-medium">{score}/{scoreGoal}</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-legacy-purple h-2 rounded-full transition-all"
              style={{ width: `${Math.min(100, (score / scoreGoal) * 100)}%` }}
            />
          </div>

          {/* AI Response */}
          <AudioVisualizer
            audioUrl={visualizerAudioUrl}
            isPlaying={isVisualizerPlaying}
            onAudioEnd={handleAudioEnd}
          />
          
          {aiText && (
            <p className="text-center text-gray-700 mt-4 px-4 max-w-2xl mx-auto text-balance">{aiText}</p>
          )}

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          {/* Tap-to-Speak / Tap-to-Send Button */}
          <div className="flex flex-col items-center gap-4">
            {status === 'ready' && !isRecording && (
              <Button
                onClick={startRecording}
                disabled={isButtonDisabled}
                className="bg-legacy-purple hover:bg-legacy-navy w-full sm:w-auto min-h-[60px] text-lg disabled:opacity-50 disabled:cursor-not-allowed"
                size="lg"
              >
                <Mic className="mr-2 h-6 w-6" />
                Tap to Speak
              </Button>
            )}

            {isRecording && (
              <Button
                onClick={stopRecording}
                disabled={isButtonDisabled}
                className="bg-red-600 hover:bg-red-700 w-full sm:w-auto min-h-[60px] text-lg animate-pulse disabled:opacity-50 disabled:cursor-not-allowed"
                size="lg"
              >
                <Square className="mr-2 h-6 w-6" />
                Tap to Send
              </Button>
            )}

            {turnNumber > 0 && status === 'ready' && (
              <Button
                onClick={endConversation}
                variant="outline"
                className="w-full sm:w-auto"
              >
                End Conversation
              </Button>
            )}
          </div>

          {/* Processing Status */}
          {status === 'processing' && (
            <div className="text-center text-gray-600">
              Processing your response...
            </div>
          )}

          {/* Status */}
          <div className="text-center text-sm text-gray-500">
            {status === 'listening' && 'Recording...'}
            {status === 'ready' && turnNumber > 0 && `Turn ${turnNumber}`}
          </div>
        </div>
      </CardContent>
      <UpgradePromptDialog
        open={showUpgradeDialog}
        onOpenChange={setShowUpgradeDialog}
        title="Upgrade to Premium"
        message={upgradeMessage}
        onUpgrade={() => {
          setShowUpgradeDialog(false);
          navigate('/pricing');
        }}
      />
    </Card>
  );
};
