
import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/contexts/AuthContext";
import { ArrowRight } from "lucide-react";
import { buildApiUrl, API_CONFIG } from '@/config/api';
import { getCurrentUser, fetchAuthSession } from 'aws-amplify/auth';
import { useToast } from "@/hooks/use-toast";
import { StreakCounter } from "@/components/StreakCounter";
import { streakService, StreakData } from "@/services/streakService";
import { ConversationInterface } from "@/components/ConversationInterface";
import VideoMemoryRecorder from "@/components/VideoMemoryRecorder";
import { videoStorageService } from "@/services/videoService";
import { Header } from "@/components/Header";

const RecordResponse = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();
  
  // Get data passed from progress bar click
  const progressData = location.state;
  
  // State for category-specific questions
  const [categoryQuestions, setCategoryQuestions] = useState(
    progressData?.remainQuestTextAtCurrLevel || []
  );
  const [categoryQuestionIds, setCategoryQuestionIds] = useState(
    progressData?.remainQuestAtCurrLevel || []
  );
  const [currentCategoryQuestion, setCurrentCategoryQuestion] = useState(null);
  const [currentCategoryQuestionId, setCurrentCategoryQuestionId] = useState(null);
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const [questionError, setQuestionError] = useState(null);
  const [levelCompleted, setLevelCompleted] = useState(false);
  const [streakData, setStreakData] = useState<StreakData | null>(null);
  const [streakLoading, setStreakLoading] = useState(true);
  const [conversationStarted, setConversationStarted] = useState(false);
  const [showVideoMemory, setShowVideoMemory] = useState(false);
  const [audioDetailedSummary, setAudioDetailedSummary] = useState<string>('');

  // Helper function to build navigation state with updated progress data
  const buildNavigationState = () => {
    if (!progressData) return null;
    
    return {
      updatedProgressItem: {
        ...progressData,
        remainQuestAtCurrLevel: categoryQuestionIds,
        remainQuestTextAtCurrLevel: categoryQuestions
      },
      questionTypeCompleted: levelCompleted
    };
  };

  // Navigation guard - redirect if no category selected
  useEffect(() => {
    if (!progressData || !progressData.questionType) {
      toast({
        title: "Please Select a Category",
        description: "Choose a question category from your dashboard to begin recording.",
        variant: "destructive"
      });
      navigate("/dashboard");
    }
  }, [progressData, navigate, toast]);

  // Pick initial question
  useEffect(() => {
    if (categoryQuestions.length > 0 && !currentCategoryQuestion) {
      const randomIndex = Math.floor(Math.random() * categoryQuestions.length);
      setCurrentCategoryQuestion(categoryQuestions[randomIndex]);
      setCurrentCategoryQuestionId(categoryQuestionIds[randomIndex]);
    }
  }, [categoryQuestions, categoryQuestionIds, currentCategoryQuestion]);

  // Load streak data
  useEffect(() => {
    const loadStreak = async () => {
      if (!user?.id) return;
      try {
        const data = await streakService.getCachedStreak(user.id);
        setStreakData(data);
      } catch (error) {
        console.error('Error loading streak:', error);
      } finally {
        setStreakLoading(false);
      }
    };
    loadStreak();
  }, [user?.id]);
  
  // Skip question function
  const handleSkipQuestion = () => {
    if (categoryQuestions.length <= 1) {
      return;
    }
    
    // Find a different question using same index for both arrays
    let randomIndex;
    do {
      randomIndex = Math.floor(Math.random() * categoryQuestions.length);
    } while (categoryQuestions[randomIndex] === currentCategoryQuestion && categoryQuestions.length > 1);
    
    setCurrentCategoryQuestion(categoryQuestions[randomIndex]);
    setCurrentCategoryQuestionId(categoryQuestionIds[randomIndex]);
  };
  
  // Handle conversation completion
  const handleConversationComplete = async (finalScore: number, audioTranscriptUrl: string, audioDetailedSummary: string) => {
    console.log('[VIDEO MEMORY FLOW] Conversation completed:', { 
      finalScore, 
      audioTranscriptUrl, 
      audioDetailedSummary,
      audioDetailedSummaryLength: audioDetailedSummary?.length,
      audioDetailedSummaryType: typeof audioDetailedSummary,
      hasAudioDetailedSummary: !!audioDetailedSummary
    });
    
    // Use summary from WebSocket message
    if (audioDetailedSummary) {
      console.log('[VIDEO MEMORY FLOW] Setting video memory state - summary available');
      setAudioDetailedSummary(audioDetailedSummary);
      setShowVideoMemory(true);
      setConversationStarted(false);
      console.log('[VIDEO MEMORY FLOW] State updated:', { showVideoMemory: true, conversationStarted: false });
    } else {
      console.log('[VIDEO MEMORY FLOW] No summary available, skipping video memory');
      // No summary available, skip to next question
      await handleRecordingSubmitted();
    }
  };

  // Handle video memory completion
  const handleVideoMemoryComplete = async () => {
    setShowVideoMemory(false);
    setAudioDetailedSummary('');
    await handleRecordingSubmitted();
  };

  const handleVideoMemorySkip = async () => {
    setShowVideoMemory(false);
    setAudioDetailedSummary('');
    await handleRecordingSubmitted();
  };

  const handleVideoMemoryDashboard = async () => {
    setShowVideoMemory(false);
    setAudioDetailedSummary('');
    await handleRecordingSubmitted();
    const navigationState = buildNavigationState();
    navigate("/dashboard", navigationState ? { state: navigationState } : undefined);
  };

  // Handle recording submission and update progress
  const handleRecordingSubmitted = async () => {
    if (!currentCategoryQuestionId) return;
    
    // Remove the answered question from both arrays using same index
    const currentIndex = categoryQuestionIds.indexOf(currentCategoryQuestionId);
    if (currentIndex !== -1) {
      const newQuestionIds = categoryQuestionIds.filter((_, index) => index !== currentIndex);
      const newQuestionTexts = categoryQuestions.filter((_, index) => index !== currentIndex);
      
      setCategoryQuestionIds(newQuestionIds);
      setCategoryQuestions(newQuestionTexts);
      
      console.log('RecordResponse: Question answered, arrays updated:', {
        originalLength: progressData.totalQuestAtCurrLevel,
        newQuestionIdsLength: newQuestionIds.length,
        newQuestionTextsLength: newQuestionTexts.length,
        questionsAnswered: progressData.totalQuestAtCurrLevel - newQuestionIds.length
      });
      
      // Check if question type completed
      if (newQuestionIds.length === 0) {
        const { toast } = await import('@/hooks/use-toast');
        toast({
          title: "Question Type Complete!",
          description: `You completed Level ${progressData.currentQuestLevel} of ${progressData.friendlyName}. Return to dashboard to continue.`,
        });
        setLevelCompleted(true);
      }
      
      // Pick next random question if available
      if (newQuestionTexts.length > 0) {
        const randomIndex = Math.floor(Math.random() * newQuestionTexts.length);
        setCurrentCategoryQuestion(newQuestionTexts[randomIndex]);
        setCurrentCategoryQuestionId(newQuestionIds[randomIndex]);
      } else {
        // No more questions - disable UI and show completion message
        setCurrentCategoryQuestion("Level completed! Return to dashboard to continue.");
        setCurrentCategoryQuestionId(null);
        setLevelCompleted(true);
      }
    }
  };



  // Redirect to login if not authenticated
  if (!user) {
    navigate("/login");
    return null;
  }

  // Check if user is a benefactor and redirect
  if (user.personaType === 'legacy_benefactor') {
    navigate("/benefactor-dashboard");
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Shared Header with UserMenu */}
      <Header />
      
      {/* Page-specific context bar */}
      <div className="bg-white border-b">
        <div className="container mx-auto py-3 px-4 flex justify-between items-center">
          <h2 className="text-lg font-medium text-legacy-navy">
            Level {progressData?.currentQuestLevel} - {progressData?.friendlyName}
          </h2>
          <Button variant="outline" onClick={() => {
            const navigationState = buildNavigationState();
            navigate("/dashboard", navigationState ? { state: navigationState } : undefined);
          }}>
            Back to Dashboard
          </Button>
        </div>
      </div>

      <main className="container mx-auto px-4 py-8">
        {/* STREAK DISPLAY */}
        <div className="mb-6">
          <StreakCounter 
            streakData={streakData} 
            loading={streakLoading}
            showFreeze={true}
          />
        </div>

        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="flex justify-between items-center mb-2">
              <h3 className="font-medium text-gray-900">Level {progressData?.currentQuestLevel} - {progressData?.friendlyName}</h3>
              <span className="text-sm text-gray-600">
                {loadingQuestions ? "Loading..." : `${progressData?.totalQuestAtCurrLevel - categoryQuestions.length} of ${progressData?.totalQuestAtCurrLevel} completed`}
              </span>
            </div>
            
            <div className="flex items-center space-x-3">
              <Progress 
                value={loadingQuestions ? 0 : Math.round(((progressData?.totalQuestAtCurrLevel - categoryQuestions.length) / progressData?.totalQuestAtCurrLevel) * 100)} 
                className="flex-1 h-3"
              />
              <span className="text-sm font-medium text-gray-700 min-w-[3rem]">
                {loadingQuestions ? "..." : `${Math.round(((progressData?.totalQuestAtCurrLevel - categoryQuestions.length) / progressData?.totalQuestAtCurrLevel) * 100)}%`}
              </span>
            </div>
            
            <div className="text-xs text-gray-500 mt-2">
              {progressData?.totalQuestAtCurrLevel} total questions at this level
            </div>
          </CardContent>
        </Card>

        <Card className="mb-8">
          <CardContent className="pt-6">
            {loadingQuestions ? (
              <h2 className="text-2xl font-semibold text-center mb-6 text-gray-500">Loading questions...</h2>
            ) : questionError ? (
              <h2 className="text-2xl font-semibold text-center mb-6 text-red-600">Error loading questions: {questionError}</h2>
            ) : currentCategoryQuestion ? (
              <h2 className="text-2xl font-semibold text-center mb-6">{currentCategoryQuestion}</h2>
            ) : (
              <h2 className="text-2xl font-semibold text-center mb-6 text-gray-500">No questions available</h2>
            )}
          </CardContent>
        </Card>

        {(() => {
          console.log('[VIDEO MEMORY FLOW] Render check:', { 
            showVideoMemory, 
            levelCompleted, 
            conversationStarted,
            audioDetailedSummaryLength: audioDetailedSummary?.length 
          });
          return null;
        })()}
        {showVideoMemory ? (
          <VideoMemoryRecorder
            audioDetailedSummary={audioDetailedSummary}
            questionId={currentCategoryQuestionId || ''}
            questionType={progressData?.questionType || ''}
            onComplete={handleVideoMemoryComplete}
            onSkip={handleVideoMemorySkip}
            onDashboard={handleVideoMemoryDashboard}
          />
        ) : levelCompleted ? (
          <Card>
            <CardContent className="pt-6 text-center">
              <h3 className="text-xl font-semibold mb-4 text-green-600">Level Completed!</h3>
              <p className="text-gray-600 mb-6">
                You have completed all questions for Level {progressData?.currentQuestLevel} of {progressData?.friendlyName}.
                Return to the dashboard to see if you can advance to the next level.
              </p>
              <Button 
                onClick={() => {
                  const navigationState = buildNavigationState();
                  navigate("/dashboard", navigationState ? { state: navigationState } : undefined);
                }}
                className="bg-legacy-purple hover:bg-legacy-navy"
              >
                Return to Dashboard
              </Button>
            </CardContent>
          </Card>
        ) : conversationStarted ? (
          <ConversationInterface
            questionId={currentCategoryQuestionId || ''}
            questionText={currentCategoryQuestion || ''}
            onComplete={handleConversationComplete}
          />
        ) : (
          <Card>
            <CardContent className="pt-6">
              <h3 className="text-xl font-semibold mb-6 text-center">Ready to share your story?</h3>
              <p className="text-center text-gray-600 mb-6">
                Have a natural conversation with our AI interviewer. It will ask follow-up questions to help you share meaningful details.
              </p>
              <div className="flex justify-center gap-4">
                <Button 
                  onClick={() => setConversationStarted(true)}
                  className="bg-legacy-purple hover:bg-legacy-navy"
                >
                  Start Conversation
                </Button>
                {categoryQuestions.length > 1 && (
                  <Button 
                    onClick={handleSkipQuestion}
                    variant="outline"
                    className="border-legacy-purple text-legacy-purple hover:bg-legacy-lightPurple"
                  >
                    Skip Question <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
};

export default RecordResponse;
