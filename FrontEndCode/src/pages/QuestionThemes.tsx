import React from "react";
import { Button } from "@/components/ui/button";
import { Link, useNavigate } from "react-router-dom";
import Logo from "@/components/Logo";
import { useAuth } from "@/contexts/AuthContext";
import { Header } from "@/components/Header";
import { ArrowLeft } from "lucide-react";

const QuestionThemes = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const themes = [
    {
      category: "Childhood Memories",
      levels: "1–5",
      explanation: "The safest, most nostalgic entry point. Concrete, sensory, positive memories. Builds recording confidence."
    },
    {
      category: "Family & Upbringing",
      levels: "1–6",
      explanation: "Slightly more relational than childhood places/objects. Introduces family roles, routines, warmth early on."
    },
    {
      category: "School Days & Education",
      levels: "1–6",
      explanation: "Chronological continuation of childhood. Safe stories about teachers, friends, routines, small achievements."
    },
    {
      category: "Friends & Important Relationships (youth)",
      levels: "1–6",
      explanation: "Focus on peer connections, play, loyalty. Still mostly light-hearted; introduces mild social emotions by level 5–6."
    },
    {
      category: "Hobbies, Play & Free Time",
      levels: "2–7",
      explanation: "Personal interests and joy. Starts light (level 2–3), becomes identity-forming by level 6–7."
    },
    {
      category: "Traditions, Holidays & Celebrations",
      levels: "2–7",
      explanation: "Family rituals, joy, belonging. Warm and sensory early on, starts touching change/loss around level 6–7."
    },
    {
      category: "Love, Romance & Early Partnerships",
      levels: "3–8",
      explanation: "First innocent crushes → early dating → first heartbreaks → lessons about connection. Gradual emotional ramp."
    },
    {
      category: "Work & Career Beginnings",
      levels: "4–8",
      explanation: "First jobs, responsibilities, small wins/failures. Starts factual, becomes reflective about identity & values."
    },
    {
      category: "Proudest Moments & Achievements",
      levels: "5–9",
      explanation: "Positive self-reflection. Starts with smaller wins (level 5–6), moves to life-defining accomplishments (8–9)."
    },
    {
      category: "Challenges & Hard Times",
      levels: "6–10",
      explanation: "First real vulnerability. Starts manageable setbacks (level 6–7), becomes deeper wounds/regrets by 9–10."
    },
    {
      category: "Values & Guiding Principles",
      levels: "7–10",
      explanation: "Core beliefs, ethics, life philosophy. Appears when user has enough life context to articulate what matters."
    },
    {
      category: "Messages to Loved Ones / Future Generations",
      levels: "9–10",
      explanation: "Deepest, most emotionally charged category. Only unlocked at the very end when trust and reflection are highest. Usually the most watched / cherished videos."
    }
  ];

  return (
    <div className="min-h-screen flex flex-col">
      {/* Conditional Header: Use shared Header for authenticated users, custom header for guests */}
      {user ? (
        <Header />
      ) : (
        <header className="w-full border-b">
          <div className="container mx-auto py-4 flex justify-between items-center">
            <Logo />
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
      
      <main className="flex-1 py-12">
        <div className="container mx-auto px-4">
          {/* Back to Dashboard button for authenticated users */}
          {user && (
            <div className="mb-6">
              <Button
                variant="ghost"
                onClick={() => {
                  const dashboardRoute = user.personaType === 'legacy_benefactor' 
                    ? '/benefactor-dashboard' 
                    : '/dashboard';
                  navigate(dashboardRoute);
                }}
                className="flex items-center gap-2 text-legacy-navy hover:text-legacy-purple hover:bg-legacy-purple/10"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Dashboard
              </Button>
            </div>
          )}
          
          <h1 className="text-2xl md:text-3xl font-bold mb-4 text-center bg-gradient-to-r from-legacy-navy to-legacy-purple bg-clip-text text-transparent">
            Question Themes & Levels
          </h1>
          <p className="text-lg text-gray-600 text-center mb-10 max-w-3xl mx-auto">
            Our questions are carefully organized into themes that progress from light and nostalgic to deep and meaningful. 
            Each theme appears across multiple levels, gradually increasing in emotional depth.
          </p>

          {/* Mobile: card layout */}
          <div className="sm:hidden space-y-4">
            {themes.map((theme, index) => (
              <div key={index} className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold text-gray-900">{theme.category}</h3>
                  <span className="text-sm text-legacy-purple font-medium whitespace-nowrap ml-3">
                    Levels {theme.levels}
                  </span>
                </div>
                <p className="text-sm text-gray-600">{theme.explanation}</p>
              </div>
            ))}
          </div>

          {/* Desktop: table layout */}
          <div className="hidden sm:block overflow-x-auto shadow-lg rounded-lg">
            <table className="w-full border-collapse bg-white">
              <thead>
                <tr className="bg-legacy-purple text-white">
                  <th className="px-6 py-4 text-left font-semibold">Category / Theme</th>
                  <th className="px-6 py-4 text-left font-semibold">Appears in Levels</th>
                  <th className="px-6 py-4 text-left font-semibold">Explanation / Purpose</th>
                </tr>
              </thead>
              <tbody>
                {themes.map((theme, index) => (
                  <tr 
                    key={index}
                    className={index % 2 === 0 ? "bg-white hover:bg-gray-50" : "bg-gray-50 hover:bg-gray-100"}
                  >
                    <td className="px-6 py-4 border-t border-gray-200 font-medium text-gray-900">
                      {theme.category}
                    </td>
                    <td className="px-6 py-4 border-t border-gray-200 text-gray-700">
                      {theme.levels}
                    </td>
                    <td className="px-6 py-4 border-t border-gray-200 text-gray-600">
                      {theme.explanation}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-12 text-center">
            {user ? (
              <Link to="/record">
                <Button className="text-lg py-6 px-8 bg-legacy-purple hover:bg-legacy-navy">
                  Start Recording Your Legacy
                </Button>
              </Link>
            ) : (
              <Link to="/legacy-create-choice">
                <Button className="text-lg py-6 px-8 bg-legacy-purple hover:bg-legacy-navy">
                  Get Started
                </Button>
              </Link>
            )}
          </div>
        </div>
      </main>
      
      <footer className="bg-legacy-navy text-white py-8 mt-12">
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

export default QuestionThemes;
