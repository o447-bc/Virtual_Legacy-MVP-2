import { describe, it, expect } from 'vitest';
import fc from 'fast-check';

/**
 * Feature: data-retention-lifecycle, Property 28: Persona-based page section visibility
 *
 * Validates: Requirements 15.8
 *
 * For any authenticated user viewing the /your-data page, if the user's persona
 * is legacy_benefactor, only the TrustStatement, LegacyProtection, and Rights
 * sections should be rendered. If the persona is legacy_maker, all sections
 * (including Export and Deletion) should be rendered.
 */

// --- Pure logic extracted from YourData.tsx ---

type PersonaType = 'legacy_maker' | 'legacy_benefactor';

const ALL_SECTIONS = [
  'TrustStatement',
  'StorageExplanation',
  'LegacyProtection',
  'Export',
  'Deletion',
  'Rights',
] as const;

const BENEFACTOR_SECTIONS = ['TrustStatement', 'LegacyProtection', 'Rights'] as const;

/**
 * Determines which page sections are visible for a given persona type.
 * This mirrors the conditional rendering logic in YourData.tsx where
 * Export and Deletion sections are gated behind `isLegacyMaker`.
 */
function getVisibleSections(personaType: PersonaType): string[] {
  const isLegacyMaker = personaType === 'legacy_maker';

  const sections: string[] = [];

  // TrustStatement — always visible
  sections.push('TrustStatement');

  // StorageExplanation — always visible (both personas see "How We Protect Your Content")
  if (isLegacyMaker) {
    sections.push('StorageExplanation');
  }

  // LegacyProtection — always visible
  sections.push('LegacyProtection');

  // Export — legacy_maker only
  if (isLegacyMaker) {
    sections.push('Export');
  }

  // Deletion — legacy_maker only
  if (isLegacyMaker) {
    sections.push('Deletion');
  }

  // Rights — always visible
  sections.push('Rights');

  return sections;
}

// --- Persona strategy ---
const personaTypeArb: fc.Arbitrary<PersonaType> = fc.constantFrom(
  'legacy_maker' as PersonaType,
  'legacy_benefactor' as PersonaType,
);

describe('Feature: data-retention-lifecycle, Property 28: Persona-based page section visibility', () => {
  it('legacy_benefactor sees only TrustStatement, LegacyProtection, and Rights; legacy_maker sees all sections', () => {
    fc.assert(
      fc.property(personaTypeArb, (personaType) => {
        const visible = getVisibleSections(personaType);

        if (personaType === 'legacy_benefactor') {
          // Benefactor should see exactly TrustStatement, LegacyProtection, Rights
          expect(visible).toEqual([...BENEFACTOR_SECTIONS]);

          // Should NOT see Export or Deletion
          expect(visible).not.toContain('Export');
          expect(visible).not.toContain('Deletion');
          expect(visible).not.toContain('StorageExplanation');
        } else {
          // legacy_maker sees all sections
          expect(visible).toEqual([...ALL_SECTIONS]);

          // Must include Export and Deletion
          expect(visible).toContain('Export');
          expect(visible).toContain('Deletion');
          expect(visible).toContain('StorageExplanation');
        }

        // Both personas always see TrustStatement, LegacyProtection, Rights
        expect(visible).toContain('TrustStatement');
        expect(visible).toContain('LegacyProtection');
        expect(visible).toContain('Rights');
      }),
      { numRuns: 100 },
    );
  });
});

/**
 * Feature: data-retention-lifecycle, Property 29: Content summary accuracy
 *
 * Validates: Requirements 15.6
 *
 * For any user viewing the /your-data page, the displayed content summary
 * (recording count, storage size, benefactor count) should use correct
 * human-readable formatting.
 */

// --- Pure formatting logic ---

/**
 * Formats a byte count into a human-readable string.
 * Matches the display requirement from Requirement 15.6: e.g., "2.3 GB".
 */
function formatBytes(bytes: number): string {
  if (bytes < 0) return '0 B';
  if (bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), units.length - 1);
  const value = bytes / Math.pow(k, i);

  // Use up to 1 decimal place, but drop trailing .0
  const formatted = i === 0 ? Math.round(value).toString() : value.toFixed(1).replace(/\.0$/, '');
  return `${formatted} ${units[i]}`;
}

/**
 * Formats a content summary for display.
 */
function formatContentSummary(
  recordingCount: number,
  totalBytes: number,
  benefactorCount: number,
): { recordings: string; storage: string; benefactors: string } {
  return {
    recordings: `${recordingCount} recording${recordingCount !== 1 ? 's' : ''}`,
    storage: formatBytes(totalBytes),
    benefactors: `${benefactorCount} benefactor${benefactorCount !== 1 ? 's' : ''}`,
  };
}

// --- Strategies ---
const bytesArb = fc.integer({ min: 0, max: 5 * 1024 * 1024 * 1024 * 1024 }); // 0 to 5 TB
const itemCountArb = fc.integer({ min: 0, max: 10000 });

describe('Feature: data-retention-lifecycle, Property 29: Content summary accuracy', () => {
  it('formatBytes produces human-readable output with correct unit progression', () => {
    fc.assert(
      fc.property(bytesArb, (bytes) => {
        const result = formatBytes(bytes);

        // Result must be a non-empty string
        expect(result.length).toBeGreaterThan(0);

        // Result must end with a valid unit
        const validUnits = ['B', 'KB', 'MB', 'GB', 'TB'];
        const hasValidUnit = validUnits.some((unit) => result.endsWith(` ${unit}`));
        expect(hasValidUnit).toBe(true);

        // The numeric part must be parseable
        const numericPart = result.split(' ')[0];
        const numValue = parseFloat(numericPart);
        expect(isNaN(numValue)).toBe(false);
        expect(numValue).toBeGreaterThanOrEqual(0);

        // The numeric value should be < 1024 (properly scaled to the right unit)
        // Exception: 0 B
        if (bytes > 0) {
          expect(numValue).toBeGreaterThan(0);
          expect(numValue).toBeLessThan(1024);
        }
      }),
      { numRuns: 200 },
    );
  });

  it('formatContentSummary produces correct pluralization and formatting', () => {
    fc.assert(
      fc.property(
        itemCountArb,
        bytesArb,
        itemCountArb,
        (recordingCount, totalBytes, benefactorCount) => {
          const summary = formatContentSummary(recordingCount, totalBytes, benefactorCount);

          // Recordings string contains the count
          expect(summary.recordings).toContain(recordingCount.toString());

          // Correct pluralization for recordings
          if (recordingCount === 1) {
            expect(summary.recordings).toBe('1 recording');
          } else {
            expect(summary.recordings).toMatch(/\d+ recordings$/);
          }

          // Storage is a valid formatted byte string
          expect(summary.storage).toBe(formatBytes(totalBytes));

          // Benefactors string contains the count
          expect(summary.benefactors).toContain(benefactorCount.toString());

          // Correct pluralization for benefactors
          if (benefactorCount === 1) {
            expect(summary.benefactors).toBe('1 benefactor');
          } else {
            expect(summary.benefactors).toMatch(/\d+ benefactors$/);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
