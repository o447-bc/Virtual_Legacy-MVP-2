import { buildApiUrl } from '@/config/api';
import { fetchAuthSession } from 'aws-amplify/auth';

export interface AccessCondition {
  condition_type: 'immediate' | 'time_delayed' | 'inactivity_trigger' | 'manual_release';
  activation_date?: string; // ISO 8601 for time_delayed
  inactivity_months?: number; // for inactivity_trigger
  check_in_interval_days?: number;
  last_check_in?: string;
  consecutive_missed_check_ins?: number;
  condition_id?: string;
  status?: string;
  released_at?: string;
  released_by?: string;
}

export interface Assignment {
  initiator_id: string;
  related_user_id: string;
  benefactor_email?: string;
  benefactor_first_name?: string;
  benefactor_last_name?: string;
  maker_email?: string;
  maker_first_name?: string;
  maker_last_name?: string;
  account_status?: 'registered' | 'invitation_pending';
  assignment_status: 'pending' | 'active' | 'declined' | 'revoked' | 'expired';
  access_conditions: AccessCondition[];
  created_at: string;
  updated_at?: string;
  relationship_type?: string;
}

export interface CreateAssignmentRequest {
  benefactor_email: string;
  access_conditions: AccessCondition[];
}

export interface CreateAssignmentResponse {
  message: string;
  assignment_id: string;
  status: string;
  benefactor_registered: boolean;
  invitation_sent: boolean;
  invitation_token?: string;
  conditions_created: number;
}

export interface GetAssignmentsResponse {
  assignments: Assignment[];
  count: number;
}

export interface UpdateAssignmentRequest {
  action: 'update_conditions' | 'revoke' | 'delete';
  related_user_id: string;
  access_conditions?: AccessCondition[];
}

export interface UpdateAssignmentResponse {
  success: boolean;
  message: string;
  conditions_deleted?: number;
  conditions_created?: number;
  notification_sent?: boolean;
}

export interface AcceptDeclineAssignmentRequest {
  action: 'accept' | 'decline';
  initiator_id: string;
}

export interface AcceptDeclineAssignmentResponse {
  success: boolean;
  message: string;
  status: string;
  notification_sent: boolean;
}

export interface ResendInvitationRequest {
  related_user_id?: string;
  benefactor_email?: string;
}

export interface ResendInvitationResponse {
  success: boolean;
  message: string;
  invitation_token: string;
  email_sent: boolean;
  benefactor_email: string;
}

export interface ManualReleaseResponse {
  success: boolean;
  message: string;
  summary: {
    total_conditions: number;
    already_released: number;
    newly_released: number;
    notifications_sent: number;
    errors: number;
  };
  details: Array<{
    benefactor_email: string;
    status: 'released' | 'already_released' | 'error';
    notification_sent: boolean;
    error?: string;
    released_at?: string;
  }>;
}

/**
 * Create a new benefactor assignment with access conditions.
 * 
 * @param benefactorEmail - Email address of the benefactor
 * @param accessConditions - Array of access condition configurations
 * @returns Promise with assignment creation result
 */
export const createAssignment = async (
  benefactorEmail: string,
  accessConditions: AccessCondition[]
): Promise<CreateAssignmentResponse> => {
  try {
    // Get authentication token
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) {
      throw new Error('No authentication token available. Please log in again.');
    }

    // Make API call
    const response = await fetch(buildApiUrl('/assignments'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`
      },
      body: JSON.stringify({
        benefactor_email: benefactorEmail,
        access_conditions: accessConditions
      })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
    
  } catch (error) {
    console.error('Error creating assignment:', error);
    throw error;
  }
};

/**
 * Get all assignments for a Legacy Maker.
 * 
 * @param userId - Optional user ID (defaults to current user from JWT)
 * @returns Promise with list of assignments
 */
export const getAssignments = async (userId?: string): Promise<GetAssignmentsResponse> => {
  try {
    // Get authentication token
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) {
      throw new Error('No authentication token available. Please log in again.');
    }

    // Build URL with optional userId parameter
    const url = userId 
      ? `${buildApiUrl('/assignments')}?userId=${userId}`
      : buildApiUrl('/assignments');

    // Make API call
    const response = await fetch(url, {
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
    console.error('Error fetching assignments:', error);
    throw error;
  }
};

/**
 * Get all assignments where the current user is the benefactor.
 * This queries assignments from Legacy Makers who have assigned the current user.
 * 
 * @returns Promise with list of assignments where user is the benefactor
 */
export const getBenefactorAssignments = async (): Promise<GetAssignmentsResponse> => {
  try {
    // Get authentication token
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) {
      throw new Error('No authentication token available. Please log in again.');
    }

    // Make API call with asBeneficiary parameter
    const response = await fetch(`${buildApiUrl('/assignments')}?asBeneficiary=true`, {
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
    console.error('Error fetching benefactor assignments:', error);
    throw error;
  }
};

/**
 * Update an existing assignment (update conditions, revoke, or delete).
 * 
 * @param action - Action to perform: 'update_conditions', 'revoke', or 'delete'
 * @param relatedUserId - ID of the benefactor
 * @param accessConditions - New access conditions (required for 'update_conditions')
 * @returns Promise with update result
 */
export const updateAssignment = async (
  action: 'update_conditions' | 'revoke' | 'delete',
  relatedUserId: string,
  accessConditions?: AccessCondition[]
): Promise<UpdateAssignmentResponse> => {
  try {
    // Get authentication token
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) {
      throw new Error('No authentication token available. Please log in again.');
    }

    // Build request body
    const requestBody: UpdateAssignmentRequest = {
      action,
      related_user_id: relatedUserId
    };

    if (action === 'update_conditions' && accessConditions) {
      requestBody.access_conditions = accessConditions;
    }

    // Make API call
    const response = await fetch(buildApiUrl('/assignments'), {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
    
  } catch (error) {
    console.error('Error updating assignment:', error);
    throw error;
  }
};

/**
 * Accept a benefactor assignment.
 * 
 * @param initiatorId - ID of the Legacy Maker who created the assignment
 * @returns Promise with acceptance result
 */
export const acceptAssignment = async (
  initiatorId: string
): Promise<AcceptDeclineAssignmentResponse> => {
  try {
    // Get authentication token
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) {
      throw new Error('No authentication token available. Please log in again.');
    }

    // Make API call
    const response = await fetch(buildApiUrl('/assignments/respond'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`
      },
      body: JSON.stringify({
        action: 'accept',
        initiator_id: initiatorId
      })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
    
  } catch (error) {
    console.error('Error accepting assignment:', error);
    throw error;
  }
};

/**
 * Decline a benefactor assignment.
 * 
 * @param initiatorId - ID of the Legacy Maker who created the assignment
 * @returns Promise with decline result
 */
export const declineAssignment = async (
  initiatorId: string
): Promise<AcceptDeclineAssignmentResponse> => {
  try {
    // Get authentication token
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) {
      throw new Error('No authentication token available. Please log in again.');
    }

    // Make API call
    const response = await fetch(buildApiUrl('/assignments/respond'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`
      },
      body: JSON.stringify({
        action: 'decline',
        initiator_id: initiatorId
      })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
    
  } catch (error) {
    console.error('Error declining assignment:', error);
    throw error;
  }
};

/**
 * Resend invitation email to an unregistered benefactor.
 * 
 * @param relatedUserId - ID of the benefactor (pending#email format) or email address
 * @returns Promise with resend result
 */
export const resendInvitation = async (
  relatedUserId: string
): Promise<ResendInvitationResponse> => {
  try {
    // Get authentication token
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) {
      throw new Error('No authentication token available. Please log in again.');
    }

    // Make API call
    const response = await fetch(buildApiUrl('/assignments/resend-invitation'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`
      },
      body: JSON.stringify({
        related_user_id: relatedUserId
      })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
    
  } catch (error) {
    console.error('Error resending invitation:', error);
    throw error;
  }
};

/**
 * Manually release content to all benefactors with manual_release conditions.
 * 
 * @returns Promise with manual release result and summary
 */
export const manualRelease = async (): Promise<ManualReleaseResponse> => {
  try {
    // Get authentication token
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) {
      throw new Error('No authentication token available. Please log in again.');
    }

    // Make API call
    const response = await fetch(buildApiUrl('/assignments/manual-release'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`
      },
      body: JSON.stringify({})
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
    
  } catch (error) {
    console.error('Error triggering manual release:', error);
    throw error;
  }
};

export interface UnmetCondition {
  condition_type: string;
  reason: string;
  activation_date?: string;
  inactivity_months?: number;
}

export interface ValidateAccessResponse {
  hasAccess: boolean;
  reason: 'self_access' | 'relationship_access' | 'reverse_relationship_access' | 'conditions_not_met' | 'no_relationship' | 'expired';
  unmet_conditions?: UnmetCondition[];
  relationship?: any;
}

/**
 * Validate if the current user has access to a Legacy Maker's content.
 * 
 * @param requestingUserId - ID of the user requesting access (benefactor)
 * @param targetUserId - ID of the Legacy Maker whose content is being accessed
 * @returns Promise with access validation result
 */
export const validateAccess = async (
  requestingUserId: string,
  targetUserId: string
): Promise<ValidateAccessResponse> => {
  try {
    // Get authentication token
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();
    
    if (!idToken) {
      throw new Error('No authentication token available. Please log in again.');
    }

    // Make API call
    const response = await fetch(
      `${buildApiUrl('/relationships/validate')}?requestingUserId=${requestingUserId}&targetUserId=${targetUserId}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${idToken}`
        }
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
    
  } catch (error) {
    console.error('Error validating access:', error);
    throw error;
  }
};
