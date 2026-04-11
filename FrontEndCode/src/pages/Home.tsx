
import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import Logo from "@/components/Logo";
import { useAuth } from "@/contexts/AuthContext";
import { getPublicPlans, type PlanDefinition } from "@/services/billingService";

const Home = () => {
  const { user } = useAuth();
  const [premiumPlan, setPremiumPlan] = useState<PlanDefinition | null>(null);

  useEffect(() => {
    getPublicPlans()
      .then((data) => setPremiumPlan(data.plans?.premium ?? null))
      .catch(() => {});
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="w-full border-b">
        <div className="container mx-auto py-4 flex justify-between items-center">
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
        <section className="py-20 container mx-auto text-center">
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-legacy-navy to-legacy-purple bg-clip-text text-transparent">
            Preserve Your Legacy
          </h1>
          <p className="text-xl md:text-2xl text-gray-600 max-w-3xl mx-auto mb-10">
            Record video responses to thoughtful questions and create a timeless 
            collection of your experiences, wisdom, and personality.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            {user ? (
              <Link to="/record">
                <Button className="text-lg py-6 px-8 bg-legacy-purple hover:bg-legacy-navy">
                  Start Recording
                </Button>
              </Link>
            ) : (
              <>
                <Link to="/signup-create-legacy">
                  <Button className="text-lg py-6 px-8 bg-legacy-purple hover:bg-legacy-navy">
                    Start Free
                  </Button>
                </Link>
                <Link to="/signup-start-their-legacy">
                  <Button className="text-lg py-6 px-8 bg-legacy-navy hover:bg-legacy-purple">
                    Start Their Legacy
                  </Button>
                </Link>
              </>
            )}
          </div>
        </section>
        
        <section className="bg-legacy-lightPurple py-16">
          <div className="container mx-auto">
            <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
            
            <div className="grid md:grid-cols-3 gap-8">
              <div className="bg-white p-6 rounded-lg shadow-md">
                <div className="w-12 h-12 bg-legacy-purple text-white rounded-full flex items-center justify-center text-xl font-bold mb-4">1</div>
                <h3 className="text-xl font-semibold mb-3">Sign Up</h3>
                <p className="text-gray-600">
                  Create an account to start preserving your memories and experiences.
                </p>
              </div>
              
              <div className="bg-white p-6 rounded-lg shadow-md">
                <div className="w-12 h-12 bg-legacy-purple text-white rounded-full flex items-center justify-center text-xl font-bold mb-4">2</div>
                <h3 className="text-xl font-semibold mb-3">Answer Questions</h3>
                <p className="text-gray-600">
                  Respond to thoughtful questions through video recordings.
                </p>
              </div>
              
              <div className="bg-white p-6 rounded-lg shadow-md">
                <div className="w-12 h-12 bg-legacy-purple text-white rounded-full flex items-center justify-center text-xl font-bold mb-4">3</div>
                <h3 className="text-xl font-semibold mb-3">Build Your Legacy</h3>
                <p className="text-gray-600">
                  Create a collection of memories that can be treasured for generations.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Pricing Section */}
        <section className="py-16 bg-white">
          <div className="container mx-auto text-center px-4">
            <h2 className="text-3xl font-bold text-legacy-navy mb-4">Simple, Transparent Pricing</h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto mb-2">
              Free to start. Upgrade to Premium for{' '}
              {premiumPlan?.monthlyPriceDisplay ?? '$9.99'}/mo to unlock all questions and features.
            </p>
            <p className="text-sm text-legacy-purple font-medium mb-8">
              {premiumPlan?.annualMonthlyEquivalentDisplay ?? '$6.58'}/mo — save{' '}
              {premiumPlan?.annualSavingsPercent ?? 34}% with annual billing
            </p>
            <Link to="/pricing">
              <Button className="bg-legacy-purple hover:bg-legacy-navy text-lg py-5 px-8">
                View Plans
              </Button>
            </Link>
          </div>
        </section>
      </main>
      
      <footer className="bg-legacy-navy text-white py-8">
        <div className="container mx-auto">
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
                  <Link to="/" className="text-gray-300 hover:text-white">
                    Home
                  </Link>
                </li>
                <li>
                  <Link to="/login" className="text-gray-300 hover:text-white">
                    Log In
                  </Link>
                </li>
                <li>
                  <Link to="/legacy-create-choice" className="text-gray-300 hover:text-white">
                    Sign Up
                  </Link>
                </li>
                <li>
                  <Link to="/pricing" className="text-gray-300 hover:text-white">
                    Pricing
                  </Link>
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
