import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { getUserProgress, ProgressData } from "@/services/progressService";
import { Header } from "@/components/Header";
import { OverallProgressSection } from "@/components/OverallProgressSection";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Sparkles } from "lucide-react";

/**
 * PERSONAL INSIGHTS PAGE
 *
 * Placeholder page for the "Values & Emotions Deep Dive" content path.
 * Displays overall progress and a "Coming Soon" card with no interactive content.
 *
 * Route: /personal-insights
 * Protected by ProtectedRoute with requiredPersona="legacy_maker"
 *
 * Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
 */
const PersonalInsights: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [overallProgress, setOverallProgress] = useState<ProgressData | null>(null);

  // Redirect unauthenticated users
  useEffect(() => {
    if (!user) {
      navigate("/login");
    }
  }, [user, navigate]);

  // Fetch overall progress via getUserProgress
  useEffect(() => {
    const fetchProgress = async () => {
      if (!user?.id) return;
      const data = await getUserProgress(user.id);
      setOverallProgress(data);
    };
    fetchProgress();
  }, [user?.id]);

  if (!user) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <main className="container mx-auto px-4 py-8">
        {/* Back to Dashboard */}
        <Button
          variant="ghost"
          onClick={() => navigate("/dashboard")}
          className="mb-6 text-gray-600 hover:text-legacy-navy"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dashboard
        </Button>

        {/* Overall Progress */}
        <OverallProgressSection
          completed={overallProgress?.completed ?? 0}
          total={overallProgress?.total ?? 0}
        />

        {/* Coming Soon Card */}
        <div className="bg-white rounded-xl shadow p-8 text-center">
          <div className="flex justify-center mb-4">
            <div className="bg-amber-100 rounded-full p-4">
              <Sparkles className="h-10 w-10 text-amber-500" />
            </div>
          </div>
          <h2 className="text-2xl font-semibold text-legacy-navy mb-2">
            Coming Soon
          </h2>
          <p className="text-gray-500 max-w-md mx-auto">
            Emotional and psychology-based evaluations are coming in a future update.
          </p>
        </div>
      </main>
    </div>
  );
};

export default PersonalInsights;
