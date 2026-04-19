import React, { createContext, useContext, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from './AuthContext';
import { getSubscriptionStatus, type PlanLimits } from '@/services/billingService';

interface SubscriptionState {
  planId: 'free' | 'premium';
  status: string;
  trialExpiresAt: string | null;
  trialDaysRemaining: number | null;
  couponCode: string | null;
  benefactorCount: number;
  planLimits: PlanLimits;
  freePlanLimits: PlanLimits;
  previewQuestions: string[];
  conversationsThisWeek: number;
  weekResetDate: string | null;
  conversationsPerWeek: number;
  isLoading: boolean;
  isPremium: boolean;
  refetch: () => void;
}

const FREE_PLAN_LIMITS: PlanLimits = {
  allowedQuestionCategories: ['life_story_reflections_L1'],
  maxBenefactors: 2,
  accessConditionTypes: ['immediate'],
  features: ['basic'],
  previewQuestions: [],
};

const DEFAULT_STATE: Omit<SubscriptionState, 'isLoading' | 'refetch'> = {
  planId: 'free',
  status: 'active',
  trialExpiresAt: null,
  trialDaysRemaining: null,
  couponCode: null,
  benefactorCount: 0,
  planLimits: FREE_PLAN_LIMITS,
  freePlanLimits: FREE_PLAN_LIMITS,
  previewQuestions: [],
  conversationsThisWeek: 0,
  weekResetDate: null,
  conversationsPerWeek: 3,
  isPremium: false,
};

const SubscriptionContext = createContext<SubscriptionState | undefined>(undefined);

export function computeTrialDaysRemaining(trialExpiresAt: string | null): number | null {
  if (!trialExpiresAt) return null;
  const diff = new Date(trialExpiresAt).getTime() - Date.now();
  if (diff <= 0) return 0;
  return Math.ceil(diff / 86400000);
}

export function computeIsPremium(status: string, trialExpiresAt: string | null): boolean {
  if (status === 'active' || status === 'comped') return true;
  if (status === 'trialing' && trialExpiresAt) {
    return new Date(trialExpiresAt).getTime() > Date.now();
  }
  return false;
}

export const SubscriptionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const isAuthenticated = !!user;

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['subscription-status'],
    queryFn: getSubscriptionStatus,
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: true,
  });

  const value = useMemo<SubscriptionState>(() => {
    if (!isAuthenticated || !data) {
      return {
        ...DEFAULT_STATE,
        isLoading: isAuthenticated ? isLoading : false,
        refetch: () => refetch(),
      };
    }

    const trialDaysRemaining = computeTrialDaysRemaining(data.trialExpiresAt);
    const isPremium = computeIsPremium(data.status, data.trialExpiresAt);

    return {
      planId: data.planId,
      status: data.status,
      trialExpiresAt: data.trialExpiresAt,
      trialDaysRemaining,
      couponCode: data.couponCode,
      benefactorCount: data.benefactorCount,
      planLimits: data.planLimits,
      freePlanLimits: data.freePlanLimits,
      previewQuestions: data.planLimits?.previewQuestions ?? [],
      conversationsThisWeek: data.conversationsThisWeek ?? 0,
      weekResetDate: data.weekResetDate ?? null,
      conversationsPerWeek: data.conversationsPerWeek ?? data.planLimits?.conversationsPerWeek ?? 3,
      isLoading: false,
      isPremium,
      refetch: () => refetch(),
    };
  }, [isAuthenticated, data, isLoading, refetch]);

  return (
    <SubscriptionContext.Provider value={value}>
      {children}
    </SubscriptionContext.Provider>
  );
};

export const useSubscription = (): SubscriptionState => {
  const context = useContext(SubscriptionContext);
  if (context === undefined) {
    throw new Error('useSubscription must be used within a SubscriptionProvider');
  }
  return context;
};
