import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Crown, ChevronRight } from 'lucide-react';
import { useSubscription } from '@/contexts/SubscriptionContext';
import { getPortalUrl } from '@/services/billingService';
import { toastError } from '@/utils/toastError';

/**
 * Displays the user's current plan details and management options.
 * Used in the profile/settings area.
 */
export const PlanSettingsSection: React.FC = () => {
  const {
    planId,
    status,
    isPremium,
    billingInterval,
    benefactorCount,
    level1CompletionPercent,
  } = useSubscription();

  const [portalLoading, setPortalLoading] = React.useState(false);

  const handleManageSubscription = async () => {
    setPortalLoading(true);
    try {
      const { portalUrl } = await getPortalUrl();
      window.location.href = portalUrl;
    } catch (err: any) {
      toastError(err.message || 'Failed to open billing portal.', 'PlanSettings');
    } finally {
      setPortalLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <h3 className="text-lg font-semibold text-legacy-navy mb-4">Your Plan</h3>

      <div className="flex items-center gap-3 mb-4">
        {isPremium && <Crown className="h-5 w-5 text-legacy-purple" />}
        <div>
          <p className="font-medium text-gray-900">
            {isPremium ? 'Premium' : 'Free'}
          </p>
          <p className="text-sm text-gray-500">
            {isPremium && billingInterval
              ? `Billed ${billingInterval}`
              : isPremium
                ? `Status: ${status}`
                : 'Complete Level 1 at full quality'}
          </p>
        </div>
      </div>

      {/* Free user: show progress and upgrade button */}
      {!isPremium && (
        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>Level 1 Progress</span>
              <span>{level1CompletionPercent}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-legacy-purple h-2 rounded-full transition-all"
                style={{ width: `${level1CompletionPercent}%` }}
              />
            </div>
          </div>
          <p className="text-sm text-gray-500">
            {benefactorCount} of 1 benefactor{benefactorCount !== 1 ? 's' : ''} used
          </p>
          <Button asChild className="w-full bg-legacy-purple hover:bg-legacy-navy text-white">
            <Link to="/pricing">
              Upgrade to Premium <ChevronRight className="h-4 w-4 ml-1" />
            </Link>
          </Button>
        </div>
      )}

      {/* Premium user: show manage button */}
      {isPremium && (
        <Button
          className="w-full bg-legacy-purple hover:bg-legacy-navy text-white"
          onClick={handleManageSubscription}
          disabled={portalLoading}
        >
          {portalLoading ? 'Loading...' : 'Manage Subscription'}
        </Button>
      )}
    </div>
  );
};
