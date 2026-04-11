import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { calculateProgress } from '@/components/psych-tests/testUtils';

/**
 * Feature: psych-test-framework, Property 14: Progress percentage calculation
 *
 * **Validates: Requirements 10.3**
 *
 * For any total T > 0 and answered A where 0 ≤ A ≤ T,
 * the displayed progress percentage should equal Math.round((A / T) * 100).
 */
describe('Feature: psych-test-framework, Property 14: Progress percentage calculation', () => {
  it('progress equals Math.round((answered / total) * 100) for any valid inputs', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 10_000 }).chain((total) =>
          fc.integer({ min: 0, max: total }).map((answered) => ({
            total,
            answered,
          })),
        ),
        ({ total, answered }) => {
          const result = calculateProgress(answered, total);
          const expected = Math.round((answered / total) * 100);
          expect(result).toBe(expected);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('returns 0 when total is 0', () => {
    expect(calculateProgress(0, 0)).toBe(0);
  });

  it('returns 0 when total is negative', () => {
    expect(calculateProgress(5, -1)).toBe(0);
  });
});
