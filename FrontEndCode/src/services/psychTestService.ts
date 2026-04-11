import { buildApiUrl, API_CONFIG } from '@/config/api';
import { fetchAuthSession } from 'aws-amplify/auth';
import type {
  PsychTest,
  TestDefinition,
  TestProgress,
  TestResult,
  ExportResponse,
  QuestionResponse,
} from '@/types/psychTests';

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
// API Functions
// ---------------------------------------------------------------------------

/**
 * List all available psychological tests.
 * Includes `completedAt` for tests the user has already taken.
 */
export async function listPsychTests(): Promise<PsychTest[]> {
  const data = await authFetch<{ tests: PsychTest[] }>(
    buildApiUrl(API_CONFIG.ENDPOINTS.PSYCH_TESTS_LIST)
  );
  return data.tests;
}

/**
 * Fetch the full test definition JSON for a given test.
 */
export async function getTestDefinition(testId: string): Promise<TestDefinition> {
  return authFetch<TestDefinition>(
    buildApiUrl(`${API_CONFIG.ENDPOINTS.PSYCH_TEST_DEFINITION}/${testId}`)
  );
}

/**
 * Save in-progress test responses for later resume.
 */
export async function saveTestProgress(
  testId: string,
  responses: QuestionResponse[],
  currentQuestionIndex: number
): Promise<void> {
  await authFetch<void>(
    buildApiUrl(API_CONFIG.ENDPOINTS.PSYCH_TESTS_PROGRESS_SAVE),
    {
      method: 'POST',
      body: JSON.stringify({ testId, responses, currentQuestionIndex }),
    }
  );
}

/**
 * Get saved progress for a test. Returns null if no progress exists (404).
 */
export async function getTestProgress(testId: string): Promise<TestProgress | null> {
  try {
    return await authFetch<TestProgress>(
      buildApiUrl(`${API_CONFIG.ENDPOINTS.PSYCH_TESTS_PROGRESS_GET}/${testId}`)
    );
  } catch (error: unknown) {
    // Return null on 404 (no saved progress)
    if (error instanceof Error && error.message.includes('404')) {
      return null;
    }
    throw error;
  }
}

/**
 * Submit all responses for scoring.
 */
export async function scoreTest(
  testId: string,
  responses: QuestionResponse[]
): Promise<TestResult> {
  return authFetch<TestResult>(
    buildApiUrl(API_CONFIG.ENDPOINTS.PSYCH_TESTS_SCORE),
    {
      method: 'POST',
      body: JSON.stringify({ testId, responses }),
    }
  );
}

/**
 * Generate an export file and get a pre-signed download URL.
 */
export async function exportResults(
  testId: string,
  version: string,
  timestamp: string,
  format: string
): Promise<ExportResponse> {
  return authFetch<ExportResponse>(
    buildApiUrl(API_CONFIG.ENDPOINTS.PSYCH_TESTS_EXPORT),
    {
      method: 'POST',
      body: JSON.stringify({ testId, version, timestamp, format }),
    }
  );
}
