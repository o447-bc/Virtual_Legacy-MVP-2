import React from "react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import Logo from "@/components/Logo";

const LegacyCreateChoice = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <Link to="/">
            <Logo />
          </Link>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">
            Select your legacy
          </h2>
        </div>
        
        <div className="space-y-4">
          <Link to="/signup-create-legacy" className="block">
            <Button className="w-full text-lg py-6 px-8 bg-legacy-purple hover:bg-legacy-navy">
              Create Your Legacy
            </Button>
          </Link>
          <p className="text-sm text-gray-500 mt-2 text-center">Preserve your own stories, memories, and wisdom for the people who matter most.</p>
          
          <Link to="/signup-start-their-legacy" className="block">
            <Button className="w-full text-lg py-6 px-8 bg-legacy-purple hover:bg-legacy-navy">
              Start Their Legacy
            </Button>
          </Link>
          <p className="text-sm text-gray-500 mt-2 text-center">Set it up for a parent, grandparent, or loved one — you'll manage the account and they'll record their stories.</p>
        </div>
        
        <div className="text-center">
          <p className="text-sm text-gray-600">
            Already have an account?{" "}
            <Link to="/login" className="text-legacy-purple hover:underline font-medium">
              Sign in
            </Link>
          </p>
          <Link to="/discover" className="text-legacy-purple hover:underline text-sm">Learn more about SoulReel →</Link>
        </div>
      </div>
    </div>
  );
};

export default LegacyCreateChoice;
