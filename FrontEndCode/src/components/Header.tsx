import React from "react";
import { Link } from "react-router-dom";
import { UserMenu } from "@/components/UserMenu";
import { useSubscription } from "@/contexts/SubscriptionContext";

/**
 * Header Component
 * 
 * Shared header component that appears on all authenticated pages.
 * Provides consistent navigation and user menu access across the application.
 * 
 * Requirements covered:
 * - 8.1: Display application title "Virtual Legacy Dashboard"
 * - 8.2: Include UserMenu component
 * - 8.3: Responsive layout (stack on mobile, horizontal on desktop)
 * - 8.6: Maintain existing purple/navy color scheme
 * - 8.7: Use Tailwind CSS for styling consistency
 * - 12.1: Use legacy-purple color for primary actions
 * - 12.2: Use legacy-navy color for text
 * - 12.5: White background with subtle shadow
 * - 12.8: Consistent spacing with other UI components
 */
export const Header: React.FC = () => {
  const { trialDaysRemaining } = useSubscription();
  const showTrialIndicator = trialDaysRemaining !== null && trialDaysRemaining <= 5 && trialDaysRemaining > 0;

  return (
    <header className="bg-white shadow-sm">
      <div className="container mx-auto py-3 px-4 sm:py-4 flex flex-col sm:flex-row justify-between items-center gap-3 sm:gap-0">
        {/* Application Title */}
        <div className="flex items-center gap-3">
          <h1 className="text-lg sm:text-xl font-semibold text-legacy-navy text-center sm:text-left">
            SoulReel
          </h1>
          {showTrialIndicator && (
            <Link
              to="/pricing"
              className="text-xs font-medium text-amber-700 bg-amber-100 border border-amber-300 rounded-full px-2.5 py-0.5 hover:bg-amber-200 transition-colors"
            >
              Trial: {trialDaysRemaining} {trialDaysRemaining === 1 ? 'day' : 'days'} left
            </Link>
          )}
        </div>
        
        {/* User Menu */}
        <UserMenu />
      </div>
    </header>
  );
};
