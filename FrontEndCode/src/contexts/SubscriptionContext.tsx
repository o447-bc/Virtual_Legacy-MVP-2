import React, { createContext, useContext, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from './AuthContext';
import { getSubscriptionStatus, type PlanLimits } from '@/services/billingService';

interface SubscriptionState {
  planId: 'free' | 'premium';
  status: string;
  couponCode: string | null;
  couponExpiresAt: string | null;
  benefactorCount: number;
  billingInterval: 'monthly' | 'annual' | null;
  level1CompletionPercent: number;
  level1CompletedAt: string | null;
  totalQuestionsCompleted: number;
  planLimits: PlanLimits;
  freePlanLimits: PlanLimits;
  isLoading: boolean;
  isPremium: boolean;
  refetch: () => void;
  // Deprecated V1 fields — kept for backward compat until Dashboard/Header/UserMenu are updated
  trialDaysRemaining: number | null;
  previewQuestions: string[];
  conversationsThisWeek: number;
  conversationsPerWeek: number;
}

const FREE_PLAN_LIMITS: PlanLimits = {
  maxLevel: 1,
  allowedQuestionCategories: ['life_story_reflections'],
  maxBenefactors: 1,
  accessConditionTypes: ['immediate'],
  features: ['basic'],
};

const DEFAULT_STATE: Omit<SubscriptionState, 'isLoading' | 'refetch'> = {
  planId: 'free',
  status: 'active',
  couponCode: null,
  couponExpiresAt: null,
  benefactorCount: 0,
  billingInterval: null,
  level1CompletionPercent: 0,
  level1CompletedAt: null,
  totalQuestionsCompleted: 0,
  planLimits: FREE_PLAN_LIMITS,
  freePlanLimits: FREE_PLAN_LIMITS,
  isPremium: false,
  // Deprecated V1 fields
  trialDaysRemaining: null,
  previewQuestions: [],
  conversationsThisWeek: 0,
  conversationsPerWeek: 0,
};

const SubscriptionContext = createContext<SubscriptionState | undefined>(undefined);

export function computeIsPremium(
  status: string,
  couponExpiresAt: string | null,
): boolean {
  if (status === 'active' || status === 'comped') return true;
  if (status === 'trialing' && couponExpiresAt) {
    return new Date(couponExpiresAt).getTime() > Date.now();
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

    const isPremium = computeIsPremium(data.status, data.couponExpiresAt ?? null);

    return {
      planId: data.planId,
      status: data.status,
      couponCode: data.couponCode,
      couponExpiresAt: data.couponExpiresAt ?? null,
      benefactorCount: data.benefactorCount,
      billingInterval: data.billingInterval ?? null,
      level1CompletionPercent: data.level1CompletionPercent ?? 0,
      level1CompletedAt: data.level1CompletedAt ?? null,
      totalQuestionsCompleted: data.totalQuestionsCompleted ?? 0,
      planLimits: data.planLimits,
      freePlanLimits: data.freePlanLimits,
      isLoading: false,
      isPremium,
      refetch: () => refetch(),
      // Deprecated V1 fields — will be removed when Dashboard/Header/UserMenu are updated
      trialDaysRemaining: null,
      previewQuestions: [],
      conversationsThisWeek: 0,
      conversationsPerWeek: 0,
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
