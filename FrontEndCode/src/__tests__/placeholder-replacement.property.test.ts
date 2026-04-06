import { describe, it, expect, vi } from 'vitest';
import fc from 'fast-check';

// Mock service modules to prevent API config validation from throwing during import
vi.mock('@/services/surveyService', () => ({
  getSurveyStatus: vi.fn(),
}));

import { replacePlaceholder } from '@/hooks/useLifeEventsProgress';

/**
 * Feature: dashboard-content-hub, Property 7: Placeholder token replacement
 *
 * Validates: Requirements 8.3
 *
 * For any question text containing a placeholder token (e.g., `{spouse_name}`,
 * `{child_name}`, `{deceased_name}`) and for any non-empty instance name string,
 * replacing the placeholder with the instance name should produce a string that
 * contains the instance name and does not contain the original placeholder token.
 */

const PLACEHOLDERS = ['{spouse_name}', '{child_name}', '{deceased_name}'] as const;

// Map each placeholder to an eventKey that resolves to it
const PLACEHOLDER_TO_EVENT_KEY: Record<string, string> = {
  '{spouse_name}': 'got_married',
  '{child_name}': 'had_children',
  '{deceased_name}': 'death_of_child',
};

// The custom placeholderMap we pass to replacePlaceholder so we don't depend on the registry
const PLACEHOLDER_MAP: Record<string, string> = {
  got_married: '{spouse_name}',
  had_children: '{child_name}',
  death_of_child: '{deceased_name}',
};

/**
 * Generator for a random placeholder token from the known set.
 */
const placeholderArb = fc.constantFrom(...PLACEHOLDERS);

/**
 * Generator for a "safe" string segment that does NOT contain any placeholder token.
 * We filter out strings containing the curly-brace patterns to keep things clean.
 */
const safeStringArb = fc
  .string({ minLength: 0, maxLength: 30 })
  .filter((s) => !PLACEHOLDERS.some((p) => s.includes(p)));

/**
 * Generator for question text that contains exactly one occurrence of a placeholder.
 * Structure: <prefix><placeholder><suffix>
 */
const questionTextWithPlaceholderArb = fc
  .tuple(safeStringArb, placeholderArb, safeStringArb)
  .map(([prefix, placeholder, suffix]) => ({
    text: `${prefix}${placeholder}${suffix}`,
    placeholder,
    eventKey: PLACEHOLDER_TO_EVENT_KEY[placeholder],
  }));

/**
 * Generator for a non-empty instance name that does NOT contain any placeholder token.
 * This constraint is critical — if the instance name contained the placeholder,
 * the "result does not contain placeholder" check would be trivially violated.
 */
const instanceNameArb = fc
  .string({ minLength: 1, maxLength: 30 })
  .filter((s) => !PLACEHOLDERS.some((p) => s.includes(p)));

describe('Feature: dashboard-content-hub, Property 7: Placeholder token replacement', () => {
  it('replacing a placeholder with an instance name produces a string containing the name and not the placeholder', () => {
    fc.assert(
      fc.property(
        questionTextWithPlaceholderArb,
        instanceNameArb,
        ({ text, placeholder, eventKey }, instanceName) => {
          const result = replacePlaceholder(text, eventKey, instanceName, PLACEHOLDER_MAP);

          // 1. The result contains the instance name
          expect(result).toContain(instanceName);

          // 2. The result does NOT contain the original placeholder token
          expect(result).not.toContain(placeholder);
        },
      ),
      { numRuns: 100 },
    );
  });
});
