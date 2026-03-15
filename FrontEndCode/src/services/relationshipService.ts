import { buildApiUrl, API_CONFIG } from '@/config/api';
import { fetchAuthSession } from 'aws-amplify/auth';

export interface Relationship {
  initiator_id: string;
  related_user_id: string;
  related_user_email?: string;
  related_user_first_name?: string;
  related_user_last_name?: string;
  relationship_type: string;
  status: string;
  created_at: string;
  created_via: string;
}

export interface GetRelationshipsResponse {
  relationships: Relationship[];
}

export const getRelationships = async (userId: string): Promise<GetRelationshipsResponse> => {
  try {
    // Get authentication token
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) {
      throw new Error('No authentication token available. Please log in again.');
    }

    // Make API call
    const response = await fetch(`${buildApiUrl('/relationships')}?userId=${userId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`
      }
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
    
  } catch (error) {
    console.error('Error fetching relationships:', error);
    throw error;
  }
};