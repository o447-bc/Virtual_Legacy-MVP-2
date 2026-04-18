/**
 * Property-based tests for the Error Reporter module.
 *
 * Feature: error-logging-monitoring
 * Property 9: Rate limiter caps reports
 *
 * Validates: Requirements 3.6
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import fc from 'fast-check';

// Mock aws-amplify/auth before importing errorReporter
vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: vi.fn().mockResolvedValue({
    tokens: { idToken: { toString: () => 'mock-token' } },
  }),
}));

// Mock api config to avoid env var validation
vi.mock('@/config/api', () => ({
  API_CONFIG: {
    BASE_URL: 'https://test-api.example.com',
    ENDPOINTS: { LOG_ERROR: '/log-error' },
  },
  buildApiUrl: (endpoint: string) => `https://test-api.example.com${endpoint}`,
}));

// Mock fetch globally
const mockFetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
vi.stubGlobal('fetch', mockFetch);

// Import after mocks are set up
import { reportError, _testing, getCorrelationId } from '@/services/errorReporter';

// ---------------------------------------------------------------------------
// Property 9: Rate limiter caps reports
// Feature: error-logging-monitoring, Property 9
// Validates: Requirements 3.6
// ---------------------------------------------------------------------------

describe('Error Reporter — Rate Limiter', () => {
  beforeEach(() => {
    mockFetch.mockClear();
    // Clear the rate limiter state
    _testing.reportTimestamps.length = 0;
  });

  it('Property 9: only first 10 reports in a 60-second window trigger fetch calls', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 11, max: 50 }),
        async (reportCount) => {
          // Reset state
          mockFetch.mockClear();
          _testing.reportTimestamps.length = 0;

          // Fire N reports synchronously
          for (let i = 0; i < reportCount; i++) {
            reportError({
              errorMessage: `Error ${i}`,
              component: 'TestComponent',
              url: 'https://example.com/test',
            });
          }

          // Wait for async sends to complete
          await new Promise((r) => setTimeout(r, 100));

          // Only the first 10 should have triggered fetch
          expect(mockFetch).toHaveBeenCalledTimes(10);
        },
      ),
      { numRuns: 20 },
    );
  });

  it('allows reports under the limit', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 1, max: 10 }),
        async (reportCount) => {
          mockFetch.mockClear();
          _testing.reportTimestamps.length = 0;

          for (let i = 0; i < reportCount; i++) {
            reportError({
              errorMessage: `Error ${i}`,
              component: 'TestComponent',
              url: 'https://example.com/test',
            });
          }

          await new Promise((r) => setTimeout(r, 100));

          expect(mockFetch).toHaveBeenCalledTimes(reportCount);
        },
      ),
      { numRuns: 20 },
    );
  });

  it('getCorrelationId returns a valid UUID-like string', () => {
    const id = getCorrelationId();
    expect(id).toBeTruthy();
    expect(typeof id).toBe('string');
    expect(id.length).toBeGreaterThan(0);
  });
});
