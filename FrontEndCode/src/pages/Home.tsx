
import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import Logo from "@/components/Logo";
import { useAuth } from "@/contexts/AuthContext";
import { getPublicPlans, type PlanDefinition } from "@/services/billingService";
import { MessageSquare, Mic, Heart } from "lucide-react";

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
                <div className="flex flex-col items-center">
                  <Link to="/signup-create-legacy">
                    <Button className="text-lg py-6 px-8 bg-legacy-purple hover:bg-legacy-navy">
                      Start Free
                    </Button>
                  </Link>
                  <p className="text-sm text-gray-500 mt-2">Preserve your own stories and memories</p>
                </div>
                <div className="flex flex-col items-center">
                  <Link to="/signup-start-their-legacy">
                    <Button variant="outline" className="text-lg py-6 px-8 border-legacy-purple text-legacy-purple hover:bg-legacy-purple hover:text-white">
                      Start Their Legacy
                    </Button>
                  </Link>
                  <p className="text-sm text-gray-500 mt-2">Set it up for a parent, grandparent, or loved one</p>
                </div>
              </>
            )}
          </div>
        </section>
        
        <section className="bg-legacy-lightPurple py-16">
          <div className="container mx-auto">
            <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
            
            <div className="grid md:grid-cols-3 gap-8">
              <div className="bg-white p-6 rounded-lg shadow-md">
                <div className="w-12 h-12 bg-legacy-purple text-white rounded-full flex items-center justify-center mb-4">
                  <MessageSquare className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-semibold mb-3">Choose a Question</h3>
                <p className="text-gray-600">
                  Pick from thoughtful questions about your life story, key events, and values.
                </p>
              </div>
              
              <div className="bg-white p-6 rounded-lg shadow-md">
                <div className="w-12 h-12 bg-legacy-purple text-white rounded-full flex items-center justify-center mb-4">
                  <Mic className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-semibold mb-3">Have an AI-Guided Conversation</h3>
                <p className="text-gray-600">
                  Our AI interviewer asks follow-up questions to draw out the deeper story behind your answer.
                </p>
              </div>
              
              <div className="bg-white p-6 rounded-lg shadow-md">
                <div className="w-12 h-12 bg-legacy-purple text-white rounded-full flex items-center justify-center mb-4">
                  <Heart className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-semibold mb-3">Share with the People Who Matter</h3>
                <p className="text-gray-600">
                  Choose who receives your stories and when — now, later, or when the time is right.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Sample Questions Section */}
        <section className="py-16 bg-white">
          <div className="container mx-auto px-4">
            <h2 className="text-3xl font-bold text-center text-legacy-navy mb-4">Questions That Spark Your Story</h2>
            <p className="text-lg text-gray-600 text-center max-w-2xl mx-auto mb-12">
              Here are a few of the questions waiting for you
            </p>
            <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              <div className="border border-gray-200 rounded-lg p-6 text-center">
                <p className="text-sm font-medium text-legacy-purple mb-3">Life Story</p>
                <p className="text-gray-700 italic">"What's the bravest thing you've ever done?"</p>
              </div>
              <div className="border border-gray-200 rounded-lg p-6 text-center">
                <p className="text-sm font-medium text-legacy-purple mb-3">Life Events</p>
                <p className="text-gray-700 italic">"Tell me about the day you became a parent."</p>
              </div>
              <div className="border border-gray-200 rounded-lg p-6 text-center">
                <p className="text-sm font-medium text-legacy-purple mb-3">Values &amp; Emotions</p>
                <p className="text-gray-700 italic">"What value do you most want to pass on to the next generation?"</p>
              </div>
            </div>
          </div>
        </section>

        {/* Testimonial Placeholder Section */}
        <section className="py-12 bg-legacy-lightPurple">
          <div className="container mx-auto px-4 max-w-2xl text-center">
            <blockquote className="text-lg italic text-gray-700">
              "I never thought my stories mattered until my grandchildren asked to hear them again."
            </blockquote>
            <p className="mt-4 text-sm text-gray-500">— A SoulReel Family</p>
          </div>
        </section>

        {/* Pricing Section */}
        <section className="py-16 bg-white">
          <div className="container mx-auto text-center px-4">
            <h2 className="text-3xl font-bold text-legacy-navy mb-4">Simple, Transparent Pricing</h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto mb-6">
              Everything you need to preserve your story
            </p>
            <p className="text-4xl font-bold text-legacy-navy mb-1">
              {premiumPlan?.annualMonthlyEquivalentDisplay ?? '$6.58'}<span className="text-lg font-normal text-gray-500">/mo</span>
            </p>
            <p className="text-sm text-gray-500 mb-2">
              with annual billing — save {premiumPlan?.annualSavingsPercent ?? 34}%
            </p>
            <p className="text-sm text-gray-400 mb-8">
              or {premiumPlan?.monthlyPriceDisplay ?? '$9.99'}/mo billed monthly
            </p>
            <Link to="/pricing">
              <Button className="bg-legacy-purple hover:bg-legacy-navy text-lg py-5 px-8">
                View Plans
              </Button>
            </Link>
            <p className="text-xs text-gray-500 mt-4">
              Your stories are always yours — all recordings remain accessible regardless of your plan.
            </p>
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
