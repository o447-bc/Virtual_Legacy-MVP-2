import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { controlKindForResponseType } from '@/components/psych-tests/testUtils';

/**
 * Feature: psych-test-framework, Property 18: Response type renders correct control
 *
 * **Validates: Requirements 10.2**
 *
 * For any question with responseType R, the rendered control type is:
 * Likert scale for "likert5", bipolar scale for "bipolar5",
 * radio buttons for "multipleChoice".
 */
describe('Feature: psych-test-framework, Property 18: Response type renders correct control', () => {
  const responseTypeArb = fc.constantFrom(
    'likert5' as const,
    'bipolar5' as const,
    'multipleChoice' as const,
  );

  const expectedMapping: Record<string, string> = {
    likert5: 'likert',
    bipolar5: 'bipolar',
    multipleChoice: 'radio',
  };

  it('maps every responseType to the correct control kind', () => {
    fc.assert(
      fc.property(responseTypeArb, (responseType) => {
        const result = controlKindForResponseType(responseType);
        expect(result).toBe(expectedMapping[responseType]);
      }),
      { numRuns: 100 },
    );
  });
});
