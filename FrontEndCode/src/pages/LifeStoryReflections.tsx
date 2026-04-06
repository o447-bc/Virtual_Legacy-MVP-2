import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { getUserProgress, ProgressData } from "@/services/progressService";
import { Header } from "@/components/Header";
import { OverallProgressSection } from "@/components/OverallProgressSection";
import { ProgressSection } from "@/components/ProgressSection";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";

/**
 * LIFE STORY REFLECTIONS PAGE
 *
 * Dedicated page for the "Life Story Reflections" content path.
 * Displays per-category progress grid with click-to-record functionality.
 *
 * Route: /life-story-reflections
 * Protected by ProtectedRoute with requiredPersona="legacy_maker"
 *
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7
 */
const LifeStoryReflections: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
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

        {/* Per-category progress grid with auto-advance level logic */}
        <ProgressSection user={user} navigationState={location.state} />
      </main>
    </div>
  );
};

export default LifeStoryReflections;
