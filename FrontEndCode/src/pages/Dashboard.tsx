
// DASHBOARD COMPONENT - Content Hub landing page for authenticated legacy makers
// Displays overall progress and three content path cards for navigation

import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useSubscription } from "@/contexts/SubscriptionContext";
import { getUserProgress, ProgressData } from "@/services/progressService";
import { StreakCounter } from "@/components/StreakCounter";
import { streakService, StreakData } from "@/services/streakService";
import { DashboardInfoPanel } from "@/components/DashboardInfoPanel";
import { InfoTooltip } from "@/components/InfoTooltip";
import { Header } from "@/components/Header";
import { OverallProgressSection } from "@/components/OverallProgressSection";
import { ContentPathCard } from "@/components/ContentPathCard";
import { UpgradePromptDialog } from "@/components/UpgradePromptDialog";
import { useProgress, computeLifeStoryProgress } from "@/hooks/useProgress";
import { useLifeEventsProgress } from "@/hooks/useLifeEventsProgress";
import LifeEventsSurvey from "@/components/LifeEventsSurvey";
import { getSurveyStatus, type LifeEventInstanceGroup } from "@/services/surveyService";
import { BookOpen, Calendar, Sparkles, AlertTriangle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

const Dashboard = () => {
  const { user, hasCompletedSurvey, refreshSurveyStatus } = useAuth();
  const { isPremium, trialDaysRemaining } = useSubscription();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { toast } = useToast();
  const [overallProgress, setOverallProgress] = useState<ProgressData | null>(null);
  const [showRetakeSurvey, setShowRetakeSurvey] = useState(false);
  const [surveyDismissed, setSurveyDismissed] = useState(false);
  const [retakeSelections, setRetakeSelections] = useState<string[]>([]);
  const [retakeInstances, setRetakeInstances] = useState<LifeEventInstanceGroup[]>([]);
  const [streakData, setStreakData] = useState<StreakData | null>(null);
  const [streakLoading, setStreakLoading] = useState(true);
  const [showUpgradeDialog, setShowUpgradeDialog] = useState(false);
  const [upgradeDialogContent, setUpgradeDialogContent] = useState<{
    title: string;
    message: string;
    previewQuestion?: string;
    questionCount?: number;
  }>({ title: "", message: "" });

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

  // Handle checkout success URL param
  useEffect(() => {
    if (searchParams.get('checkout') === 'success') {
      toast({
        title: "Welcome to Premium!",
        description: "All features are now unlocked.",
      });
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams, toast]);

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

        {/* Trial nudge banner */}
        {trialDaysRemaining !== null && trialDaysRemaining <= 3 && trialDaysRemaining > 0 && (
          <div className="mb-4 flex items-center gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4">
            <AlertTriangle className="h-5 w-5 flex-shrink-0 text-amber-600" />
            <p className="text-sm text-amber-800">
              Your trial ends in {trialDaysRemaining} day{trialDaysRemaining !== 1 ? 's' : ''}. You'll lose access to Life Events, deeper questions, and unlimited benefactors.{' '}
              <Link to="/pricing" className="font-semibold text-legacy-purple underline">
                View plans
              </Link>
            </p>
          </div>
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
            locked={!isPremium}
            onLockedClick={() => {
              setUpgradeDialogContent({
                title: "Life Events",
                message: "These are the moments that shaped who you are. Upgrade to Premium to start preserving them.",
                questionCount: lifeEventsTotal || undefined,
              });
              setShowUpgradeDialog(true);
            }}
            onClick={() => navigate("/life-events")}
          />
          <ContentPathCard
            title="Values & Emotions Deep Dive"
            subtitle="Emotional and psychology-based evaluations"
            icon={<Sparkles className="w-5 h-5 text-amber-500" />}
            progressLabel="0 out of 0 surveys done"
            accentColor="border-amber-500"
            locked={!isPremium}
            onLockedClick={() => {
              setUpgradeDialogContent({
                title: "Values & Emotions",
                message: "Explore the deeper dimensions of who you are. Upgrade to Premium to unlock these insights.",
              });
              setShowUpgradeDialog(true);
            }}
            onClick={() => navigate("/personal-insights")}
          />
        </div>
      </main>

      {/* Life-Events Survey Overlay */}
      {(hasCompletedSurvey === false && !surveyDismissed || showRetakeSurvey) && (
        <LifeEventsSurvey
          onComplete={(count) => {
            if (count > 0) {
              refreshSurveyStatus();
            } else {
              setSurveyDismissed(true);
            }
            setShowRetakeSurvey(false);
          }}
          isRetake={showRetakeSurvey}
          initialSelections={showRetakeSurvey ? retakeSelections : undefined}
          initialInstances={showRetakeSurvey ? retakeInstances : undefined}
        />
      )}

      {/* Upgrade Prompt Dialog */}
      <UpgradePromptDialog
        open={showUpgradeDialog}
        onOpenChange={setShowUpgradeDialog}
        title={upgradeDialogContent.title}
        message={upgradeDialogContent.message}
        previewQuestion={upgradeDialogContent.previewQuestion}
        questionCount={upgradeDialogContent.questionCount}
        onUpgrade={() => {
          setShowUpgradeDialog(false);
          navigate("/pricing");
        }}
      />
    </div>
  );
};

export default Dashboard;
