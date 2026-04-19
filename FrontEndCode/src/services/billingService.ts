import { buildApiUrl, API_CONFIG } from '@/config/api';
import { fetchAuthSession } from 'aws-amplify/auth';

export interface PlanLimits {
  allowedQuestionCategories: string[];
  maxBenefactors: number;
  accessConditionTypes: string[];
  features: string[];
  monthlyPriceDisplay?: string;
  annualPriceDisplay?: string;
  annualMonthlyEquivalentDisplay?: string;
  annualSavingsPercent?: number;
  previewQuestions?: string[];
  conversationsPerWeek?: number;
}

export interface SubscriptionStatus {
  planId: 'free' | 'premium';
  status: 'active' | 'canceled' | 'past_due' | 'trialing' | 'comped' | 'expired';
  currentPeriodEnd: string | null;
  trialExpiresAt: string | null;
  couponCode: string | null;
  couponExpiresAt: string | null;
  benefactorCount: number;
  planLimits: PlanLimits;
  freePlanLimits: PlanLimits;
  conversationsThisWeek: number;
  weekResetDate: string | null;
  conversationsPerWeek: number;
}

export interface CouponResult {
  success: boolean;
  type: 'forever_free' | 'time_limited' | 'percentage';
  planId?: string;
  expiresAt?: string;
  stripeCouponId?: string;
  message: string;
}

export interface PlanDefinition {
  planId: string;
  allowedQuestionCategories: string[];
  maxBenefactors: number;
  accessConditionTypes: string[];
  features: string[];
  monthlyPriceDisplay?: string;
  annualPriceDisplay?: string;
  annualMonthlyEquivalentDisplay?: string;
  annualSavingsPercent?: number;
}

/**
 * Get the current user's subscription status and plan limits.
 */
export const getSubscriptionStatus = async (): Promise<SubscriptionStatus> => {
  try {
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();

    if (!idToken) {
      throw new Error('No authentication token available. Please log in again.');
    }

    const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.BILLING_STATUS), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching subscription status:', error);
    throw error;
  }
};

/**
 * Create a Stripe Checkout Session for subscribing to a plan.
 */
export const createCheckoutSession = async (priceId: string): Promise<{ sessionUrl: string }> => {
  try {
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();

    if (!idToken) {
      throw new Error('No authentication token available. Please log in again.');
    }

    const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.BILLING_CREATE_CHECKOUT), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`,
      },
      body: JSON.stringify({ priceId }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error creating checkout session:', error);
    throw error;
  }
};

/**
 * Get a Stripe Customer Portal URL for managing the subscription.
 */
export const getPortalUrl = async (): Promise<{ portalUrl: string }> => {
  try {
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();

    if (!idToken) {
      throw new Error('No authentication token available. Please log in again.');
    }

    const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.BILLING_PORTAL), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching portal URL:', error);
    throw error;
  }
};

/**
 * Apply a coupon code to the current user's account.
 */
export const applyCoupon = async (code: string): Promise<CouponResult> => {
  try {
    const authSession = await fetchAuthSession();
    const idToken = authSession.tokens?.idToken?.toString();

    if (!idToken) {
      throw new Error('No authentication token available. Please log in again.');
    }

    const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.BILLING_APPLY_COUPON), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`,
      },
      body: JSON.stringify({ code }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error applying coupon:', error);
    throw error;
  }
};

/**
 * Get public plan definitions (no auth required).
 */
export const getPublicPlans = async (): Promise<{ plans: Record<string, PlanDefinition> }> => {
  try {
    const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.BILLING_PLANS), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching public plans:', error);
    throw error;
  }
};
