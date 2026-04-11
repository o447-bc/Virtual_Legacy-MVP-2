import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { shouldShowVideoPrompt } from '@/components/psych-tests/testUtils';

/**
 * Feature: psych-test-framework, Property 16: Video prompt trigger logic
 *
 * **Validates: Requirements 10.8**
 *
 * For any question index I ≥ 0 and videoPromptFrequency F > 0,
 * the video prompt should be shown if and only if I % F === 0.
 */
describe('Feature: psych-test-framework, Property 16: Video prompt trigger logic', () => {
  it('video prompt shown iff index % frequency === 0', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 10_000 }),
        fc.integer({ min: 1, max: 100 }),
        (index, frequency) => {
          const result = shouldShowVideoPrompt(index, frequency);
          const expected = index % frequency === 0;
          expect(result).toBe(expected);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('returns false when frequency is 0 or negative', () => {
    expect(shouldShowVideoPrompt(0, 0)).toBe(false);
    expect(shouldShowVideoPrompt(5, -1)).toBe(false);
  });
});
