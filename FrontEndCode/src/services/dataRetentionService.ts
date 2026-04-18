import { buildApiUrl, API_CONFIG } from '@/config/api';
import { fetchAuthSession } from 'aws-amplify/auth';
import { getCorrelationId } from '@/services/errorReporter';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ExportResponse {
  status: 'processing' | 'ready' | 'pending_retrieval';
  downloadUrl?: string;
  message?: string;
}

export interface ExportStatusResponse {
  status: 'pending' | 'processing' | 'ready' | 'expired' | 'failed' | 'pending_retrieval';
  downloadUrl?: string;
  createdAt?: string;
  updatedAt?: string;
  message?: string;
}

export interface DeletionResponse {
  status: 'pending';
  graceEndDate: string;
  message?: string;
}

export interface DeletionStatusResponse {
  status: 'pending' | 'completed' | 'canceled' | null;
  graceEndDate?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface CancelDeletionResponse {
  status: 'canceled';
  message?: string;
}

export interface LegacyProtectionResponse {
  status: 'active';
  message?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function getIdToken(): Promise<string> {
  const authSession = await fetchAuthSession();
  const idToken = authSession.tokens?.idToken?.toString();
  if (!idToken) {
    throw new Error('No authentication token available. Please log in again.');
  }
  return idToken;
}

async function authFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  const idToken = await getIdToken();
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${idToken}`,
      'X-Correlation-ID': getCorrelationId(),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.error || `HTTP ${response.status}: ${response.statusText}`
    );
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Export endpoints
// ---------------------------------------------------------------------------

/**
 * Request a full Content_Package export (Premium only).
 */
export const requestDataExport = async (): Promise<ExportResponse> => {
  return authFetch<ExportResponse>(
    buildApiUrl(API_CONFIG.ENDPOINTS.DATA_EXPORT_REQUEST),
    { method: 'POST' }
  );
};

/**
 * Request a lightweight GDPR text-only export (all users).
 */
export const requestGdprExport = async (): Promise<ExportResponse> => {
  return authFetch<ExportResponse>(
    buildApiUrl(API_CONFIG.ENDPOINTS.DATA_GDPR_EXPORT),
    { method: 'POST' }
  );
};

/**
 * Get the current export status.
 */
export const getExportStatus = async (): Promise<ExportStatusResponse> => {
  return authFetch<ExportStatusResponse>(
    buildApiUrl(API_CONFIG.ENDPOINTS.DATA_EXPORT_STATUS),
    { method: 'GET' }
  );
};

// ---------------------------------------------------------------------------
// Deletion endpoints
// ---------------------------------------------------------------------------

/**
 * Request account deletion (starts 30-day grace period).
 */
export const requestAccountDeletion = async (): Promise<DeletionResponse> => {
  return authFetch<DeletionResponse>(
    buildApiUrl(API_CONFIG.ENDPOINTS.ACCOUNT_DELETE_REQUEST),
    { method: 'POST' }
  );
};

/**
 * Cancel a pending account deletion during the grace period.
 */
export const cancelAccountDeletion =
  async (): Promise<CancelDeletionResponse> => {
    return authFetch<CancelDeletionResponse>(
      buildApiUrl(API_CONFIG.ENDPOINTS.ACCOUNT_CANCEL_DELETION),
      { method: 'POST' }
    );
  };

/**
 * Get the current deletion request status.
 */
export const getDeletionStatus =
  async (): Promise<DeletionStatusResponse> => {
    return authFetch<DeletionStatusResponse>(
      buildApiUrl(API_CONFIG.ENDPOINTS.ACCOUNT_DELETION_STATUS),
      { method: 'GET' }
    );
  };

// ---------------------------------------------------------------------------
// Legacy protection endpoint
// ---------------------------------------------------------------------------

/**
 * Request legacy protection for a maker (benefactor-initiated).
 */
export const requestLegacyProtection = async (
  legacyMakerId: string,
  reason?: string
): Promise<LegacyProtectionResponse> => {
  return authFetch<LegacyProtectionResponse>(
    buildApiUrl(API_CONFIG.ENDPOINTS.LEGACY_PROTECTION_REQUEST),
    {
      method: 'POST',
      body: JSON.stringify({ legacyMakerId, reason }),
    }
  );
};
