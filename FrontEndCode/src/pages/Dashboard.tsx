
// DASHBOARD COMPONENT - Content Hub landing page for authenticated legacy makers
// Displays overall progress and three content path cards for navigation

import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { getUserProgress, ProgressData } from "@/services/progressService";
import { StreakCounter } from "@/components/StreakCounter";
import { streakService, StreakData } from "@/services/streakService";
import { DashboardInfoPanel } from "@/components/DashboardInfoPanel";
import { InfoTooltip } from "@/components/InfoTooltip";
import { Header } from "@/components/Header";
import { OverallProgressSection } from "@/components/OverallProgressSection";
import { ContentPathCard } from "@/components/ContentPathCard";
import { useProgress, computeLifeStoryProgress } from "@/hooks/useProgress";
import { useLifeEventsProgress } from "@/hooks/useLifeEventsProgress";
import LifeEventsSurvey from "@/components/LifeEventsSurvey";
import { getSurveyStatus, type LifeEventInstanceGroup } from "@/services/surveyService";
import { BookOpen, Calendar, Sparkles } from "lucide-react";

const Dashboard = () => {
  const { user, hasCompletedSurvey, refreshSurveyStatus } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [overallProgress, setOverallProgress] = useState<ProgressData | null>(null);
  const [showRetakeSurvey, setShowRetakeSurvey] = useState(false);
  const [retakeSelections, setRetakeSelections] = useState<string[]>([]);
  const [retakeInstances, setRetakeInstances] = useState<LifeEventInstanceGroup[]>([]);
  const [streakData, setStreakData] = useState<StreakData | null>(null);
  const [streakLoading, setStreakLoading] = useState(true);

  // Progress hooks for content path cards
  const { data: progressData } = useProgress(user?.id);
  const { data: lifeEventsData } = useLifeEventsProgress(user?.id);

  // Compute Life Story progress from useProgress data
  const { total: lifeStoryTotal, completed: lifeStoryCompleted } = progressData
    ? computeLifeStoryProgress(progressData)
    : { total: 0, completed: 0 };
  const currentLevel = progressData?.progressItems?.[0]?.currentQuestLevel;

  // Life Events progress from useLifeEventsProgress
  const lifeEventsTotal = lifeEventsData?.totalQuestions ?? 0;
  const lifeEventsCompleted = lifeEventsData?.completedQuestions ?? 0;

  // Defensive camera cleanup
  useEffect(() => {
    try {
      const videos = document.querySelectorAll('video');
      videos.forEach(video => {
        if (video.srcObject) {
          const stream = video.srcObject as MediaStream;
          stream.getTracks().forEach(track => track.stop());
          video.srcObject = null;
        }
      });
    } catch (error) {
      console.error('Error stopping cameras on dashboard mount:', error);
    }
  }, []);

  // Authentication and routing
  useEffect(() => {
    if (!user) {
      navigate("/login");
      return;
    }
    if (user.personaType === 'legacy_benefactor') {
      navigate("/benefactor-dashboard");
      return;
    }
  }, [user, navigate]);

  // Handle retake survey URL param
  useEffect(() => {
    if (searchParams.get('retakeSurvey') === 'true' && hasCompletedSurvey === true) {
      setSearchParams({}, { replace: true });
      getSurveyStatus().then((status) => {
        setRetakeSelections(status.selectedLifeEvents || []);
        setRetakeInstances(status.lifeEventInstances || []);
        setShowRetakeSurvey(true);
      }).catch(() => {
        setShowRetakeSurvey(true);
      });
    }
  }, [searchParams, hasCompletedSurvey]);

  // Fetch overall progress
  useEffect(() => {
    const fetchProgress = async () => {
      if (!user?.id) return;
      const data = await getUserProgress(user.id);
      setOverallProgress(data);
    };
    fetchProgress();
  }, [user?.id]);

  // Fetch streak data
  useEffect(() => {
    const loadStreak = async () => {
      if (!user?.id) return;
      try {
        const data = await streakService.getStreak();
        setStreakData(data);
      } catch (error) {
        console.error('Error loading streak:', error);
      } finally {
        setStreakLoading(false);
      }
    };
    loadStreak();
  }, [user?.id]);

  if (!user) return null;
  if (user.personaType === 'legacy_benefactor') return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <main className="container mx-auto px-4 py-8">
        {/* Streak display */}
        <div className="mb-6">
          <div className="flex items-center gap-2">
            <StreakCounter
              streakData={streakData}
              loading={streakLoading}
              showFreeze={true}
            />
            <InfoTooltip content="Record at least one video daily to maintain your streak and unlock rewards" />
          </div>
        </div>

        {/* Info panel */}
        <div className="mb-6">
          <DashboardInfoPanel />
        </div>

        {/* Overall progress */}
        {overallProgress && (
          <OverallProgressSection
            completed={overallProgress.completed}
            total={overallProgress.total}
          />
        )}

        {/* Content path cards */}
        <div className="space-y-4">
          <ContentPathCard
            title="Life Story Reflections"
            subtitle="General Questions"
            icon={<BookOpen className="w-5 h-5 text-legacy-purple" />}
            progressLabel={`${lifeStoryCompleted} out of ${lifeStoryTotal} questions`}
            levelLabel={currentLevel ? `Level ${currentLevel}` : undefined}
            accentColor="border-legacy-purple"
            onClick={() => navigate("/life-story-reflections")}
          />
          <ContentPathCard
            title="Life Events"
            subtitle="Personalized life event questions"
            icon={<Calendar className="w-5 h-5 text-blue-500" />}
            progressLabel={`${lifeEventsCompleted} out of ${lifeEventsTotal} questions completed`}
            accentColor="border-blue-500"
            onClick={() => navigate("/life-events")}
          />
          <ContentPathCard
            title="Values & Emotions Deep Dive"
            subtitle="Emotional and psychology-based evaluations"
            icon={<Sparkles className="w-5 h-5 text-amber-500" />}
            progressLabel="0 out of 0 surveys done"
            accentColor="border-amber-500"
            disabled
            badge="Coming Soon"
            onClick={() => navigate("/personal-insights")}
          />
        </div>
      </main>

      {/* Life-Events Survey Overlay */}
      {(hasCompletedSurvey === false || showRetakeSurvey) && (
        <LifeEventsSurvey
          onComplete={() => {
            refreshSurveyStatus();
            setShowRetakeSurvey(false);
          }}
          isRetake={showRetakeSurvey}
          initialSelections={showRetakeSurvey ? retakeSelections : undefined}
          initialInstances={showRetakeSurvey ? retakeInstances : undefined}
        />
      )}
    </div>
  );
};

export default Dashboard;
