import React, { useState } from "react";
import { Crown, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useSubscription } from "@/contexts/SubscriptionContext";
import { createCheckoutSession } from "@/services/billingService";
import { toastError } from "@/utils/toastError";

const STRIPE_ANNUAL_PRICE_ID =
  import.meta.env.VITE_STRIPE_ANNUAL_PRICE_ID || "price_annual_placeholder";

interface UpgradePromptDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  message: string;
  previewQuestion?: string;
  questionCount?: number;
  onUpgrade: () => void;
}

export const UpgradePromptDialog: React.FC<UpgradePromptDialogProps> = ({
  open,
  onOpenChange,
  title,
  message,
  previewQuestion,
  questionCount,
  onUpgrade,
}) => {
  const { planLimits } = useSubscription();
  const [checkoutLoading, setCheckoutLoading] = useState(false);

  const monthlyPrice = planLimits.monthlyPriceDisplay ?? "$14.99";
  const annualEquivalent = planLimits.annualMonthlyEquivalentDisplay ?? "$12.42";

  const handleSubscribeNow = async () => {
    setCheckoutLoading(true);
    try {
      const { sessionUrl } = await createCheckoutSession(STRIPE_ANNUAL_PRICE_ID);
      window.location.href = sessionUrl;
    } catch (err: any) {
      toastError(
        err.message || "Failed to start checkout. Please try again.",
        "UpgradePromptDialog"
      );
    } finally {
      setCheckoutLoading(false);
    }
  };

  const handleRemindMeLater = () => {
    try {
      localStorage.setItem("sr_upgrade_deferred", "true");
    } catch {
      // localStorage may be unavailable in private browsing
    }
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-legacy-navy">
            <Crown className="h-5 w-5 text-legacy-purple" />
            {title}
          </DialogTitle>
          <DialogDescription className="text-base text-gray-600 pt-2">
            {message}
          </DialogDescription>
        </DialogHeader>

        {previewQuestion && (
          <div className="border-l-4 border-legacy-purple bg-purple-50 rounded-r-md p-4 my-2">
            <p className="text-sm italic text-gray-700">"{previewQuestion}"</p>
          </div>
        )}

        {questionCount != null && questionCount > 0 && (
          <p className="text-sm font-medium text-legacy-purple">
            {questionCount} questions are waiting for you
          </p>
        )}

        {/* Price display */}
        <div className="rounded-lg bg-gray-50 p-4 my-2 text-center space-y-1">
          <p className="text-lg font-bold text-legacy-navy">
            {annualEquivalent}
            <span className="text-sm font-normal text-gray-500">/mo with annual billing</span>
          </p>
          <p className="text-sm text-gray-500">
            {monthlyPrice}/mo billed monthly
          </p>
        </div>

        <DialogFooter className="flex flex-col sm:flex-row gap-2 pt-2">
          <Button
            variant="outline"
            onClick={handleRemindMeLater}
            className="sm:order-1"
          >
            Remind Me Later
          </Button>
          <Button
            variant="outline"
            onClick={onUpgrade}
            className="sm:order-2"
          >
            <Crown className="h-4 w-4 mr-1" />
            View Plans
          </Button>
          <Button
            onClick={handleSubscribeNow}
            disabled={checkoutLoading}
            className="bg-legacy-purple hover:bg-legacy-purple/90 text-white sm:order-3"
          >
            {checkoutLoading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
            Subscribe Now
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
