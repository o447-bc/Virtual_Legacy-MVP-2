import { describe, it, expect, vi } from 'vitest';

// Mock aws-amplify/auth before importing adminService
vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: vi.fn().mockResolvedValue({
    tokens: { idToken: { toString: () => 'mock-token' } },
  }),
}));

// Mock the api config to avoid VITE_API_BASE_URL validation error
vi.mock('@/config/api', () => ({
  API_CONFIG: { BASE_URL: 'https://test-api.example.com' },
  buildApiUrl: (endpoint: string) => `https://test-api.example.com${endpoint}`,
}));

import type { QuestionRecord } from '@/services/adminService';
import { applyThemeDefaults } from '@/services/adminService';

// ---------------------------------------------------------------------------
// Task 7.2: Unit tests for adminService.ts changes
// Requirements: 2.7, 2.9
// ---------------------------------------------------------------------------

describe('QuestionRecord interface accepts promptDescription', () => {
  it('accepts an object with promptDescription field', () => {
    const record: QuestionRecord = {
      questionId: 'childhood-1',
      questionType: 'childhood',
      themeName: 'Childhood Memories',
      difficulty: 1,
      Valid: 1,
      questionText: 'What is your earliest memory?',
      requiredLifeEvents: [],
      isInstanceable: false,
      instancePlaceholder: '',
      promptDescription: 'Focus on early childhood experiences',
      lastModifiedBy: 'admin@test.com',
      lastModifiedAt: '2025-01-01T00:00:00Z',
    };
    expect(record.promptDescription).toBe('Focus on early childhood experiences');
  });

  it('accepts an object without promptDescription field (optional)', () => {
    const record: QuestionRecord = {
      questionId: 'childhood-1',
      questionType: 'childhood',
      themeName: 'Childhood Memories',
      difficulty: 1,
      Valid: 1,
      questionText: 'What is your earliest memory?',
      requiredLifeEvents: [],
      isInstanceable: false,
      instancePlaceholder: '',
      lastModifiedBy: 'admin@test.com',
      lastModifiedAt: '2025-01-01T00:00:00Z',
    };
    expect(record.promptDescription).toBeUndefined();
  });
});

describe('applyThemeDefaults includes promptDescription', () => {

  it('includes promptDescription in the request body when provided', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ message: 'Updated', questionsUpdated: 3 }),
    });
    vi.stubGlobal('fetch', mockFetch);

    await applyThemeDefaults('childhood', {
      requiredLifeEvents: ['school'],
      isInstanceable: false,
      instancePlaceholder: '',
      promptDescription: 'Focus on early childhood',
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [, options] = mockFetch.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.promptDescription).toBe('Focus on early childhood');
  });

  it('works without promptDescription (backward compatibility)', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ message: 'Updated', questionsUpdated: 3 }),
    });
    vi.stubGlobal('fetch', mockFetch);

    await applyThemeDefaults('childhood', {
      requiredLifeEvents: ['school'],
      isInstanceable: false,
      instancePlaceholder: '',
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [, options] = mockFetch.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body).not.toHaveProperty('promptDescription');
  });
});
