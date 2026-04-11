import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import Logo from "@/components/Logo";
import { Header } from "@/components/Header";
import { useAuth } from "@/contexts/AuthContext";
import { useSubscription } from "@/contexts/SubscriptionContext";
import {
  createCheckoutSession,
  getPortalUrl,
  applyCoupon,
  getPublicPlans,
  type PlanDefinition,
  type CouponResult,
} from "@/services/billingService";
import { toast } from "@/components/ui/sonner";
import { Check, Crown, Loader2 } from "lucide-react";

const STRIPE_MONTHLY_PRICE_ID = import.meta.env.VITE_STRIPE_MONTHLY_PRICE_ID || "price_monthly_placeholder";
const STRIPE_ANNUAL_PRICE_ID = import.meta.env.VITE_STRIPE_ANNUAL_PRICE_ID || "price_annual_placeholder";

const FREE_FEATURES = [
  "Life Story Reflections (Level 1)",
  "Up to 2 benefactors",
  "Immediate access conditions",
  "Basic features",
];

const PREMIUM_FEATURES = [
  "All Life Story Reflections levels",
  "Life Events questions",
  "Values & Emotions questions",
  "Unlimited benefactors",
  "All access condition types",
  "PDF export, legacy export & more",
];

const PricingPage: React.FC = () => {
  const { user } = useAuth();
  const isAuthenticated = !!user;

  // Only call useSubscription for rendering — context is always available
  const subscription = useSubscription();

  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "annual">("monthly");
  const [couponExpanded, setCouponExpanded] = useState(false);
  const [couponCode, setCouponCode] = useState("");
  const [couponLoading, setCouponLoading] = useState(false);
  const [couponMessage, setCouponMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [ctaLoading, setCtaLoading] = useState(false);

  // For unauthenticated visitors, fetch public plans
  const [publicPlans, setPublicPlans] = useState<Record<string, PlanDefinition> | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) {
      getPublicPlans()
        .then((data) => setPublicPlans(data.plans))
        .catch(() => {
          // Silently fail — pricing will show without dynamic data
        });
    }
  }, [isAuthenticated]);

  // Derive plan limits from the right source
  const premiumLimits = isAuthenticated
    ? subscription.planLimits
    : publicPlans?.premium;

  const monthlyPrice = premiumLimits?.monthlyPriceDisplay ?? "$9.99";
  const annualEquivalent = premiumLimits?.annualMonthlyEquivalentDisplay ?? "$6.58";
  const annualSavings = premiumLimits?.annualSavingsPercent ?? 34;

  const savingsNote =
    billingPeriod === "annual" ? `save ${annualSavings}%` : null;

  // Determine CTA state
  const isFreePlan = !isAuthenticated || subscription.planId === "free";
  const isTrialing = isAuthenticated && subscription.status === "trialing";
  const isPremiumActive =
    isAuthenticated && subscription.isPremium && !isTrialing;

  const handleSubscribe = async () => {
    if (!isAuthenticated) {
      navigate("/signup-create-legacy");
      return;
    }
    setCtaLoading(true);
    try {
      const priceId =
        billingPeriod === "monthly"
          ? STRIPE_MONTHLY_PRICE_ID
          : STRIPE_ANNUAL_PRICE_ID;
      const { sessionUrl } = await createCheckoutSession(priceId);
      window.location.href = sessionUrl;
    } catch (err: any) {
      toast.error(err.message || "Failed to start checkout. Please try again.");
    } finally {
      setCtaLoading(false);
    }
  };

  const handleManageSubscription = async () => {
    setCtaLoading(true);
    try {
      const { portalUrl } = await getPortalUrl();
      window.location.href = portalUrl;
    } catch (err: any) {
      toast.error(err.message || "Failed to open billing portal.");
    } finally {
      setCtaLoading(false);
    }
  };

  const handleApplyCoupon = async () => {
    if (!couponCode.trim()) return;
    setCouponLoading(true);
    setCouponMessage(null);
    try {
      const result: CouponResult = await applyCoupon(couponCode.trim());
      setCouponMessage({ type: "success", text: result.message });
      setCouponCode("");
      // Refetch subscription status to reflect coupon changes
      if (isAuthenticated) {
        subscription.refetch();
      }
    } catch (err: any) {
      setCouponMessage({ type: "error", text: err.message || "Invalid coupon code" });
    } finally {
      setCouponLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      {isAuthenticated ? (
        <Header />
      ) : (
        <header className="w-full border-b bg-white">
          <div className="container mx-auto py-4 flex justify-between items-center">
            <Link to="/">
              <Logo />
            </Link>
            <div className="flex gap-4">
              <Link to="/login">
                <Button variant="outline">Log In</Button>
              </Link>
              <Link to="/legacy-create-choice">
                <Button className="bg-legacy-purple hover:bg-legacy-navy">Sign Up</Button>
              </Link>
            </div>
          </div>
        </header>
      )}

      <main className="flex-1">
        {/* Hero */}
        <section className="py-12 sm:py-16 text-center">
          <div className="container mx-auto px-4">
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-legacy-navy to-legacy-purple bg-clip-text text-transparent">
              Choose Your Plan
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Start preserving your legacy for free, or unlock the full experience with Premium.
            </p>
          </div>
        </section>

        {/* Billing Toggle */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex rounded-lg bg-white border p-1 shadow-sm">
            <button
              onClick={() => setBillingPeriod("monthly")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                billingPeriod === "monthly"
                  ? "bg-legacy-purple text-white"
                  : "text-gray-600 hover:text-legacy-navy"
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingPeriod("annual")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                billingPeriod === "annual"
                  ? "bg-legacy-purple text-white"
                  : "text-gray-600 hover:text-legacy-navy"
              }`}
            >
              Annual
            </button>
          </div>
        </div>

        {/* Plan Comparison Grid */}
        <section className="container mx-auto px-4 pb-16">
          <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {/* Free Plan Card */}
            <Card className="relative border-2 border-gray-200">
              <CardHeader className="text-center pb-2">
                <CardTitle className="text-2xl text-legacy-navy">Free</CardTitle>
                <p className="text-4xl font-bold text-legacy-navy mt-2">
                  $0<span className="text-base font-normal text-gray-500">/mo</span>
                </p>
              </CardHeader>
              <CardContent className="pt-4">
                <ul className="space-y-3 mb-8">
                  {FREE_FEATURES.map((feature) => (
                    <li key={feature} className="flex items-start gap-2">
                      <Check className="h-5 w-5 text-gray-400 mt-0.5 shrink-0" />
                      <span className="text-gray-600 text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>
                {isAuthenticated && isFreePlan && !isTrialing ? (
                  <Button variant="outline" className="w-full" disabled>
                    Current Plan
                  </Button>
                ) : !isAuthenticated ? (
                  <Link to="/signup-create-legacy" className="block">
                    <Button variant="outline" className="w-full">
                      Start Free
                    </Button>
                  </Link>
                ) : null}
              </CardContent>
            </Card>

            {/* Premium Plan Card */}
            <Card className="relative border-2 border-legacy-purple shadow-lg">
              {isPremiumActive && (
                <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 bg-legacy-purple text-white">
                  Current Plan
                </Badge>
              )}
              {isTrialing && (
                <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-500 text-white">
                  Trial Active
                </Badge>
              )}
              <CardHeader className="text-center pb-2">
                <div className="flex items-center justify-center gap-2">
                  <Crown className="h-5 w-5 text-legacy-purple" />
                  <CardTitle className="text-2xl text-legacy-navy">Premium</CardTitle>
                </div>
                <div className="mt-2">
                  <p className="text-4xl font-bold text-legacy-navy">
                    {billingPeriod === "monthly" ? monthlyPrice : annualEquivalent}
                    <span className="text-base font-normal text-gray-500">/mo</span>
                  </p>
                  {savingsNote && (
                    <p className="text-sm text-legacy-purple font-medium mt-1">
                      {savingsNote}
                    </p>
                  )}
                </div>
              </CardHeader>
              <CardContent className="pt-4">
                <ul className="space-y-3 mb-8">
                  {PREMIUM_FEATURES.map((feature) => (
                    <li key={feature} className="flex items-start gap-2">
                      <Check className="h-5 w-5 text-legacy-purple mt-0.5 shrink-0" />
                      <span className="text-gray-700 text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* CTA by auth state */}
                {!isAuthenticated && (
                  <Button
                    className="w-full bg-legacy-purple hover:bg-legacy-navy"
                    onClick={() => navigate("/signup-create-legacy")}
                  >
                    Start Free Trial
                  </Button>
                )}
                {isAuthenticated && isFreePlan && !isTrialing && (
                  <Button
                    className="w-full bg-legacy-purple hover:bg-legacy-navy"
                    onClick={handleSubscribe}
                    disabled={ctaLoading}
                  >
                    {ctaLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : null}
                    Subscribe
                  </Button>
                )}
                {isPremiumActive && (
                  <Button
                    className="w-full bg-legacy-purple hover:bg-legacy-navy"
                    onClick={handleManageSubscription}
                    disabled={ctaLoading}
                  >
                    {ctaLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : null}
                    Manage Subscription
                  </Button>
                )}
                {isTrialing && (
                  <Button
                    className="w-full bg-legacy-purple hover:bg-legacy-navy"
                    onClick={handleSubscribe}
                    disabled={ctaLoading}
                  >
                    {ctaLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : null}
                    Subscribe Now
                  </Button>
                )}

                {/* Coupon Section */}
                {isAuthenticated && (
                  <div className="mt-4 text-center">
                    {!couponExpanded ? (
                      <button
                        onClick={() => setCouponExpanded(true)}
                        className="text-sm text-legacy-purple hover:underline"
                      >
                        Have a code?
                      </button>
                    ) : (
                      <div className="space-y-2">
                        <div className="flex gap-2">
                          <Input
                            placeholder="Enter coupon code"
                            value={couponCode}
                            onChange={(e) => setCouponCode(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleApplyCoupon()}
                            className="text-sm"
                          />
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleApplyCoupon}
                            disabled={couponLoading || !couponCode.trim()}
                            className="shrink-0"
                          >
                            {couponLoading ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              "Apply"
                            )}
                          </Button>
                        </div>
                        {couponMessage && (
                          <p
                            className={`text-xs ${
                              couponMessage.type === "success"
                                ? "text-green-600"
                                : "text-red-600"
                            }`}
                          >
                            {couponMessage.text}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-legacy-navy text-white py-8">
        <div className="container mx-auto px-4 text-center text-gray-400">
          <p>&copy; {new Date().getFullYear()} SoulReel. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

export default PricingPage;
