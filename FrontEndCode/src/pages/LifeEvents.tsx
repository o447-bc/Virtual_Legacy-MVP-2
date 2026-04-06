import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { getUserProgress, ProgressData } from "@/services/progressService";
import { useLifeEventsProgress } from "@/hooks/useLifeEventsProgress";
import { Header } from "@/components/Header";
import { OverallProgressSection } from "@/components/OverallProgressSection";
import { LifeEventGroup } from "@/components/LifeEventGroup";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, AlertCircle } from "lucide-react";

/**
 * LIFE EVENTS PAGE
 *
 * Dedicated page for the "Life Events" content path.
 * Displays life-event-specific questions grouped by life event instance,
 * ordered by lowest difficulty level first then alphabetically by eventKey.
 *
 * Route: /life-events
 * Protected by ProtectedRoute with requiredPersona="legacy_maker"
 *
 * Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10
 */
const LifeEvents: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [overallProgress, setOverallProgress] = useState<ProgressData | null>(null);

  const {
    data: lifeEventsData,
    isLoading,
    isError,
    refetch,
  } = useLifeEventsProgress(user?.id);

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

  const handleRecord = (questionIds: string[], questionTexts: string[]) => {
    navigate("/record-conversation", {
      state: {
        remainQuestAtCurrLevel: questionIds,
        remainQuestTextAtCurrLevel: questionTexts,
        questionType: "Life Events",
        friendlyName: "Life Events",
        currentQuestLevel: 1,
        totalQuestAtCurrLevel: questionIds.length,
      },
    });
  };

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

        {/* Life Event Groups */}
        {isLoading && (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-xl p-5 shadow-sm">
                <Skeleton className="h-6 w-48 mb-3" />
                <Skeleton className="h-4 w-32 mb-2" />
                <Skeleton className="h-2 w-44" />
              </div>
            ))}
          </div>
        )}

        {isError && (
          <div className="bg-white rounded-xl p-8 shadow-sm text-center">
            <AlertCircle className="h-10 w-10 text-red-400 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Something went wrong
            </h3>
            <p className="text-gray-500 mb-4">
              We couldn't load your life event questions. Please try again.
            </p>
            <Button onClick={() => refetch()}>Retry</Button>
          </div>
        )}

        {!isLoading && !isError && lifeEventsData && lifeEventsData.groups.length === 0 && (
          <div className="bg-white rounded-xl p-8 shadow-sm text-center">
            <p className="text-gray-500">
              No life event questions assigned. Complete the Life Events Survey to get personalized questions.
            </p>
          </div>
        )}

        {!isLoading && !isError && lifeEventsData && lifeEventsData.groups.length > 0 && (
          <div className="space-y-4">
            {lifeEventsData.groups.map((group) => (
              <LifeEventGroup
                key={`${group.eventKey}-${group.instanceOrdinal}`}
                eventKey={group.eventKey}
                instanceName={group.instanceName}
                instanceOrdinal={group.instanceOrdinal}
                questions={group.questions}
                totalQuestions={group.totalQuestions}
                completedQuestions={group.completedQuestions}
                onRecord={handleRecord}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default LifeEvents;
