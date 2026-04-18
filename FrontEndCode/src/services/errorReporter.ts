/**
 * Error Reporter — silently sends error details to POST /log-error.
 *
 * Generates a session-scoped correlation ID and attaches it to every
 * error report and outgoing API request (via getCorrelationId()).
 *
 * Features:
 * - Rate limiting: max 10 reports per 60-second sliding window
 * - Silent failure: never throws, never shows UI errors
 * - Auth-gated: only sends when a valid Cognito session exists
 * - PII-safe: never includes form field values or user content
 *
 * Requirements: 3.1, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
 */
import { fetchAuthSession } from 'aws-amplify/auth';
import { buildApiUrl, API_CONFIG } from '@/config/api';

// ---------------------------------------------------------------------------
// Correlation ID (session-scoped)
// ---------------------------------------------------------------------------

function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  // Fallback for older browsers
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

const correlationId: string = generateUUID();

export function getCorrelationId(): string {
  return correlationId;
}

// ---------------------------------------------------------------------------
// Rate limiter (sliding window)
// ---------------------------------------------------------------------------

const MAX_REPORTS = 10;
const WINDOW_MS = 60_000;
const reportTimestamps: number[] = [];

function isRateLimited(): boolean {
  const now = Date.now();
  // Remove timestamps outside the window
  while (reportTimestamps.length > 0 && reportTimestamps[0] <= now - WINDOW_MS) {
    reportTimestamps.shift();
  }
  return reportTimestamps.length >= MAX_REPORTS;
}

function recordReport(): void {
  reportTimestamps.push(Date.now());
}

// ---------------------------------------------------------------------------
// Error report interface
// ---------------------------------------------------------------------------

export interface ErrorReport {
  errorMessage: string;
  component: string;
  url: string;
  stackTrace?: string;
  errorType?: string;
  metadata?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Core reporter (fire-and-forget)
// ---------------------------------------------------------------------------

export function reportError(report: ErrorReport): void {
  // Never throw — wrap everything in try/catch
  try {
    if (isRateLimited()) return;
    recordReport();

    // Fire-and-forget async send
    _sendReport(report).catch(() => {
      // Silently discard network failures
    });
  } catch {
    // Silently discard any unexpected errors
  }
}

async function _sendReport(report: ErrorReport): Promise<void> {
  // Check auth — discard if not authenticated
  let idToken: string;
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    if (!token) return; // Not authenticated, discard
    idToken = token;
  } catch {
    return; // Auth check failed, discard
  }

  const url = buildApiUrl(API_CONFIG.ENDPOINTS.LOG_ERROR);

  await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${idToken}`,
      'X-Correlation-ID': correlationId,
    },
    body: JSON.stringify({
      errorMessage: report.errorMessage,
      component: report.component,
      url: report.url,
      stackTrace: report.stackTrace,
      errorType: report.errorType,
      metadata: report.metadata,
    }),
  });
}

// ---------------------------------------------------------------------------
// Export internals for testing
// ---------------------------------------------------------------------------

export const _testing = {
  reportTimestamps,
  MAX_REPORTS,
  WINDOW_MS,
};
