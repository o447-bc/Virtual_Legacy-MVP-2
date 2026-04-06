import React, { useState, useMemo } from "react";
import { CheckCircle2, Circle, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { LIFE_EVENT_REGISTRY } from "@/constants/lifeEventRegistry";
import { cn } from "@/lib/utils";

interface LifeEventGroupProps {
  eventKey: string;
  instanceName: string;
  instanceOrdinal: number;
  questions: Array<{
    questionId: string;
    questionText: string;
    isAnswered: boolean;
  }>;
  totalQuestions: number;
  completedQuestions: number;
  onRecord: (questionIds: string[], questionTexts: string[]) => void;
}

/** Map life-event categories to left-border accent colours. */
const CATEGORY_ACCENT: Record<string, string> = {
  "Core Relationship & Family": "border-rose-500",
  "Education & Early Life": "border-sky-500",
  "Career & Professional": "border-indigo-500",
  "Health & Resilience": "border-emerald-500",
  "Relocation & Transitions": "border-amber-500",
  "Spiritual, Creative & Legacy": "border-violet-500",
  Other: "border-gray-500",
  "Status-derived": "border-slate-400",
};


/**
 * LIFE EVENT GROUP
 *
 * Displays a single life-event instance group on the Life Events page.
 * Shows event label + instance name, per-group progress bar, an expandable
 * question list with answered/unanswered icons, and a "Record" button that
 * passes unanswered questions to the recording flow.
 *
 * When all questions are answered the card switches to a muted completed state.
 */
export const LifeEventGroup: React.FC<LifeEventGroupProps> = ({
  eventKey,
  instanceName,
  instanceOrdinal: _instanceOrdinal,
  questions,
  totalQuestions,
  completedQuestions,
  onRecord,
}) => {
  const [open, setOpen] = useState(false);

  const isComplete = completedQuestions >= totalQuestions && totalQuestions > 0;

  const registryEntry = useMemo(
    () => LIFE_EVENT_REGISTRY.find((e) => e.key === eventKey),
    [eventKey]
  );
  const eventLabel = registryEntry?.label ?? eventKey;
  const category = registryEntry?.category ?? "Other";
  const accentClass = CATEGORY_ACCENT[category] ?? "border-gray-500";

  const progressPercent =
    totalQuestions > 0 ? (completedQuestions / totalQuestions) * 100 : 0;

  const unanswered = useMemo(
    () => questions.filter((q) => !q.isAnswered),
    [questions]
  );

  const handleRecord = () => {
    if (unanswered.length === 0) return;
    onRecord(
      unanswered.map((q) => q.questionId),
      unanswered.map((q) => q.questionText)
    );
  };

  return (
    <div
      className={cn(
        "bg-white rounded-xl border-l-4 p-5 shadow-sm transition-opacity",
        accentClass,
        isComplete && "opacity-60"
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h4 className="text-lg font-semibold text-legacy-navy truncate">
            {eventLabel}
            {instanceName && (
              <span className="font-normal text-gray-500">
                {" — "}
                {instanceName}
              </span>
            )}
          </h4>

          {/* Progress text + bar */}
          <div className="mt-2 flex items-center gap-3">
            <span className="text-sm text-gray-600 whitespace-nowrap">
              {completedQuestions} / {totalQuestions}
            </span>
            <Progress
              value={progressPercent}
              className="h-2 flex-1 max-w-[180px]"
            />
            {isComplete && (
              <span className="text-xs font-medium text-emerald-600">
                Complete
              </span>
            )}
          </div>
        </div>

        {!isComplete && (
          <Button size="sm" onClick={handleRecord} className="flex-shrink-0">
            Record
          </Button>
        )}
      </div>

      {/* Expandable question list */}
      <Collapsible open={open} onOpenChange={setOpen} className="mt-3">
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            {open ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
            {open ? "Hide questions" : "Show questions"}
          </button>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <ul className="mt-2 space-y-1.5">
            {questions.map((q) => (
              <li key={q.questionId} className="flex items-start gap-2 text-sm">
                {q.isAnswered ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                ) : (
                  <Circle className="w-4 h-4 text-gray-300 mt-0.5 flex-shrink-0" />
                )}
                <span
                  className={cn(
                    q.isAnswered && "text-gray-400 line-through"
                  )}
                >
                  {q.questionText}
                </span>
              </li>
            ))}
          </ul>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
};
