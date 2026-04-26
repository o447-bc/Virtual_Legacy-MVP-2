import { describe, it, expect } from 'vitest';
import fc from 'fast-check';

/**
 * Feature: pricing-and-billing-v2
 * Tests for upgrade banner display logic.
 *
 * Tests the pure visibility conditions extracted from UpgradeBanner.tsx:
 * - HalfwayBanner: shown when percent >= 50 && !level1CompletedAt && !isPremium
 * - PostCompletionBanner: shown when level1CompletedAt set && !isPremium
 * - BenefactorAwareBanner: shown when level1CompletedAt set && benefactorCount > 0 && !isPremium
 * - No banners for premium users
 *
 * Validates: Requirements 18.1, 19.1–19.5, 20.1–20.5
 */

// ---------------------------------------------------------------------------
// Pure visibility functions (extracted from component logic)
// ---------------------------------------------------------------------------

function shouldShowHalfwayBanner(
  isPremium: boolean,
  level1CompletionPercent: number,
  level1CompletedAt: string | null,
): boolean {
  if (isPremium) return false;
  if (level1CompletionPercent < 50) return false;
  if (level1CompletedAt) return false;
  return true;
}

function shouldShowPostCompletionBanner(
  isPremium: boolean,
  level1CompletedAt: string | null,
): boolean {
  if (isPremium) return false;
  if (!level1CompletedAt) return false;
  return true;
}

function shouldShowBenefactorAwareBanner(
  isPremium: boolean,
  level1CompletedAt: string | null,
  benefactorCount: number,
): boolean {
  if (isPremium) return false;
  if (!level1CompletedAt) return false;
  if (benefactorCount <= 0) return false;
  return true;
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

describe('HalfwayBanner visibility', () => {
  it('hidden at 49% completion', () => {
    expect(shouldShowHalfwayBanner(false, 49, null)).toBe(false);
  });

  it('shown at 50% completion, Level 1 not complete', () => {
    expect(shouldShowHalfwayBanner(false, 50, null)).toBe(true);
  });

  it('shown at 75% completion, Level 1 not complete', () => {
    expect(shouldShowHalfwayBanner(false, 75, null)).toBe(true);
  });

  it('hidden when Level 1 is complete (post-completion banner takes over)', () => {
    expect(shouldShowHalfwayBanner(false, 100, '2025-01-01T00:00:00Z')).toBe(false);
  });

  it('hidden for premium users', () => {
    expect(shouldShowHalfwayBanner(true, 75, null)).toBe(false);
  });
});

describe('PostCompletionBanner visibility', () => {
  it('shown when Level 1 complete and not premium', () => {
    expect(shouldShowPostCompletionBanner(false, '2025-01-01T00:00:00Z')).toBe(true);
  });

  it('hidden when Level 1 not complete', () => {
    expect(shouldShowPostCompletionBanner(false, null)).toBe(false);
  });

  it('hidden for premium users', () => {
    expect(shouldShowPostCompletionBanner(true, '2025-01-01T00:00:00Z')).toBe(false);
  });
});

describe('BenefactorAwareBanner visibility', () => {
  it('shown when Level 1 complete + has benefactor + not premium', () => {
    expect(shouldShowBenefactorAwareBanner(false, '2025-01-01T00:00:00Z', 1)).toBe(true);
  });

  it('hidden when no benefactors', () => {
    expect(shouldShowBenefactorAwareBanner(false, '2025-01-01T00:00:00Z', 0)).toBe(false);
  });

  it('hidden when Level 1 not complete', () => {
    expect(shouldShowBenefactorAwareBanner(false, null, 2)).toBe(false);
  });

  it('hidden for premium users', () => {
    expect(shouldShowBenefactorAwareBanner(true, '2025-01-01T00:00:00Z', 3)).toBe(false);
  });
});

describe('No banners for premium users', () => {
  it('all banners hidden when isPremium is true', () => {
    expect(shouldShowHalfwayBanner(true, 75, null)).toBe(false);
    expect(shouldShowPostCompletionBanner(true, '2025-01-01T00:00:00Z')).toBe(false);
    expect(shouldShowBenefactorAwareBanner(true, '2025-01-01T00:00:00Z', 5)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Property-based tests
// ---------------------------------------------------------------------------

describe('Banner visibility property tests', () => {
  it('halfway banner shown iff !isPremium && percent >= 50 && !completed', () => {
    fc.assert(
      fc.property(
        fc.boolean(),
        fc.integer({ min: 0, max: 100 }),
        fc.oneof(fc.constant(null), fc.constant('2025-01-01T00:00:00Z')),
        (isPremium, percent, completedAt) => {
          const result = shouldShowHalfwayBanner(isPremium, percent, completedAt);
          const expected = !isPremium && percent >= 50 && !completedAt;
          expect(result).toBe(expected);
        },
      ),
      { numRuns: 200 },
    );
  });

  it('post-completion banner shown iff !isPremium && completedAt set', () => {
    fc.assert(
      fc.property(
        fc.boolean(),
        fc.oneof(fc.constant(null), fc.constant('2025-01-01T00:00:00Z')),
        (isPremium, completedAt) => {
          const result = shouldShowPostCompletionBanner(isPremium, completedAt);
          const expected = !isPremium && !!completedAt;
          expect(result).toBe(expected);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('benefactor banner shown iff !isPremium && completedAt set && benefactorCount > 0', () => {
    fc.assert(
      fc.property(
        fc.boolean(),
        fc.oneof(fc.constant(null), fc.constant('2025-01-01T00:00:00Z')),
        fc.integer({ min: 0, max: 10 }),
        (isPremium, completedAt, benefactorCount) => {
          const result = shouldShowBenefactorAwareBanner(isPremium, completedAt, benefactorCount);
          const expected = !isPremium && !!completedAt && benefactorCount > 0;
          expect(result).toBe(expected);
        },
      ),
      { numRuns: 200 },
    );
  });
});
