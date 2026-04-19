import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import Logo from "@/components/Logo";
import { useAuth } from "@/contexts/AuthContext";
import { trackEvent } from "@/lib/analytics";
import HeroSection from "@/components/landing/HeroSection";
import EaseOfUseStrip from "@/components/landing/EaseOfUseStrip";
import HowItWorksSection from "@/components/landing/HowItWorksSection";
import SampleQuestionsSection from "@/components/landing/SampleQuestionsSection";
import FounderStorySection from "@/components/landing/FounderStorySection";
import ClosingCTASection from "@/components/landing/ClosingCTASection";
import EmailCaptureSection from "@/components/landing/EmailCaptureSection";
import TrustStrip from "@/components/landing/TrustStrip";

const Home = () => {
  const { user } = useAuth();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="w-full border-b sticky top-0 z-50 bg-white/95 backdrop-blur-sm">
        <div className="container mx-auto px-4 sm:px-8 py-4 flex justify-between items-center">
          <Logo />
          <div className="flex gap-4">
            {user ? (
              <Link to="/dashboard">
                <Button variant="outline">Go to Dashboard</Button>
              </Link>
            ) : (
              <>
                <Link to="/login">
                  <Button variant="outline">Log In</Button>
                </Link>
                <Link to="/legacy-create-choice">
                  <Button className="bg-legacy-purple hover:bg-legacy-navy">Sign Up</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        <HeroSection user={user} />
        <EaseOfUseStrip />
        <HowItWorksSection />
        <SampleQuestionsSection />
        <FounderStorySection />
        <ClosingCTASection user={user} />
        <EmailCaptureSection />
        <TrustStrip />
      </main>

      <footer className="bg-legacy-navy text-white py-8">
        <div className="container mx-auto px-4 sm:px-8">
          <div className="flex flex-col md:flex-row justify-between">
            <div>
              <Logo className="text-white" />
              <p className="mt-4 text-gray-300">
                Preserving your stories for future generations.
              </p>
            </div>

            <div className="mt-6 md:mt-0">
              <h3 className="font-semibold mb-2">Quick Links</h3>
              <ul className="space-y-1">
                <li>
                  <Link to="/" className="text-gray-300 hover:text-white">Home</Link>
                </li>
                <li>
                  <Link to="/login" className="text-gray-300 hover:text-white">Log In</Link>
                </li>
                <li>
                  <Link to="/legacy-create-choice" className="text-gray-300 hover:text-white">Sign Up</Link>
                </li>
                <li>
                  <Link to="/pricing" className="text-gray-300 hover:text-white">Pricing</Link>
                </li>
                <li>
                  <Link to="/your-data" className="text-gray-300 hover:text-white" onClick={() => trackEvent('footer_privacy_click')}>Privacy &amp; Your Data</Link>
                </li>
              </ul>
            </div>
          </div>

          <div className="border-t border-gray-700 mt-8 pt-6 text-center text-gray-400">
            <p>&copy; {new Date().getFullYear()} SoulReel. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Home;
