import React from "react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

const Home = () => {
  const { user } = useAuth();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="w-full border-b">
        <div className="container mx-auto py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="h-10 w-10 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold text-xl">
              VL
            </div>
            <span className="text-xl font-semibold text-purple-600">
              Virtual Legacy
            </span>
          </div>
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
                <Link to="/signup">
                  <Button className="bg-purple-600 hover:bg-purple-700">Sign Up</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>
      
      <main className="flex-1">
        <section className="py-20 container mx-auto text-center">
          <h1 className="text-5xl md:text-6xl font-bold mb-6 text-purple-600">
            Preserve Your Legacy
          </h1>
          <p className="text-xl md:text-2xl text-gray-600 max-w-3xl mx-auto mb-10">
            Record video responses to thoughtful questions and create a timeless 
            collection of your experiences, wisdom, and personality.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            {user ? (
              <Link to="/record">
                <Button className="text-lg py-6 px-8 bg-purple-600 hover:bg-purple-700">
                  Start Recording
                </Button>
              </Link>
            ) : (
              <Link to="/signup">
                <Button className="text-lg py-6 px-8 bg-purple-600 hover:bg-purple-700">
                  Create Your Legacy
                </Button>
              </Link>
            )}
          </div>
        </section>
      </main>
    </div>
  );
};

export default Home;