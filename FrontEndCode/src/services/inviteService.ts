import { buildApiUrl, API_CONFIG } from '@/config/api';
import { fetchAuthSession } from 'aws-amplify/auth';

export interface SendInviteRequest {
  benefactor_email: string;
  invitee_email: string;
}

export interface SendInviteResponse {
  message: string;
  invite_token: string;
  sent_to: string;
}

export const sendInvite = async (request: SendInviteRequest): Promise<SendInviteResponse> => {
  try {
    // Get authentication token
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) {
      throw new Error('No authentication token available. Please log in again.');
    }

    // Make API call
    const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.SEND_INVITE), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
    
  } catch (error) {
    console.error('Error sending invite:', error);
    throw error;
  }
};