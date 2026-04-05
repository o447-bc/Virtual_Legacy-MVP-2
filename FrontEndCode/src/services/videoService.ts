import { API_CONFIG } from '@/config/api';
import { fetchAuthSession, getCurrentUser } from 'aws-amplify/auth';

export interface Video {
  questionId: string;
  questionType: string;
  questionText: string;
  responseType: 'video' | 'audio' | 'video_memory';
  videoUrl: string | null;
  thumbnailUrl: string | null;
  audioUrl: string | null;
  oneSentence?: string | null;
  timestamp: string;
  filename: string;
}

export interface VideosByType {
  [questionType: string]: {
    friendlyName: string;
    videos: Video[];
  };
}

export interface VideoData {
  id: string;
  questionId: string;
  questionType: string;
  questionText: string;
  videoBlob: Blob;
  timestamp: Date;
  userId: string;
  instanceKey?: string;
}

export interface VideoUploadResponse {
  message: string;
  filename: string;
  s3Key: string;
  thumbnailFilename?: string;
  streakData?: {
    streakCount: number;
    streakFreezeAvailable: boolean;
    freezeUsed?: boolean;
  };
}

export const videoStorageService = {
  async getAudioSummaryForVideo(questionId: string): Promise<string> {
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) throw new Error('No authentication token');

    const response = await fetch(
      `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.GET_AUDIO_SUMMARY_FOR_VIDEO}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ questionId })
      }
    );

    if (!response.ok) {
      throw new Error('Failed to fetch audio summary');
    }

    const data = await response.json();
    return data.audioDetailedSummary || '';
  },

  async storeVideo(videoData: VideoData, isVideoMemory: boolean = false): Promise<VideoUploadResponse> {
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) throw new Error('No authentication token');

    // Step 1: Get pre-signed URL
    const urlResponse = await fetch(
      `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.GET_UPLOAD_URL}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          questionId: videoData.questionId,
          questionType: videoData.questionType
        })
      }
    );

    if (!urlResponse.ok) {
      throw new Error('Failed to get upload URL');
    }

    const { uploadUrl, s3Key, filename } = await urlResponse.json();

    // Step 2: Upload directly to S3
    const s3Response = await fetch(uploadUrl, {
      method: 'PUT',
      body: videoData.videoBlob,
      headers: {
        'Content-Type': 'video/webm'
      }
    });

    if (!s3Response.ok) {
      throw new Error('Failed to upload video to S3');
    }

    // Step 3: Process the video
    const processResponse = await fetch(
      `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.PROCESS_VIDEO}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          questionId: videoData.questionId,
          questionType: videoData.questionType,
          questionText: videoData.questionText,
          s3Key,
          filename,
          isVideoMemory,
          ...(videoData.instanceKey ? { instanceKey: videoData.instanceKey } : {}),
        })
      }
    );

    if (!processResponse.ok) {
      throw new Error('Failed to process video');
    }

    return await processResponse.json();
  }
};

export const getMakerVideos = async (makerId: string): Promise<VideosByType> => {
  const authSession = await fetchAuthSession();
  const idToken = authSession.tokens?.idToken?.toString();
  
  if (!idToken) throw new Error('No authentication token');

  const response = await fetch(
    `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.GET_MAKER_VIDEOS}/${makerId}`,
    { headers: { 'Authorization': `Bearer ${idToken}` } }
  );

  if (!response.ok) throw new Error('Failed to fetch videos');
  return await response.json();
};
