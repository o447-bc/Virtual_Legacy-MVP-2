
// DASHBOARD COMPONENT - Main landing page for authenticated legacy makers
// This component displays user progress across question categories and provides
// navigation to recording functionality

import React, { useState, useEffect } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";           // React Router navigation
import { Button } from "@/components/ui/button";           // Reusable UI button component
import { Progress } from "@/components/ui/progress";       // Progress bar component
import { useAuth } from "@/contexts/AuthContext";          // Authentication context hook
import { getCurrentUser, fetchAuthSession } from 'aws-amplify/auth'; // AWS Amplify auth functions
import { buildApiUrl, API_CONFIG } from '@/config/api';    // API configuration and URL builder
import { ProgressBar } from "@/components/ProgressBar";    // Overall progress bar component
import { getUserProgress, ProgressData } from "@/services/progressService"; // Progress service
import { StreakCounter } from "@/components/StreakCounter";  // Streak display component
import { streakService, StreakData } from "@/services/streakService"; // Streak service
import { DashboardInfoPanel } from "@/components/DashboardInfoPanel"; // Info panel component
import { InfoTooltip } from "@/components/InfoTooltip"; // Tooltip component
import { Play, ChevronRight } from "lucide-react"; // Icons for UI elements
import { Header } from "@/components/Header"; // Shared header component

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
  const { user, logout } = useAuth();    // Get current user and logout function from context
  const navigate = useNavigate();         // React Router navigation function
  const location = useLocation();         // Access navigation state
  const [overallProgress, setOverallProgress] = useState<ProgressData | null>(null); // Overall progress state
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
        
        {/* PROGRESS TRACKING SECTION */}
        {/* Separate component that handles progress display and category-specific navigation */}
        <ProgressSection user={user} navigationState={location.state} overallProgress={overallProgress} />
      </main>
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
  // STATE MANAGEMENT
  // Separate state for different aspects of progress data
  const [questionTypeData, setQuestionTypeData] = useState(null);        // Question types, names, counts
  const [progressData, setProgressData] = useState({});                  // Unanswered counts per type
  const [unansweredQuestionsData, setUnansweredQuestionsData] = useState({}); // Specific question IDs
  const [unansweredQuestionTextsData, setUnansweredQuestionTextsData] = useState({}); // Specific question texts
  const [progressItems, setProgressItems] = useState([]);                // Raw progress items from userQuestionLevelProgressDB
  const [loading, setLoading] = useState(true);                          // Loading state for UI
  const [error, setError] = useState(null);                              // Error state for error handling
  const navigate = useNavigate();                                        // Navigation function

  /**
   * CONTINUE RECORDING HANDLER
   * 
   * Smart category selection that picks the best category for the user to work on next.
   * Prioritizes categories with the lowest completion percentage to encourage balanced progress.
   * 
   * LOGIC:
   * 1. Filter out completed categories (100%)
   * 2. Sort remaining categories by completion percentage (lowest first)
   * 3. Navigate to recording page with selected category's data
   * 4. If all categories complete, show completion message
   */
  const handleContinueRecording = () => {
    if (!questionTypeData || !progressItems.length) return;

    // Build array of incomplete categories with their progress data
    const incompleteCategoriesWithProgress = questionTypeData.questionTypes
      .map((questionType, index) => {
        const progressItem = progressItems.find(item => item.questionType === questionType);
        const totalQuestions = questionTypeData.numValidQuestions[index];
        const unansweredCount = progressData[questionType] || 0;
        const answeredCount = totalQuestions - unansweredCount;
        const percentage = totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : 0;
        
        return {
          progressItem,
          percentage,
          questionType,
          unansweredQuestionIds: unansweredQuestionsData[questionType] || [],
          unansweredQuestionTexts: unansweredQuestionTextsData[questionType] || []
        };
      })
      .filter(item => item.percentage < 100) // Only incomplete categories
      .sort((a, b) => a.percentage - b.percentage); // Sort by least complete first

    // Navigate to the category with lowest completion
    if (incompleteCategoriesWithProgress.length > 0) {
      const nextCategory = incompleteCategoriesWithProgress[0];
      navigate('/record-conversation', {
        state: {
          ...nextCategory.progressItem,
          percentage: nextCategory.percentage,
          unansweredQuestionIds: nextCategory.unansweredQuestionIds,
          unansweredQuestionTexts: nextCategory.unansweredQuestionTexts
        }
      });
    }
  };

  // PROGRESS DATA FETCHING EFFECT
  useEffect(() => {
    const fetchProgressData = async () => {
      console.log('Dashboard: Starting fetchProgressData');
      console.log('Dashboard: navigationState:', navigationState);
      console.log('Dashboard: user:', user?.email);
      
      try {
        setLoading(true);
        console.log('Dashboard: Set loading to true');
        
        const currentUser = await getCurrentUser();
        const authSession = await fetchAuthSession();
        const userId = currentUser.userId;
        const idToken = authSession.tokens?.idToken?.toString();
        
        console.log('Dashboard: Got auth data, userId:', userId);
        
        if (!idToken) {
          throw new Error('No authentication token available. Please log in again.');
        }

        console.log('Dashboard: Making API call to PROGRESS_SUMMARY_2');
        const progressResponse = await fetch(
          buildApiUrl(API_CONFIG.ENDPOINTS.PROGRESS_SUMMARY_2, { userId }),
          {
            headers: {
              'Authorization': `Bearer ${idToken}`
            }
          }
        );
        
        console.log('Dashboard: API response status:', progressResponse.status);
        
        if (!progressResponse.ok) {
          throw new Error('Failed to fetch progress data');
        }
        
        const progressJson = await progressResponse.json();
        console.log('Dashboard: API response data:', progressJson);
        console.log('Dashboard: progressItems length:', progressJson.progressItems?.length);
        
        let progressItems = progressJson.progressItems || [];
        
        // If we have passed updated data, use it to update the specific item
        if (navigationState?.updatedProgressItem) {
          console.log('Dashboard: Processing passed updated data');
          const updatedItem = navigationState.updatedProgressItem;
          
          // Validate updated data consistency
          if (updatedItem.remainQuestAtCurrLevel.length !== updatedItem.remainQuestTextAtCurrLevel.length) {
            console.warn('Dashboard: Inconsistent array lengths in updated progress item');
          }
          
          progressItems = progressItems.map(item => 
            item.questionType === updatedItem.questionType ? updatedItem : item
          );
          
          // Note: Level progression is now handled by the automatic check below
        }
        
        console.log('Dashboard: Processing progress items, count:', progressItems.length);
        
        // Process the progress items
        const questionTypes = [];
        const friendlyNames = [];
        const numValidQuestions = [];
        const progressDataMap = {};
        const unansweredQuestionsMap = {};
        const unansweredQuestionTextsMap = {};
        
        try {
          progressItems.forEach((item, index) => {
            console.log(`Dashboard: Processing item ${index}:`, item);
            questionTypes.push(item.questionType);
            friendlyNames.push(item.friendlyName);
            numValidQuestions.push(item.totalQuestAtCurrLevel);
            progressDataMap[item.questionType] = item.remainQuestAtCurrLevel.length;
            unansweredQuestionsMap[item.questionType] = item.remainQuestAtCurrLevel;
            unansweredQuestionTextsMap[item.questionType] = item.remainQuestTextAtCurrLevel || [];
          });
        } catch (processingError) {
          console.error('Dashboard: Error processing progress items:', processingError);
          throw processingError;
        }
        
        console.log('Dashboard: Processed data - questionTypes:', questionTypes);
        console.log('Dashboard: Processed data - friendlyNames:', friendlyNames);
        console.log('Dashboard: Processed data - progressDataMap:', progressDataMap);
        
        // AUTOMATIC LEVEL PROGRESSION CHECK
        // Check if all current level questions are completed and advance level if needed
        const allCurrentLevelComplete = progressItems.length > 0 && progressItems.every(item => 
          item.remainQuestAtCurrLevel && item.remainQuestAtCurrLevel.length === 0
        );
        
        console.log('Dashboard: Level completion check:', {
          progressItemsCount: progressItems.length,
          allCurrentLevelComplete,
          progressItems: progressItems.map(item => ({
            questionType: item.questionType,
            remainingCount: item.remainQuestAtCurrLevel?.length || 0,
            currentLevel: item.currentQuestLevel
          }))
        });
        
        if (allCurrentLevelComplete) {
          console.log('Dashboard: All current level questions complete, calling INCREMENT_LEVEL_2');
          
          try {
            const incrementResponse = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.INCREMENT_LEVEL_2), {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${idToken}`,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({ questionType: progressItems[0]?.questionType || 'auto' })
            });
            
            console.log('Dashboard: INCREMENT_LEVEL_2 response status:', incrementResponse.status);
            
            if (incrementResponse.ok) {
              const result = await incrementResponse.json();
              console.log('Dashboard: INCREMENT_LEVEL_2 result:', result);
              
              if (result.levelComplete && result.updatedProgressItems) {
                console.log('Dashboard: Level advanced successfully, updating progress items');
                
                // Update progressItems with new level data
                progressItems = result.updatedProgressItems;
                
                // Reprocess the updated progress items
                const updatedQuestionTypes = [];
                const updatedFriendlyNames = [];
                const updatedNumValidQuestions = [];
                const updatedProgressDataMap = {};
                const updatedUnansweredQuestionsMap = {};
                const updatedUnansweredQuestionTextsMap = {};
                
                progressItems.forEach((item) => {
                  updatedQuestionTypes.push(item.questionType);
                  updatedFriendlyNames.push(item.friendlyName);
                  updatedNumValidQuestions.push(item.totalQuestAtCurrLevel);
                  updatedProgressDataMap[item.questionType] = item.remainQuestAtCurrLevel.length;
                  updatedUnansweredQuestionsMap[item.questionType] = item.remainQuestAtCurrLevel;
                  updatedUnansweredQuestionTextsMap[item.questionType] = item.remainQuestTextAtCurrLevel || [];
                });
                
                // Update the processed data arrays
                questionTypes.length = 0;
                questionTypes.push(...updatedQuestionTypes);
                friendlyNames.length = 0;
                friendlyNames.push(...updatedFriendlyNames);
                numValidQuestions.length = 0;
                numValidQuestions.push(...updatedNumValidQuestions);
                Object.assign(progressDataMap, updatedProgressDataMap);
                Object.assign(unansweredQuestionsMap, updatedUnansweredQuestionsMap);
                Object.assign(unansweredQuestionTextsMap, updatedUnansweredQuestionTextsMap);
                
                console.log('Dashboard: Successfully processed level advancement');
                
                // Show success toast
                try {
                  const { toast } = await import('@/hooks/use-toast');
                  toast({
                    title: "Level Complete!",
                    description: `Congratulations! You completed Level ${result.newGlobalLevel - 1}. Level ${result.newGlobalLevel} is now unlocked!`,
                  });
                } catch (toastError) {
                  console.warn('Dashboard: Could not show toast notification:', toastError);
                }
              } else {
                console.warn('Dashboard: INCREMENT_LEVEL_2 returned success but levelComplete=false or no updatedProgressItems');
              }
            } else {
              // Handle HTTP error responses
              const errorResult = await incrementResponse.json().catch(() => ({ error: 'Unknown error' }));
              console.error('Dashboard: INCREMENT_LEVEL_2 HTTP error:', {
                status: incrementResponse.status,
                statusText: incrementResponse.statusText,
                error: errorResult
              });
              
              // Show error message to user
              try {
                const { toast } = await import('@/hooks/use-toast');
                toast({
                  title: "Level Advancement Failed",
                  description: `Unable to advance to next level: ${errorResult.error || 'Server error'}. Please try refreshing the page.`,
                  variant: "destructive"
                });
              } catch (toastError) {
                console.warn('Dashboard: Could not show error toast:', toastError);
              }
            }
          } catch (networkError) {
            console.error('Dashboard: Network error in level progression:', networkError);
            
            // Show network error message to user
            try {
              const { toast } = await import('@/hooks/use-toast');
              toast({
                title: "Connection Error",
                description: "Unable to advance to next level due to connection issues. Please check your internet and try refreshing the page.",
                variant: "destructive"
              });
            } catch (toastError) {
              console.warn('Dashboard: Could not show network error toast:', toastError);
            }
          }
        }
        
        console.log('Dashboard: Setting state data');
        setQuestionTypeData({
          questionTypes,
          friendlyNames,
          numValidQuestions
        });
        setProgressData(progressDataMap);
        setUnansweredQuestionsData(unansweredQuestionsMap);
        setUnansweredQuestionTextsData(unansweredQuestionTextsMap);
        setProgressItems(progressItems);
        
        console.log('Dashboard: State data set successfully');
        
      } catch (error) {
        console.error('Dashboard: Error in fetchProgressData:', error);
        setError(error.message);
      } finally {
        console.log('Dashboard: Setting loading to false');
        setLoading(false);
      }
    };

    if (user) {
      console.log('Dashboard: User exists, calling fetchProgressData');
      fetchProgressData();
    } else {
      console.log('Dashboard: No user, skipping fetchProgressData');
    }
  }, [user, navigationState]);

  console.log('Dashboard render - loading:', loading, 'error:', error, 'questionTypeData:', questionTypeData);

  // LOADING STATE RENDER
  // Show loading message while fetching progress data
  if (loading) {
    console.log('Dashboard: Showing loading state');
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold mb-4">Your Progress</h3>
        <p className="text-gray-600">Loading your progress...</p>
      </div>
    );
  }

  // ERROR STATE RENDER
  // Show error message with retry option if API call fails
  if (error) {
    console.log('Dashboard: Showing error state:', error);
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold mb-4">Your Progress</h3>
        <p className="text-red-600">Error loading progress: {error}</p>
        {/* Retry button that reloads entire page to reset state */}
        <Button 
          onClick={() => window.location.reload()} // Full page reload to reset all state
          className="mt-4 bg-legacy-purple hover:bg-legacy-navy"
        >
          Retry
        </Button>
      </div>
    );
  }

  // NO DATA STATE RENDER
  // Handle case where API returns successfully but with no question data
  if (!questionTypeData) {
    console.log('Dashboard: Showing no data state');
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold mb-4">Your Progress</h3>
        <p className="text-gray-600">No question data available.</p>
      </div>
    );
  }

  console.log('Dashboard: Rendering progress bars for', questionTypeData.questionTypes.length, 'question types');

  // Calculate if there are any incomplete categories
  const hasIncompleteCategories = questionTypeData.questionTypes.some((questionType, index) => {
    const totalQuestions = questionTypeData.numValidQuestions[index];
    const unansweredCount = progressData[questionType] || 0;
    const percentage = totalQuestions > 0 ? Math.round(((totalQuestions - unansweredCount) / totalQuestions) * 100) : 0;
    return percentage < 100;
  });

  // MAIN PROGRESS SECTION RENDER
  // Display progress bars for each question category with interactive navigation
  return (
    <>
      {/* CONTINUE RECORDING BUTTON */}
      {/* Primary action button that intelligently selects the next best category */}
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

      {/* ALL COMPLETE MESSAGE */}
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
      
      {/* OVERALL PROGRESS SECTION */}
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
      
      {/* CATEGORY PROGRESS SECTION */}
      <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center gap-2 mb-6">
        <h3 className="text-xl font-semibold">Your Progress</h3>
        <InfoTooltip content="Click any progress bar to record responses for that category. Complete all categories to advance to the next level" />
      </div>
      
      {/* PROGRESS BARS CONTAINER */}
      {/* Responsive grid: 1 column mobile, 2 columns tablet+ (sm breakpoint = 640px) */}
      <div className="relative grid grid-cols-1 sm:grid-cols-2 gap-6 sm:gap-x-8">
        {/* Vertical divider line between columns (tablet and desktop) */}
        <div className="hidden sm:block absolute left-1/2 top-0 bottom-0 w-px bg-gray-200 -translate-x-1/2" />
        
        {/* ITERATE THROUGH EACH QUESTION TYPE */}
        {/* Map over question types and render progress bar for each */}
        {questionTypeData.questionTypes.map((questionType, index) => {
          // FIND CORRESPONDING PROGRESS ITEM FROM userQuestionLevelProgressDB
          const progressItem = progressItems.find(item => item.questionType === questionType);
          
          // CALCULATE PROGRESS METRICS FOR THIS QUESTION TYPE
          // Use parallel array indexing to get corresponding data
          const friendlyName = questionTypeData.friendlyNames[index];      // Human-readable name
          const totalQuestions = questionTypeData.numValidQuestions[index]; // Total valid questions
          const unansweredCount = progressData[questionType] || 0;          // Remaining questions
          const answeredCount = totalQuestions - unansweredCount;           // Completed questions
          const percentage = totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : 0; // Progress %
          const currentLevel = progressItem?.currentQuestLevel || 1;        // Current level from userQuestionLevelProgressDB

          /**
           * PROGRESS BAR CLICK HANDLER
           * 
           * Navigates to recording page with specific question type context.
           * This enables category-specific recording instead of general recording.
           * 
           * NAVIGATION STATE:
           * - All data from userQuestionLevelProgressDB
           * - Calculated progress metrics for UI display
           */
          const handleProgressBarClick = () => {
            // Don't allow navigation if this question type is completed
            if (percentage === 100) {
              return;
            }
            
            navigate('/record-conversation', {
              state: { // Pass all progress item data via React Router state
                ...progressItem,                                               // All userQuestionLevelProgressDB data
                percentage,                                                    // Calculated completion percentage
                unansweredQuestionIds: unansweredQuestionsData[questionType] || [], // Specific question IDs
                unansweredQuestionTexts: unansweredQuestionTextsData[questionType] || [] // Specific question texts
              }
            });
          };

          // RENDER INDIVIDUAL PROGRESS ITEM
          return (
            <div key={questionType} className="space-y-2"> {/* Unique key for React rendering */}
              {/* PROGRESS HEADER */}
              {/* Category name with level and completion stats */}
              <div className="flex justify-between items-center">
                <h4 className="font-medium text-gray-900">Level {currentLevel} - {friendlyName}</h4> {/* Level + Category display name */}
                <span className="text-sm text-gray-600">
                  {answeredCount} of {totalQuestions} completed {/* Progress fraction */}
                </span>
              </div>
              
              {/* INTERACTIVE PROGRESS BAR */}
              {/* Clickable progress bar that navigates to category-specific recording */}
              <div 
                className={`flex items-center space-x-3 transition-all ${
                  percentage === 100 
                    ? 'cursor-default opacity-75' 
                    : 'cursor-pointer hover:opacity-80'
                }`}
                onClick={handleProgressBarClick} // Navigate with question type context
                title={percentage === 100 ? 'Level completed!' : `Click to record responses for ${friendlyName}`} // Tooltip for user guidance
              >
                {/* Progress bar component */}
                <Progress 
                  value={percentage}        // Completion percentage (0-100)
                  className="flex-1 h-3"   // Full width with fixed height
                />
                {/* Percentage display */}
                <span className="text-sm font-medium text-gray-700 min-w-[3rem]">
                  {percentage}% {/* Formatted percentage with consistent width */}
                </span>
                {/* Arrow icon for incomplete categories */}
                {percentage < 100 && (
                  <ChevronRight className="h-4 w-4 text-gray-400 hover:text-legacy-purple transition-colors" />
                )}
              </div>
              
              {/* ADDITIONAL INFO */}
              {/* Total questions count for context and completion message */}
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
