import React, { useState } from "react";
import { ChevronDown, User, UserCircle, Lock, Shield, Settings, LogOut, Palette, Users, RefreshCw, Crown } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useSubscription } from "@/contexts/SubscriptionContext";
import { getPortalUrl } from "@/services/billingService";
import { useNavigate } from "react-router-dom";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatisticsSection } from "@/components/StatisticsSection";
import { ProfileDialog } from "@/components/ProfileDialog";
import { PasswordDialog } from "@/components/PasswordDialog";
import { SecurityDialog } from "@/components/SecurityDialog";
import { useStatistics } from "@/hooks/useStatistics";

/**
 * UserMenu Component
 * 
 * A dropdown menu that provides access to user profile information and actions.
 * Displays user initials in an avatar as the trigger button.
 * 
 * Requirements covered:
 * - 1.1: Display trigger button in header
 * - 1.2: Use user initials in circle
 * - 1.3: Open dropdown on click
 * - 1.4: Close on click outside (handled by DropdownMenu)
 * - 1.5: Close on Escape key (handled by DropdownMenu)
 * - 1.6: Position in top-right corner
 * - 2.1: Display user full name
 * - 2.2: Display user email
 * - 2.3: Edit Profile menu item opens ProfileDialog
 * - 2.7: Change Password menu item opens PasswordDialog
 * - 3.1: Statistics section displays key metrics
 * - 3.8: View Detailed Statistics menu item (placeholder)
 * - 3.9: Navigate to statistics page (placeholder)
 * - 4.1: Question Themes menu item
 * - 4.2: Navigate to /question-themes
 * - 4.3: Close menu after navigation
 * - 5.1: Security & Privacy menu item opens SecurityDialog
 * - 6.1: Settings menu item
 * - 6.2: Display placeholder message for Settings
 * - 6.3: Visual distinction for placeholder
 * - 6.4: Designed for future features
 * - 7.1: Log Out menu item at bottom
 * - 7.2: Call logout() from AuthContext
 * - 7.3: Redirect to home page on logout
 * - 7.4: Clear cached data on logout
 * - 7.5: Visual separation for Log Out item
 * - 9.1-9.5: Persona-specific menu items
 * - 12.1-12.9: Visual design with legacy colors
 * - 12.7: Separators between logical sections
 */
export const UserMenu: React.FC = () => {
  const { user, logout, hasCompletedSurvey } = useAuth();
  const navigate = useNavigate();
  const subscription = useSubscription();
  const { data: statisticsData, loading: statisticsLoading, error: statisticsError } = useStatistics(user?.id);

  // Dialog state management
  const [showProfileDialog, setShowProfileDialog] = useState(false);
  const [showPasswordDialog, setShowPasswordDialog] = useState(false);
  const [showSecurityDialog, setShowSecurityDialog] = useState(false);

  // Determine if user is a legacy_benefactor (hide Statistics and Question Themes)
  const isLegacyBenefactor = user?.personaType === 'legacy_benefactor';
  
  // Determine if user is a legacy_maker (show Manage Benefactors)
  const isLegacyMaker = user?.personaType === 'legacy_maker';

  // Generate user initials from firstName and lastName, or fall back to email
  const getUserInitials = (): string => {
    if (user?.firstName && user?.lastName) {
      return `${user.firstName.charAt(0)}${user.lastName.charAt(0)}`.toUpperCase();
    }
    if (user?.firstName) {
      return user.firstName.charAt(0).toUpperCase();
    }
    if (user?.email) {
      return user.email.charAt(0).toUpperCase();
    }
    return "U";
  };

  // Get full name or fall back to email
  const getDisplayName = (): string => {
    if (user?.firstName && user?.lastName) {
      return `${user.firstName} ${user.lastName}`;
    }
    if (user?.firstName) {
      return user.firstName;
    }
    return user?.email || "User";
  };

  if (!user) {
    return null;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="flex items-center gap-2 hover:bg-legacy-purple/10 min-h-[44px] min-w-[44px] px-3"
          aria-label={`User menu for ${getDisplayName()}`}
        >
          <Avatar className="h-8 w-8 bg-legacy-purple text-white">
            <AvatarFallback className="bg-legacy-purple text-white text-sm font-semibold">
              {getUserInitials()}
            </AvatarFallback>
          </Avatar>
          <ChevronDown className="h-4 w-4 text-legacy-navy" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        align="end"
        className="w-[calc(100vw-2rem)] sm:w-80 md:w-96 max-w-md bg-white shadow-lg border border-gray-200"
        sideOffset={8}
      >
        {/* Profile Section */}
        <div className="px-2 py-3">
          <div className="flex items-center gap-3">
            <Avatar className="h-10 w-10 bg-legacy-purple text-white">
              <AvatarFallback className="bg-legacy-purple text-white font-semibold">
                {getUserInitials()}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <p className="text-base font-semibold text-legacy-navy truncate">
                  {getDisplayName()}
                </p>
                <Badge
                  variant="outline"
                  className={`text-xs px-1.5 py-0 h-5 shrink-0 ${
                    subscription.isPremium
                      ? 'border-legacy-purple/30 text-legacy-purple'
                      : 'border-gray-300 text-gray-500'
                  }`}
                >
                  {subscription.isPremium ? 'Premium' : 'Free'}
                </Badge>
              </div>
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm text-gray-600 truncate">{user.email}</p>
                {subscription.status === 'trialing' && subscription.trialDaysRemaining !== null && subscription.trialDaysRemaining > 0 && (
                  <span className="text-xs text-amber-600 font-medium shrink-0">
                    Trial: {subscription.trialDaysRemaining}d left
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        <DropdownMenuSeparator />

        {/* Statistics Section - Only for legacy_maker */}
        {!isLegacyBenefactor && (
          <>
            <StatisticsSection 
              data={statisticsData}
              loading={statisticsLoading}
              error={statisticsError}
            />
            <DropdownMenuSeparator />
          </>
        )}

        {/* Profile Actions Section */}
        <div className="py-1">
          <DropdownMenuItem
            className="cursor-pointer hover:bg-legacy-purple/10 focus:bg-legacy-purple/10 min-h-[44px] py-3"
            onClick={() => setShowProfileDialog(true)}
          >
            <UserCircle className="mr-2 h-4 w-4 text-legacy-purple" />
            <span className="text-sm text-legacy-navy">Edit Profile</span>
          </DropdownMenuItem>

          <DropdownMenuItem
            className="cursor-pointer hover:bg-legacy-purple/10 focus:bg-legacy-purple/10 min-h-[44px] py-3"
            onClick={() => setShowPasswordDialog(true)}
          >
            <Lock className="mr-2 h-4 w-4 text-legacy-purple" />
            <span className="text-sm text-legacy-navy">Change Password</span>
          </DropdownMenuItem>
        </div>

        <DropdownMenuSeparator />

        {/* Navigation Section - Persona-specific */}
        <div className="py-1">
          {!isLegacyBenefactor && (
            <DropdownMenuItem
              className="cursor-pointer hover:bg-legacy-purple/10 focus:bg-legacy-purple/10 min-h-[44px] py-3"
              onClick={() => navigate('/question-themes')}
            >
              <Palette className="mr-2 h-4 w-4 text-legacy-purple" />
              <span className="text-sm text-legacy-navy">Question Themes</span>
            </DropdownMenuItem>
          )}

          {isLegacyMaker && hasCompletedSurvey && (
            <DropdownMenuItem
              className="cursor-pointer hover:bg-legacy-purple/10 focus:bg-legacy-purple/10 min-h-[44px] py-3"
              onClick={() => navigate('/dashboard?retakeSurvey=true')}
            >
              <RefreshCw className="mr-2 h-4 w-4 text-legacy-purple" />
              <span className="text-sm text-legacy-navy">Update Life Events</span>
            </DropdownMenuItem>
          )}

          {isLegacyMaker && (
            <DropdownMenuItem
              className="cursor-pointer hover:bg-legacy-purple/10 focus:bg-legacy-purple/10 min-h-[44px] py-3"
              onClick={() => navigate('/manage-benefactors')}
            >
              <Users className="mr-2 h-4 w-4 text-legacy-purple" />
              <span className="text-sm text-legacy-navy">Manage Benefactors</span>
            </DropdownMenuItem>
          )}

          <DropdownMenuItem
            className="cursor-pointer hover:bg-legacy-purple/10 focus:bg-legacy-purple/10 min-h-[44px] py-3"
            onClick={async () => {
              if (subscription.isPremium) {
                try {
                  const { portalUrl } = await getPortalUrl();
                  window.location.href = portalUrl;
                } catch {
                  navigate('/pricing');
                }
              } else {
                navigate('/pricing');
              }
            }}
          >
            <Crown className="mr-2 h-4 w-4 text-legacy-purple" />
            <span className="text-sm text-legacy-navy">Plan & Billing</span>
            <Badge
              variant="outline"
              className="ml-auto text-xs px-1.5 py-0 h-5 border-legacy-purple/30 text-legacy-purple"
            >
              {subscription.isPremium ? 'Premium' : 'Free'}
            </Badge>
          </DropdownMenuItem>

          <DropdownMenuItem
            className="cursor-pointer hover:bg-legacy-purple/10 focus:bg-legacy-purple/10 min-h-[44px] py-3"
            onClick={() => setShowSecurityDialog(true)}
          >
            <Shield className="mr-2 h-4 w-4 text-legacy-purple" />
            <span className="text-sm text-legacy-navy">Security & Privacy</span>
          </DropdownMenuItem>

          <DropdownMenuItem
            className="cursor-pointer hover:bg-legacy-purple/10 focus:bg-legacy-purple/10 opacity-60 min-h-[44px] py-3"
            disabled
          >
            <Settings className="mr-2 h-4 w-4 text-gray-400" />
            <span className="text-sm text-gray-500">Settings</span>
            <span className="ml-auto text-xs text-gray-400">Coming Soon</span>
          </DropdownMenuItem>
        </div>

        <DropdownMenuSeparator />

        {/* Logout Section */}
        <div className="py-1">
          <DropdownMenuItem
            className="cursor-pointer hover:bg-red-50 focus:bg-red-50 min-h-[44px] py-3"
            onClick={logout}
          >
            <LogOut className="mr-2 h-4 w-4 text-red-600" />
            <span className="text-sm text-red-600 font-medium">Log Out</span>
          </DropdownMenuItem>
        </div>
      </DropdownMenuContent>

      {/* Dialogs */}
      <ProfileDialog
        open={showProfileDialog}
        onOpenChange={setShowProfileDialog}
        currentFirstName={user?.firstName || ''}
        currentLastName={user?.lastName || ''}
      />

      <PasswordDialog
        open={showPasswordDialog}
        onOpenChange={setShowPasswordDialog}
      />

      <SecurityDialog
        open={showSecurityDialog}
        onOpenChange={setShowSecurityDialog}
      />
    </DropdownMenu>
  );
};
