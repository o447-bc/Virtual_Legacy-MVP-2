import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Progress } from '@/components/ui/progress';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, ArrowRight, Loader2 } from 'lucide-react';
import { toast } from '@/hooks/use-toast';
import VideoRecorder from '@/components/VideoRecorder';
import type {
  TestDefinition,
  TestProgress,
  TestResult,
  Question,
  QuestionResponse,
} from '@/types/psychTests';
import {
  calculateProgress,
  groupQuestionsByFacet,
  shouldShowVideoPrompt,
  controlKindForResponseType,
} from './testUtils';

// Re-export for backward compatibility
export {
  calculateProgress,
  groupQuestionsByFacet,
  shouldShowVideoPrompt,
  controlKindForResponseType,
} from './testUtils';

// ---------------------------------------------------------------------------
// Auto-save with exponential backoff
// ---------------------------------------------------------------------------

const AUTO_SAVE_INTERVAL_MS = 30_000;
const MAX_RETRIES = 3;

async function retryWithBackoff(
  fn: () => Promise<void>,
  retries = MAX_RETRIES,
): Promise<void> {
  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      await fn();
      return;
    } catch (err) {
      if (attempt === retries - 1) throw err;
      // Exponential backoff: 1s, 2s, 4s
      await new Promise((r) => setTimeout(r, 1000 * Math.pow(2, attempt)));
    }
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const LIKERT_LABELS = [
  'Strongly Disagree',
  'Disagree',
  'Neutral',
  'Agree',
  'Strongly Agree',
];

interface QuestionRendererProps {
  question: Question;
  value: number | undefined;
  onChange: (questionId: string, answer: number) => void;
}

const QuestionRenderer: React.FC<QuestionRendererProps> = ({
  question,
  value,
  onChange,
}) => {
  const hintId = `hint-${question.questionId}`;
  const kind = controlKindForResponseType(question.responseType);

  return (
    <div
      className="py-4 border-b border-gray-100 last:border-b-0"
      role="group"
      aria-describedby={question.accessibilityHint ? hintId : undefined}
    >
      <p className="text-sm font-medium text-gray-800 mb-3">{question.text}</p>
      {question.accessibilityHint && (
        <p id={hintId} className="sr-only">
          {question.accessibilityHint}
        </p>
      )}

      {kind === 'likert' && (
        <RadioGroup
          value={value !== undefined ? String(value) : ""}
          onValueChange={(v) => onChange(question.questionId, Number(v))}
          className="flex flex-wrap gap-2 sm:gap-3"
        >
          {LIKERT_LABELS.map((label, i) => {
            const val = i + 1;
            return (
              <Label
                key={val}
                htmlFor={`${question.questionId}-${val}`}
                className={`flex flex-col items-center gap-1 cursor-pointer rounded-lg border px-3 py-2 text-xs sm:text-sm transition-colors ${
                  value === val
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <RadioGroupItem
                  id={`${question.questionId}-${val}`}
                  value={String(val)}
                  className="sr-only"
                />
                <span className="font-semibold">{val}</span>
                <span className="text-center leading-tight hidden sm:block">
                  {label}
                </span>
              </Label>
            );
          })}
        </RadioGroup>
      )}

      {kind === 'bipolar' && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>{question.options[0] ?? ''}</span>
            <span>{question.options[question.options.length - 1] ?? ''}</span>
          </div>
          <RadioGroup
            value={value !== undefined ? String(value) : ""}
            onValueChange={(v) => onChange(question.questionId, Number(v))}
            className="flex justify-between gap-2"
          >
            {[1, 2, 3, 4, 5].map((val) => (
              <Label
                key={val}
                htmlFor={`${question.questionId}-${val}`}
                className={`flex items-center justify-center w-10 h-10 rounded-full border cursor-pointer transition-colors ${
                  value === val
                    ? 'border-primary bg-primary text-white'
                    : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <RadioGroupItem
                  id={`${question.questionId}-${val}`}
                  value={String(val)}
                  className="sr-only"
                />
                <span className="text-sm font-medium">{val}</span>
              </Label>
            ))}
          </RadioGroup>
        </div>
      )}

      {kind === 'radio' && (
        <RadioGroup
          value={value !== undefined ? String(value) : ""}
          onValueChange={(v) => onChange(question.questionId, Number(v))}
          className="space-y-2"
        >
          {question.options.map((opt, i) => {
            const val = i + 1;
            return (
              <div key={val} className="flex items-center gap-2">
                <RadioGroupItem
                  id={`${question.questionId}-${val}`}
                  value={String(val)}
                />
                <Label
                  htmlFor={`${question.questionId}-${val}`}
                  className="text-sm cursor-pointer"
                >
                  {opt}
                </Label>
              </div>
            );
          })}
        </RadioGroup>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface TestTakingUIProps {
  testDefinition: TestDefinition;
  onComplete: (result: TestResult) => void;
  onBack: () => void;
  savedProgress?: TestProgress | null;
  /** Called when the user submits responses. Returns the TestResult. */
  onSubmit?: (responses: QuestionResponse[]) => Promise<TestResult>;
  /** Called periodically to auto-save progress */
  onSaveProgress?: (
    responses: QuestionResponse[],
    currentQuestionIndex: number,
  ) => Promise<void>;
}

const TestTakingUI: React.FC<TestTakingUIProps> = ({
  testDefinition,
  onComplete,
  onBack,
  savedProgress,
  onSubmit,
  onSaveProgress,
}) => {
  // If saved progress exists, skip consent
  const [consentGiven, setConsentGiven] = useState(!!savedProgress);
  const [consentChecked, setConsentChecked] = useState(false);

  // Responses map: questionId -> answer (1-based)
  const [responses, setResponses] = useState<Map<string, number>>(() => {
    const map = new Map<string, number>();
    if (savedProgress?.responses) {
      for (const r of savedProgress.responses) {
        map.set(r.questionId, r.answer);
      }
    }
    return map;
  });

  // Current page index (for page-break navigation)
  const [currentPage, setCurrentPage] = useState(() => {
    if (savedProgress?.currentQuestionIndex != null) {
      // Determine which page the saved index falls on
      return 0; // Will be computed below after pages are built
    }
    return 0;
  });

  const [showVideoPrompt, setShowVideoPrompt] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Refs for auto-save (so the interval/visibility callbacks see latest state)
  const responsesRef = useRef(responses);
  responsesRef.current = responses;
  const currentPageRef = useRef(currentPage);
  currentPageRef.current = currentPage;

  // Build pages from questions grouped by facet + pageBreakAfter
  const pages = useMemo(() => {
    const facetGroups = groupQuestionsByFacet(testDefinition.questions);
    const result: { facet: string; questions: Question[] }[][] = [];
    let currentPageQuestions: { facet: string; questions: Question[] }[] = [];

    for (const group of facetGroups) {
      currentPageQuestions.push(group);
      // Check if the last question in this group has pageBreakAfter
      const lastQ = group.questions[group.questions.length - 1];
      if (lastQ?.pageBreakAfter) {
        result.push(currentPageQuestions);
        currentPageQuestions = [];
      }
    }
    // Push remaining questions as the last page
    if (currentPageQuestions.length > 0) {
      result.push(currentPageQuestions);
    }
    // If no pages were created (no questions), push an empty page
    if (result.length === 0) {
      result.push([]);
    }
    // Filter out any empty trailing pages (e.g. from pageBreakAfter on the last question)
    while (result.length > 1 && result[result.length - 1].length === 0) {
      result.pop();
    }
    return result;
  }, [testDefinition.questions]);

  // Compute initial page from saved progress
  const initialPage = useMemo(() => {
    if (!savedProgress?.currentQuestionIndex) return 0;
    let questionCount = 0;
    for (let pageIdx = 0; pageIdx < pages.length; pageIdx++) {
      for (const group of pages[pageIdx]) {
        questionCount += group.questions.length;
      }
      if (questionCount > savedProgress.currentQuestionIndex) {
        return pageIdx;
      }
    }
    return pages.length - 1;
  }, [savedProgress, pages]);

  // Set initial page once
  React.useEffect(() => {
    if (savedProgress) {
      setCurrentPage(initialPage);
    }
  }, [initialPage, savedProgress]);

  // --- Auto-save logic (11.2) ---
  const doAutoSave = useCallback(async () => {
    if (!onSaveProgress || !testDefinition.saveProgressEnabled) return;
    if (responsesRef.current.size === 0) return;

    const responseArray: QuestionResponse[] = Array.from(
      responsesRef.current.entries(),
    ).map(([questionId, answer]) => ({ questionId, answer }));

    // Compute flat question index from current page
    let idx = 0;
    for (let p = 0; p < currentPageRef.current; p++) {
      for (const group of pages[p]) {
        idx += group.questions.length;
      }
    }

    try {
      await retryWithBackoff(() => onSaveProgress(responseArray, idx));
    } catch {
      toast({
        title: 'Auto-save failed',
        description: 'Your progress could not be saved. Please check your connection.',
        variant: 'destructive',
      });
    }
  }, [onSaveProgress, testDefinition.saveProgressEnabled, pages]);

  // Auto-save interval (every 30s)
  useEffect(() => {
    if (!consentGiven || !testDefinition.saveProgressEnabled || !onSaveProgress) return;
    const id = setInterval(doAutoSave, AUTO_SAVE_INTERVAL_MS);
    return () => clearInterval(id);
  }, [consentGiven, testDefinition.saveProgressEnabled, onSaveProgress, doAutoSave]);

  // Auto-save on visibility change (tab switch / minimize)
  useEffect(() => {
    if (!consentGiven || !testDefinition.saveProgressEnabled || !onSaveProgress) return;
    const handleVisibility = () => {
      if (document.visibilityState === 'hidden') {
        doAutoSave();
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [consentGiven, testDefinition.saveProgressEnabled, onSaveProgress, doAutoSave]);

  const totalQuestions = testDefinition.questions.length;
  const answeredCount = responses.size;
  const progressPercent = calculateProgress(answeredCount, totalQuestions);

  const isLastPage = currentPage >= pages.length - 1;

  // Flat index of the first question on the current page
  const currentPageStartIndex = useMemo(() => {
    let idx = 0;
    for (let p = 0; p < currentPage; p++) {
      for (const group of pages[p]) {
        idx += group.questions.length;
      }
    }
    return idx;
  }, [currentPage, pages]);

  const handleAnswer = useCallback(
    (questionId: string, answer: number) => {
      setResponses((prev) => {
        const next = new Map(prev);
        next.set(questionId, answer);
        return next;
      });
    },
    [],
  );

  const handleBeginTest = () => {
    setConsentGiven(true);
  };

  const handleNextPage = () => {
    // Check for video prompt on page transition
    const nextPageStart = currentPageStartIndex + pages[currentPage].reduce(
      (sum, g) => sum + g.questions.length,
      0,
    );
    const freq = testDefinition.questions[0]?.videoPromptFrequency;
    if (freq && freq > 0 && shouldShowVideoPrompt(nextPageStart, freq)) {
      setShowVideoPrompt(true);
      return;
    }
    setCurrentPage((p) => Math.min(p + 1, pages.length - 1));
  };

  const handlePrevPage = () => {
    setCurrentPage((p) => Math.max(p - 1, 0));
  };

  const handleVideoComplete = () => {
    setShowVideoPrompt(false);
    setCurrentPage((p) => Math.min(p + 1, pages.length - 1));
  };

  const handleSubmit = async () => {
    if (!onSubmit) return;
    setIsSubmitting(true);
    try {
      const responseArray: QuestionResponse[] = Array.from(responses.entries()).map(
        ([questionId, answer]) => ({ questionId, answer }),
      );
      const result = await onSubmit(responseArray);
      onComplete(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong. Please try again.';
      toast({
        title: 'Scoring failed',
        description: message.includes('Missing responses')
          ? 'Please answer all questions before submitting.'
          : message,
        variant: 'destructive',
      });
      setIsSubmitting(false);
    }
  };

  // --- Consent Screen ---
  if (!consentGiven) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8">
        <Button
          variant="ghost"
          onClick={onBack}
          className="mb-6 text-gray-600 hover:text-legacy-navy"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>

        <Card>
          <CardHeader>
            <CardTitle className="text-xl text-legacy-navy">
              {testDefinition.consentBlock.title}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-line">
              {testDefinition.consentBlock.bodyText}
            </p>

            <div className="flex items-start gap-3">
              <Checkbox
                id="consent-checkbox"
                checked={consentChecked}
                onCheckedChange={(checked) =>
                  setConsentChecked(checked === true)
                }
              />
              <Label
                htmlFor="consent-checkbox"
                className="text-sm cursor-pointer leading-relaxed"
              >
                {testDefinition.consentBlock.requiredCheckboxLabel}
              </Label>
            </div>

            <Button
              onClick={handleBeginTest}
              disabled={!consentChecked}
              className="w-full bg-legacy-purple hover:bg-legacy-navy"
            >
              Begin Test
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // --- Video Prompt ---
  if (showVideoPrompt) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8">
        <h2 className="text-lg font-semibold text-legacy-navy mb-4">
          {testDefinition.videoPromptTrigger}
        </h2>
        <VideoRecorder
          onSkipQuestion={handleVideoComplete}
          canSkip
          onRecordingSubmitted={handleVideoComplete}
        />
      </div>
    );
  }

  // --- Question Pages ---
  const currentGroups = pages[currentPage] ?? [];

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      {/* Back button */}
      <Button
        variant="ghost"
        onClick={onBack}
        className="mb-4 text-gray-600 hover:text-legacy-navy"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back
      </Button>

      {/* Progress bar */}
      <div className="mb-6 space-y-2">
        <div className="flex justify-between text-sm text-gray-600">
          <span>
            {answeredCount} of {totalQuestions} questions answered
          </span>
          <span className="font-medium">{progressPercent}%</span>
        </div>
        <Progress value={progressPercent} className="h-2" />
      </div>

      {/* Facet groups */}
      {currentGroups.map((group) => (
        <Card key={group.facet} className="mb-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-legacy-navy capitalize">
              {group.facet.replace(/_/g, ' ')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {group.questions.map((q) => (
              <QuestionRenderer
                key={q.questionId}
                question={q}
                value={responses.get(q.questionId)}
                onChange={handleAnswer}
              />
            ))}
          </CardContent>
        </Card>
      ))}

      {/* Navigation */}
      <div className="flex justify-between gap-4 mt-4">
        <Button
          variant="outline"
          onClick={handlePrevPage}
          disabled={currentPage === 0}
          className="flex-1"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Previous
        </Button>

        {isLastPage ? (
          <>
            {answeredCount < totalQuestions && (
              <p className="text-xs text-amber-600 text-center w-full mb-2">
                {totalQuestions - answeredCount} question{totalQuestions - answeredCount !== 1 ? 's' : ''} unanswered — go back to complete them before submitting.
              </p>
            )}
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting || answeredCount < totalQuestions}
              className="flex-1 bg-legacy-purple hover:bg-legacy-navy"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Scoring…
                </>
              ) : (
                `Submit (${answeredCount}/${totalQuestions})`
              )}
            </Button>
          </>
        ) : (
          <Button
            onClick={handleNextPage}
            className="flex-1 bg-legacy-purple hover:bg-legacy-navy"
          >
            Next
            <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
        )}
      </div>

      {/* Disclaimer */}
      {testDefinition.disclaimerText && (
        <p className="text-xs text-gray-400 mt-6 text-center">
          {testDefinition.disclaimerText}
        </p>
      )}
    </div>
  );
};

export default TestTakingUI;
