import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Clock, Play, RotateCcw, Eye, Loader2 } from "lucide-react";
import { toast } from "@/hooks/use-toast";
import TestTakingUI from "@/components/psych-tests/TestTakingUI";
import TestResultsView from "@/components/psych-tests/TestResultsView";
import {
  listPsychTests,
  getTestDefinition,
  getTestProgress,
  scoreTest,
  saveTestProgress,
  exportResults,
} from "@/services/psychTestService";
import type {
  PsychTest,
  TestDefinition,
  TestResult,
  TestProgress,
  QuestionResponse,
} from "@/types/psychTests";

/**
 * PERSONAL INSIGHTS PAGE
 *
 * Entry point for the "Values & Emotions Deep Dive" content path.
 * Displays available psychological tests, handles test-taking flow,
 * and shows scored results — all managed via local view state.
 *
 * Route: /personal-insights
 * Protected by ProtectedRoute with requiredPersona="legacy_maker"
 *
 * Requirements: 10.1, 10.13, 5.5
 */

type ViewState = "list" | "taking" | "results";

const PersonalInsights: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  // View navigation
  const [view, setView] = useState<ViewState>("list");
  const [selectedTestId, setSelectedTestId] = useState<string | null>(null);

  // Data
  const [availableTests, setAvailableTests] = useState<PsychTest[]>([]);
  const [testDefinition, setTestDefinition] = useState<TestDefinition | null>(null);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [savedProgress, setSavedProgress] = useState<TestProgress | null>(null);
  const [completedResults, setCompletedResults] = useState<Map<string, TestResult>>(new Map());

  // Loading states
  const [isLoadingTests, setIsLoadingTests] = useState(true);
  const [isLoadingDefinition, setIsLoadingDefinition] = useState(false);
  const [progressMap, setProgressMap] = useState<Map<string, boolean>>(new Map());

  // Redirect unauthenticated users
  useEffect(() => {
    if (!user) {
      navigate("/login");
    }
  }, [user, navigate]);

  // Fetch available tests on mount
  useEffect(() => {
    const fetchTests = async () => {
      try {
        setIsLoadingTests(true);
        const tests = await listPsychTests();
        setAvailableTests(tests);

        // Check progress for each non-completed test
        const pMap = new Map<string, boolean>();
        await Promise.all(
          tests
            .filter((t) => !t.completedAt)
            .map(async (t) => {
              try {
                const progress = await getTestProgress(t.testId);
                pMap.set(t.testId, progress !== null);
              } catch {
                pMap.set(t.testId, false);
              }
            }),
        );
        setProgressMap(pMap);
      } catch {
        toast({
          title: "Failed to load tests",
          description: "Please try again later.",
          variant: "destructive",
        });
      } finally {
        setIsLoadingTests(false);
      }
    };
    if (user) fetchTests();
  }, [user]);

  // Start or resume a test
  const handleStartTest = useCallback(async (testId: string) => {
    setSelectedTestId(testId);
    setIsLoadingDefinition(true);
    try {
      const [definition, progress] = await Promise.all([
        getTestDefinition(testId),
        getTestProgress(testId),
      ]);
      setTestDefinition(definition);
      setSavedProgress(progress);
      setView("taking");
    } catch {
      toast({
        title: "Failed to load test",
        description: "Could not fetch the test definition. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoadingDefinition(false);
    }
  }, []);

  // View results for a completed test
  const handleViewResults = useCallback(
    async (testId: string) => {
      const cached = completedResults.get(testId);
      if (cached && testDefinition?.testId === testId) {
        setTestResult(cached);
        setSelectedTestId(testId);
        setView("results");
        return;
      }
      // Need the definition to render results
      setIsLoadingDefinition(true);
      try {
        const definition = await getTestDefinition(testId);
        setTestDefinition(definition);
        const cachedResult = completedResults.get(testId);
        if (cachedResult) {
          setTestResult(cachedResult);
          setSelectedTestId(testId);
          setView("results");
        } else {
          toast({
            title: "Results not available",
            description: "Please retake the test to view updated results.",
            variant: "destructive",
          });
        }
      } catch {
        toast({
          title: "Failed to load test",
          description: "Could not fetch the test definition.",
          variant: "destructive",
        });
      } finally {
        setIsLoadingDefinition(false);
      }
    },
    [completedResults, testDefinition],
  );

  // Handle test completion (scoring)
  const handleSubmit = useCallback(
    async (responses: QuestionResponse[]): Promise<TestResult> => {
      if (!selectedTestId) throw new Error("No test selected");
      const result = await scoreTest(selectedTestId, responses);
      return result;
    },
    [selectedTestId],
  );

  const handleTestComplete = useCallback(
    (result: TestResult) => {
      setTestResult(result);
      // Cache the result
      setCompletedResults((prev) => {
        const next = new Map(prev);
        next.set(result.testId, result);
        return next;
      });
      // Update the available tests list to reflect completion
      setAvailableTests((prev) =>
        prev.map((t) =>
          t.testId === result.testId
            ? { ...t, completedAt: result.timestamp }
            : t,
        ),
      );
      // Clear progress for this test
      setProgressMap((prev) => {
        const next = new Map(prev);
        next.delete(result.testId);
        return next;
      });
      setView("results");
    },
    [],
  );

  // Handle auto-save progress
  const handleSaveProgress = useCallback(
    async (responses: QuestionResponse[], currentQuestionIndex: number) => {
      if (!selectedTestId) return;
      await saveTestProgress(selectedTestId, responses, currentQuestionIndex);
    },
    [selectedTestId],
  );

  // Handle export
  const handleExport = useCallback(
    async (format: string) => {
      if (!testResult) return;
      try {
        const response = await exportResults(
          testResult.testId,
          testResult.version,
          testResult.timestamp,
          format,
        );
        window.open(response.downloadUrl, "_blank");
      } catch {
        toast({
          title: `${format} export failed`,
          description: "Please try again.",
          variant: "destructive",
        });
      }
    },
    [testResult],
  );

  // Navigate back to list
  const handleBackToList = useCallback(() => {
    setView("list");
    setSelectedTestId(null);
    setTestDefinition(null);
    setTestResult(null);
    setSavedProgress(null);
  }, []);

  if (!user) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <main className="container mx-auto px-4 py-8">
        {/* Back to Dashboard — always visible */}
        <Button
          variant="ghost"
          onClick={() => navigate("/dashboard")}
          className="mb-6 text-gray-600 hover:text-legacy-navy"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dashboard
        </Button>

        {/* Psych Test Progress */}
        {!isLoadingTests && availableTests.length > 0 && (
          <div className="mb-6 p-4 bg-white rounded-lg border">
            <p className="text-sm text-gray-600">
              {availableTests.filter((t) => t.completedAt).length} of {availableTests.length} assessments completed
            </p>
          </div>
        )}

        {/* Loading overlay for definition fetch */}
        {isLoadingDefinition && (
          <div className="flex justify-center items-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-legacy-purple" />
          </div>
        )}

        {/* LIST VIEW */}
        {view === "list" && !isLoadingDefinition && (
          <>
            {isLoadingTests ? (
              <div className="flex justify-center items-center py-16">
                <Loader2 className="h-8 w-8 animate-spin text-legacy-purple" />
              </div>
            ) : availableTests.length === 0 ? (
              <Card className="text-center p-8">
                <CardContent>
                  <p className="text-gray-500">
                    No psychological tests are available at this time.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {availableTests.map((test) => {
                  const hasProgress = progressMap.get(test.testId) ?? false;
                  const isCompleted = !!test.completedAt;
                  const hasResult = completedResults.has(test.testId);

                  return (
                    <Card key={test.testId} className="flex flex-col">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-lg text-legacy-navy">
                          {test.testName}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="flex flex-col flex-1">
                        <p className="text-sm text-gray-600 mb-4 flex-1">
                          {test.description}
                        </p>
                        <div className="flex items-center text-xs text-gray-400 mb-4">
                          <Clock className="h-3 w-3 mr-1" />
                          ~{test.estimatedMinutes} min
                        </div>

                        {isCompleted && hasResult ? (
                          <Button
                            variant="outline"
                            className="w-full"
                            onClick={() => handleViewResults(test.testId)}
                          >
                            <Eye className="h-4 w-4 mr-2" />
                            View Results
                          </Button>
                        ) : isCompleted ? (
                          <Button
                            className="w-full bg-legacy-purple hover:bg-legacy-navy"
                            onClick={() => handleStartTest(test.testId)}
                          >
                            <RotateCcw className="h-4 w-4 mr-2" />
                            Retake Test
                          </Button>
                        ) : hasProgress ? (
                          <Button
                            className="w-full bg-legacy-purple hover:bg-legacy-navy"
                            onClick={() => handleStartTest(test.testId)}
                          >
                            <RotateCcw className="h-4 w-4 mr-2" />
                            Resume
                          </Button>
                        ) : (
                          <Button
                            className="w-full bg-legacy-purple hover:bg-legacy-navy"
                            onClick={() => handleStartTest(test.testId)}
                          >
                            <Play className="h-4 w-4 mr-2" />
                            Start Test
                          </Button>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </>
        )}

        {/* TAKING VIEW */}
        {view === "taking" && testDefinition && !isLoadingDefinition && (
          <TestTakingUI
            testDefinition={testDefinition}
            onComplete={handleTestComplete}
            onBack={handleBackToList}
            savedProgress={savedProgress}
            onSubmit={handleSubmit}
            onSaveProgress={handleSaveProgress}
          />
        )}

        {/* RESULTS VIEW */}
        {view === "results" && testResult && testDefinition && !isLoadingDefinition && (
          <TestResultsView
            result={testResult}
            testDefinition={testDefinition}
            onExport={handleExport}
            onBack={handleBackToList}
          />
        )}
      </main>
    </div>
  );
};

export default PersonalInsights;
