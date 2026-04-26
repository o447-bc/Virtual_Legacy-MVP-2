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
  it('returns true for status "active"', () => {
    expect(computeIsPremium('active', null)).toBe(true);
  });

  it('returns true for status "comped"', () => {
    expect(computeIsPremium('comped', null)).toBe(true);
  });

  it('returns true for status "trialing" with a future couponExpiresAt', () => {
    const future = new Date(Date.now() + 86_400_000).toISOString(); // +1 day
    expect(computeIsPremium('trialing', future)).toBe(true);
  });

  it('returns false for status "trialing" with a past couponExpiresAt', () => {
    const past = new Date(Date.now() - 86_400_000).toISOString(); // -1 day
    expect(computeIsPremium('trialing', past)).toBe(false);
  });

  it('returns false for status "trialing" with null couponExpiresAt', () => {
    expect(computeIsPremium('trialing', null)).toBe(false);
  });

  it('returns false for status "canceled"', () => {
    expect(computeIsPremium('canceled', null)).toBe(false);
  });

  it('returns false for status "past_due"', () => {
    expect(computeIsPremium('past_due', null)).toBe(false);
  });

  it('returns false for status "expired"', () => {
    expect(computeIsPremium('expired', null)).toBe(false);
  });

  it('returns false for empty string status', () => {
    expect(computeIsPremium('', null)).toBe(false);
  });
});


// ---------------------------------------------------------------------------
// Property-based test — computeIsPremium invariant
// ---------------------------------------------------------------------------

describe('computeIsPremium property test', () => {
  const statusArb = fc.constantFrom('active', 'comped', 'trialing', 'canceled', 'past_due', 'expired', 'free', '');

  const couponExpiresAtArb = fc.oneof(
    fc.constant(null),
    fc.date({ min: new Date('2020-01-01'), max: new Date('2030-12-31') }).map((d) => d.toISOString()),
  );

  it('returns true ONLY for active, comped, or trialing-with-future-coupon', () => {
    fc.assert(
      fc.property(statusArb, couponExpiresAtArb, (status, couponExpiresAt) => {
        const result = computeIsPremium(status, couponExpiresAt);

        if (status === 'active' || status === 'comped') {
          expect(result).toBe(true);
        } else if (status === 'trialing' && couponExpiresAt !== null) {
          const isFuture = new Date(couponExpiresAt).getTime() > Date.now();
          expect(result).toBe(isFuture);
        } else {
          expect(result).toBe(false);
        }
      }),
      { numRuns: 100 },
    );
  });
});
