import { describe, it, expect, vi } from 'vitest';
import fc from 'fast-check';

// Mock service modules to prevent API config validation from throwing during import
vi.mock('@/services/billingService', () => ({
  getSubscriptionStatus: vi.fn(),
  getPublicPlans: vi.fn(),
}));

vi.mock('@/config/api', () => ({
  buildApiUrl: vi.fn(),
  API_CONFIG: { ENDPOINTS: {} },
}));

import { computeIsPremium } from '@/contexts/SubscriptionContext';

// ---------------------------------------------------------------------------
// Unit tests — deterministic cases
// ---------------------------------------------------------------------------

describe('computeIsPremium', () => {
  it('returns true for premium planId + status "active"', () => {
    expect(computeIsPremium('premium', 'active', null)).toBe(true);
  });

  it('returns true for premium planId + status "comped"', () => {
    expect(computeIsPremium('premium', 'comped', null)).toBe(true);
  });

  it('returns false for free planId + status "active"', () => {
    expect(computeIsPremium('free', 'active', null)).toBe(false);
  });

  it('returns false for free planId + status "comped"', () => {
    expect(computeIsPremium('free', 'comped', null)).toBe(false);
  });

  it('returns true for premium planId + trialing with future couponExpiresAt', () => {
    const future = new Date(Date.now() + 86_400_000).toISOString();
    expect(computeIsPremium('premium', 'trialing', future)).toBe(true);
  });

  it('returns false for premium planId + trialing with past couponExpiresAt', () => {
    const past = new Date(Date.now() - 86_400_000).toISOString();
    expect(computeIsPremium('premium', 'trialing', past)).toBe(false);
  });

  it('returns false for premium planId + trialing with null couponExpiresAt', () => {
    expect(computeIsPremium('premium', 'trialing', null)).toBe(false);
  });

  it('returns false for premium planId + status "canceled"', () => {
    expect(computeIsPremium('premium', 'canceled', null)).toBe(false);
  });

  it('returns false for free planId regardless of status', () => {
    for (const status of ['active', 'comped', 'trialing', 'canceled', 'past_due', 'expired']) {
      expect(computeIsPremium('free', status, null)).toBe(false);
    }
  });
});


// ---------------------------------------------------------------------------
// Property-based test — computeIsPremium invariant
// ---------------------------------------------------------------------------

describe('computeIsPremium property test', () => {
  const planIdArb = fc.constantFrom('free', 'premium');
  const statusArb = fc.constantFrom('active', 'comped', 'trialing', 'canceled', 'past_due', 'expired', '');
  const couponExpiresAtArb = fc.oneof(
    fc.constant(null),
    fc.date({ min: new Date('2020-01-01'), max: new Date('2030-12-31') }).map((d) => d.toISOString()),
  );

  it('free planId always returns false; premium returns true only for active/comped/valid-trialing', () => {
    fc.assert(
      fc.property(planIdArb, statusArb, couponExpiresAtArb, (planId, status, couponExpiresAt) => {
        const result = computeIsPremium(planId, status, couponExpiresAt);

        if (planId === 'free') {
          expect(result).toBe(false);
        } else if (status === 'active' || status === 'comped') {
          expect(result).toBe(true);
        } else if (status === 'trialing' && couponExpiresAt !== null) {
          const isFuture = new Date(couponExpiresAt).getTime() > Date.now();
          expect(result).toBe(isFuture);
        } else {
          expect(result).toBe(false);
        }
      }),
      { numRuns: 200 },
    );
  });
});
