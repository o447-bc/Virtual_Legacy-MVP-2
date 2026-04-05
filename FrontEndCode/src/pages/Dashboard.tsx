
// DASHBOARD COMPONENT - Main landing page for authenticated legacy makers
// This component displays user progress across question categories and provides
// navigation to recording functionality

import React, { useState, useEffect } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/contexts/AuthContext";
import { buildApiUrl, API_CONFIG } from '@/config/api';
import { ProgressBar } from "@/components/ProgressBar";
import { getUserProgress, ProgressData } from "@/services/progressService";
import { StreakCounter } from "@/components/StreakCounter";
import { streakService, StreakData } from "@/services/streakService";
import { DashboardInfoPanel } from "@/components/DashboardInfoPanel";
import { InfoTooltip } from "@/components/InfoTooltip";
import { Play, ChevronRight } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Header } from "@/components/Header";
import { useProgress, useIncrementLevel, ProgressItem } from "@/hooks/useProgress";
import LifeEventsSurvey from "@/components/LifeEventsSurvey";
import { getSurveyStatus, type LifeEventInstanceGroup } from "@/services/surveyService";
import { RefreshCw } from "lucide-react";

/**
 * MAIN DASHBOARD COMPONENT
 * 
 * Primary landing page for authenticated legacy makers (content creators).
 * Handles authentication validation, persona-based routing, and renders
 * the main dashboard UI with progress tracking.
 * 
 * AUTHENTICATION FLOW:
 * 1. Check if user is authenticated via AuthContext
 * 2. Redirect unauthenticated users to login
 * 3. Route benefactors to their specialized dashboard
 * 4. Display maker dashboard for legacy_maker persona
 * 
 * PERSONA TYPES:
 * - legacy_maker: Creates content (videos/responses) - uses this dashboard
 * - legacy_benefactor: Views content from makers - uses separate dashboard
 */
const Dashboard = () => {
  // HOOKS AND STATE
  const { user, logout, hasCompletedSurvey, refreshSurveyStatus } = useAuth();    // Get current user and logout function from context
  const navigate = useNavigate();         // React Router navigation function
  const location = useLocation();         // Access navigation state
  const [overallProgress, setOverallProgress] = useState<ProgressData | null>(null);
  const [showRetakeSurvey, setShowRetakeSurvey] = useState(false);
  const [retakeSelections, setRetakeSelections] = useState<string[]>([]);
  const [retakeInstances, setRetakeInstances] = useState<LifeEventInstanceGroup[]>([]);
  // STREAK TRACKING STATE
  // Manages display of user's daily video submission streak
  const [streakData, setStreakData] = useState<StreakData | null>(null); // Current streak data from API
  const [streakLoading, setStreakLoading] = useState(true); // Loading state for streak display

  // DEFENSIVE CAMERA CLEANUP
  // Stop any active camera streams when arriving at dashboard
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

  // AUTHENTICATION AND ROUTING EFFECT
  // Runs on component mount and when user/navigate dependencies change
  useEffect(() => {
    // UNAUTHENTICATED USER HANDLING
    // Redirect to login if no user is authenticated
    if (!user) {
      navigate("/login");
      return;
    }
    
    // PERSONA-BASED ROUTING
    // Benefactors have different dashboard with view-only functionality
    // Redirect them to their specialized dashboard
    if (user.personaType === 'legacy_benefactor') {
      navigate("/benefactor-dashboard");
      return;
    }
  }, [user, navigate]); // Re-run effect when user or navigate function changes

  // FETCH OVERALL PROGRESS
  // Get user's overall completion percentage
  useEffect(() => {
    const fetchProgress = async () => {
      if (!user?.id) return;
      const data = await getUserProgress(user.id);
      setOverallProgress(data);
    };
    fetchProgress();
  }, [user?.id]);

  // FETCH STREAK DATA ON DASHBOARD LOAD
  // Always fetches fresh data from API to ensure accuracy
  // Runs when user ID changes (login/logout)
  useEffect(() => {
    const loadStreak = async () => {
      if (!user?.id) return;
      try {
        // Direct API call (no cache) to always show current streak
        // This ensures streak updates are immediately visible after video upload
        const data = await streakService.getStreak();
        setStreakData(data);
      } catch (error) {
        console.error('Error loading streak:', error);
        // Graceful degradation: Streak display will show loading/error state
      } finally {
        setStreakLoading(false);
      }
    };
    loadStreak();
  }, [user?.id]);

  // EARLY RETURNS FOR INVALID STATES
  // Prevent rendering while navigation is in progress
  if (!user) {
    return null; // Don't render anything while redirecting to login
  }

  if (user.personaType === 'legacy_benefactor') {
    return null; // Don't render anything while redirecting to benefactor dashboard
  }

  // MAIN DASHBOARD RENDER
  // Full-screen layout with header, welcome section, and progress tracking
  return (
    <div className="min-h-screen bg-gray-50"> {/* Full viewport height with light background */}
      {/* HEADER SECTION */}
      {/* Top navigation bar with title and user controls */}
      <Header />

      {/* MAIN CONTENT AREA */}
      <main className="container mx-auto px-4 py-8">
        {/* STREAK DISPLAY */}
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
        
        {/* INFO PANEL */}
        <div className="mb-6">
          <DashboardInfoPanel />
        </div>

        {/* RETAKE SURVEY BUTTON */}
        {hasCompletedSurvey === true && (
          <div className="mb-6">
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                try {
                  const status = await getSurveyStatus();
                  setRetakeSelections(status.selectedLifeEvents || []);
                  setRetakeInstances(status.lifeEventInstances || []);
                  setShowRetakeSurvey(true);
                } catch {
                  setShowRetakeSurvey(true);
                }
              }}
              className="text-legacy-purple border-legacy-purple/30 hover:bg-legacy-purple/5"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Update Life Events Survey
            </Button>
          </div>
        )}
        
        {/* PROGRESS TRACKING SECTION */}
        {/* Separate component that handles progress display and category-specific navigation */}
        <ProgressSection user={user} navigationState={location.state} overallProgress={overallProgress} />
      </main>

      {/* Life-Events Survey Overlay — shown for first-time or retake */}
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

/**
 * PROGRESS SECTION COMPONENT
 * 
 * Displays user's progress across all question categories with interactive
 * progress bars that allow direct navigation to category-specific recording.
 * 
 * KEY FEATURES:
 * - Fetches progress data from optimized batch API endpoint
 * - Displays progress bars for each question category
 * - Enables category-specific recording via progress bar clicks
 * - Handles loading states and error conditions gracefully
 * 
 * DATA FLOW:
 * 1. Fetch all progress data in single API call (replaces N+1 calls)
 * 2. Calculate progress percentages for each question type
 * 3. Render interactive progress bars
 * 4. Handle navigation with question type context
 * 
 * PERFORMANCE OPTIMIZATION:
 * - Single batch API call instead of multiple individual calls
 * - Reduces dashboard load time significantly
 * - Caches question type data on backend
 */
const ProgressSection = ({ user, navigationState, overallProgress }) => {
  const navigate = useNavigate();
  const updatedItem = navigationState?.updatedProgressItem as ProgressItem | undefined;

  const { data, isLoading, isError, error, refetch } = useProgress(user?.id, updatedItem);
  const incrementLevel = useIncrementLevel();

  // Auto-advance level when all categories are complete
  useEffect(() => {
    if (!data) return;
    const allComplete = data.progressItems.length > 0 &&
      data.progressItems.every(item => item.remainQuestAtCurrLevel.length === 0);
    if (allComplete && !incrementLevel.isPending) {
      incrementLevel.mutate(data.progressItems[0]?.questionType || 'auto');
    }
  }, [data]);

  const handleContinueRecording = () => {
    if (!data) return;
    const next = data.questionTypes
      .map((qt, i) => {
        const total = data.numValidQuestions[i];
        const unanswered = data.progressDataMap[qt] || 0;
        const pct = total > 0 ? Math.round(((total - unanswered) / total) * 100) : 0;
        return { qt, pct, progressItem: data.progressItems.find(p => p.questionType === qt) };
      })
      .filter(x => x.pct < 100)
      .sort((a, b) => a.pct - b.pct)[0];

    if (next) {
      navigate('/record-conversation', {
        state: {
          ...next.progressItem,
          percentage: next.pct,
          unansweredQuestionIds: data.unansweredQuestionsMap[next.qt] || [],
          unansweredQuestionTexts: data.unansweredQuestionTextsMap[next.qt] || [],
        },
      });
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center gap-2 mb-6">
          <Skeleton className="h-6 w-40" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 sm:gap-x-8">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="space-y-2">
              <div className="flex justify-between items-center">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-4 w-28" />
              </div>
              <div className="flex items-center space-x-3">
                <Skeleton className="flex-1 h-3 rounded-full" />
                <Skeleton className="h-4 w-10" />
              </div>
              <Skeleton className="h-3 w-24" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold mb-4">Your Progress</h3>
        <p className="text-red-600">Error loading progress: {(error as Error).message}</p>
        <Button onClick={() => refetch()} className="mt-4 bg-legacy-purple hover:bg-legacy-navy">
          Retry
        </Button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold mb-4">Your Progress</h3>
        <p className="text-gray-600">No question data available.</p>
      </div>
    );
  }

  const hasIncompleteCategories = data.questionTypes.some((qt, i) => {
    const total = data.numValidQuestions[i];
    const unanswered = data.progressDataMap[qt] || 0;
    return total > 0 ? Math.round(((total - unanswered) / total) * 100) < 100 : false;
  });

  return (
    <>
      {hasIncompleteCategories && (
        <div className="mb-6">
          <Button 
            size="lg" 
            className="w-full sm:w-auto bg-legacy-purple hover:bg-legacy-navy text-white"
            onClick={handleContinueRecording}
          >
            <Play className="mr-2 h-5 w-5" />
            Continue Recording
          </Button>
          <p className="text-sm text-gray-500 mt-2">
            We'll pick the best category for you to work on next
          </p>
        </div>
      )}

      {!hasIncompleteCategories && (
        <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-green-800 mb-2">
            🎉 Congratulations! Current Level Complete!
          </h3>
          <p className="text-green-700">
            You've completed all categories at your current level. Great work!
          </p>
        </div>
      )}
      
      {overallProgress && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <h3 className="text-xl font-semibold">Your Overall Progress</h3>
            <InfoTooltip content="Complete questions across all categories to track your overall journey through all 10 levels" />
          </div>
          <ProgressBar 
            completed={overallProgress.completed}
            total={overallProgress.total}
          />
        </div>
      )}
      
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center gap-2 mb-6">
          <h3 className="text-xl font-semibold">Your Progress</h3>
          <InfoTooltip content="Click any progress bar to record responses for that category. Complete all categories to advance to the next level" />
        </div>
      
        <div className="relative grid grid-cols-1 sm:grid-cols-2 gap-6 sm:gap-x-8">
          <div className="hidden sm:block absolute left-1/2 top-0 bottom-0 w-px bg-gray-200 -translate-x-1/2" />
        
          {data.questionTypes.map((questionType, index) => {
            const progressItem = data.progressItems.find(item => item.questionType === questionType);
            const friendlyName = data.friendlyNames[index];
            const totalQuestions = data.numValidQuestions[index];
            const unansweredCount = data.progressDataMap[questionType] || 0;
            const answeredCount = totalQuestions - unansweredCount;
            const percentage = totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : 0;
            const currentLevel = progressItem?.currentQuestLevel || 1;

            const handleProgressBarClick = () => {
              if (percentage === 100) return;
              navigate('/record-conversation', {
                state: {
                  ...progressItem,
                  percentage,
                  unansweredQuestionIds: data.unansweredQuestionsMap[questionType] || [],
                  unansweredQuestionTexts: data.unansweredQuestionTextsMap[questionType] || [],
                },
              });
            };

            return (
              <div key={questionType} className="space-y-2">
                <div className="flex justify-between items-center">
                  <h4 className="font-medium text-gray-900">Level {currentLevel} - {friendlyName}</h4>
                  <span className="text-sm text-gray-600">{answeredCount} of {totalQuestions} completed</span>
                </div>
                <div 
                  className={`flex items-center space-x-3 transition-all ${
                    percentage === 100 ? 'cursor-default opacity-75' : 'cursor-pointer hover:opacity-80 focus-visible:ring-2 focus-visible:ring-legacy-purple focus-visible:ring-offset-2 focus-visible:rounded-md'
                  }`}
                  onClick={handleProgressBarClick}
                  role={percentage < 100 ? "button" : undefined}
                  tabIndex={percentage < 100 ? 0 : undefined}
                  onKeyDown={(e) => {
                    if ((e.key === 'Enter' || e.key === ' ') && percentage < 100) {
                      e.preventDefault();
                      handleProgressBarClick();
                    }
                  }}
                  aria-label={percentage === 100 ? `${friendlyName} — level completed` : `Record responses for ${friendlyName}, ${percentage}% complete`}
                  title={percentage === 100 ? 'Level completed!' : `Click to record responses for ${friendlyName}`}
                >
                  <Progress value={percentage} className="flex-1 h-3" />
                  <span className="text-sm font-medium text-gray-700 min-w-[3rem]">{percentage}%</span>
                  {percentage < 100 && (
                    <ChevronRight className="h-4 w-4 text-gray-400 hover:text-legacy-purple transition-colors" />
                  )}
                </div>
                <div className="text-xs text-gray-500">
                  {percentage === 100 ? (
                    <span className="text-green-600 font-medium">✓ Congratulations finished!</span>
                  ) : (
                    `${totalQuestions} total questions`
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
};

// EXPORT DASHBOARD COMPONENT
// Main export for use in routing configuration
export default Dashboard;
