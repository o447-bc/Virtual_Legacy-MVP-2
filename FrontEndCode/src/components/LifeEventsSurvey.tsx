/**
 * LifeEventsSurvey — 7-step floating card overlay for collecting life events.
 * Renders on top of the Dashboard with a dimmed backdrop.
 */
import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/sonner";
import { ChevronLeft, ChevronRight, Loader2, CheckCircle } from "lucide-react";
import {
  LIFE_EVENT_REGISTRY,
  LIFE_EVENT_CATEGORIES,
  type LifeEventKeyInfo,
} from "@/constants/lifeEventRegistry";
import {
  submitSurvey,
  type LifeEventInstanceGroup,
  type LifeEventInstance,
} from "@/services/surveyService";

interface LifeEventsSurveyProps {
  onComplete: (assignedQuestionCount: number) => void;
  initialSelections?: string[];
  initialInstances?: LifeEventInstanceGroup[];
  isRetake?: boolean;
}

// Map categories to step indices
const STEP_CATEGORIES = [
  "Core Relationship & Family",
  "Education & Early Life",
  "Career & Professional",
  "Health & Resilience",
  "Relocation & Transitions",
  "Spiritual, Creative & Legacy",
  "Other",
];

const STEP_TITLES = [
  "Core Relationship & Family Events",
  "Education & Early Life Milestones",
  "Career & Professional Life",
  "Health & Personal Resilience",
  "Relocation & Life Transitions",
  "Spiritual, Creative & Legacy Moments",
  "Other High-Impact Events",
];

// Instanceable events that need follow-up name collection
const INSTANCEABLE_EVENTS = new Set([
  "got_married", "had_children",
  "death_of_child", "death_of_parent", "death_of_sibling", "death_of_friend_mentor",
]);

// Events that need a status dropdown (only got_married)
const STATUS_EVENTS = new Set(["got_married"]);

const MARRIAGE_STATUSES = [
  { value: "married", label: "Still married/together" },
  { value: "divorced", label: "Divorced/separated" },
  { value: "deceased", label: "They passed away" },
];

// Labels for instance name prompts
const INSTANCE_LABELS: Record<string, { singular: string; plural: string }> = {
  got_married: { singular: "spouse's/partner's", plural: "spouse's/partner's" },
  had_children: { singular: "child's", plural: "child's" },
  death_of_child: { singular: "child you lost", plural: "child you lost" },
  death_of_parent: { singular: "parent you lost", plural: "parent you lost" },
  death_of_sibling: { singular: "sibling/family member you lost", plural: "sibling/family member you lost" },
  death_of_friend_mentor: { singular: "friend/mentor you lost", plural: "friend/mentor you lost" },
};

const LifeEventsSurvey: React.FC<LifeEventsSurveyProps> = ({
  onComplete,
  initialSelections = [],
  initialInstances = [],
  isRetake = false,
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedEvents, setSelectedEvents] = useState<Set<string>>(
    new Set(initialSelections)
  );
  const [instanceData, setInstanceData] = useState<Map<string, LifeEventInstanceGroup>>(
    () => {
      const map = new Map<string, LifeEventInstanceGroup>();
      for (const group of initialInstances) {
        map.set(group.eventKey, group);
      }
      return map;
    }
  );
  const [customLifeEvent, setCustomLifeEvent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState<number | null>(null);

  const totalSteps = STEP_TITLES.length;

  // Get events for current step
  const getStepEvents = useCallback(
    (step: number): LifeEventKeyInfo[] => {
      const category = STEP_CATEGORIES[step];
      // Filter out status-derived keys — those are virtual, not shown in survey
      return LIFE_EVENT_REGISTRY.filter(
        (e) => e.category === category && !["Status-derived"].includes(e.category)
      );
    },
    []
  );

  const toggleEvent = (key: string) => {
    setSelectedEvents((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
        // Remove instance data when unchecked
        if (INSTANCEABLE_EVENTS.has(key)) {
          setInstanceData((prev) => {
            const next = new Map(prev);
            next.delete(key);
            return next;
          });
        }
      } else {
        next.add(key);
        // Initialize instance data with 1 empty instance
        if (INSTANCEABLE_EVENTS.has(key)) {
          setInstanceData((prev) => {
            const next = new Map(prev);
            if (!next.has(key)) {
              next.set(key, {
                eventKey: key,
                instances: [{ name: "", ordinal: 1, ...(STATUS_EVENTS.has(key) ? { status: undefined } : {}) }],
              });
            }
            return next;
          });
        }
      }
      return next;
    });
  };

  const setInstanceCount = (eventKey: string, count: number) => {
    setInstanceData((prev) => {
      const next = new Map(prev);
      const existing = next.get(eventKey);
      const instances: LifeEventInstance[] = [];
      for (let i = 0; i < count; i++) {
        const existingInst = existing?.instances[i];
        instances.push({
          name: existingInst?.name || "",
          ordinal: i + 1,
          ...(STATUS_EVENTS.has(eventKey) ? { status: existingInst?.status } : {}),
        });
      }
      next.set(eventKey, { eventKey, instances });
      return next;
    });
  };

  const updateInstanceName = (eventKey: string, ordinal: number, name: string) => {
    setInstanceData((prev) => {
      const next = new Map(prev);
      const group = next.get(eventKey);
      if (group) {
        const updated = group.instances.map((inst) =>
          inst.ordinal === ordinal ? { ...inst, name } : inst
        );
        next.set(eventKey, { ...group, instances: updated });
      }
      return next;
    });
  };

  const updateInstanceStatus = (eventKey: string, ordinal: number, status: string) => {
    setInstanceData((prev) => {
      const next = new Map(prev);
      const group = next.get(eventKey);
      if (group) {
        const updated = group.instances.map((inst) =>
          inst.ordinal === ordinal
            ? { ...inst, status: status as "married" | "divorced" | "deceased" }
            : inst
        );
        next.set(eventKey, { ...group, instances: updated });
      }
      return next;
    });
  };

  // Validate current step before advancing
  const canAdvance = (): boolean => {
    const events = getStepEvents(currentStep);
    for (const event of events) {
      if (!selectedEvents.has(event.key)) continue;
      if (!INSTANCEABLE_EVENTS.has(event.key)) continue;
      const group = instanceData.get(event.key);
      if (!group || group.instances.length === 0) return false;
      for (const inst of group.instances) {
        if (!inst.name.trim()) return false;
        if (STATUS_EVENTS.has(event.key) && !inst.status) return false;
      }
    }
    return true;
  };

  const handleNext = () => {
    if (!canAdvance()) {
      toast.error("Please fill in all names and statuses before continuing");
      return;
    }
    if (currentStep < totalSteps - 1) {
      setCurrentStep((s) => s + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) setCurrentStep((s) => s - 1);
  };

  const handleSubmit = async () => {
    if (!canAdvance()) {
      toast.error("Please fill in all names and statuses before submitting");
      return;
    }

    setIsSubmitting(true);
    try {
      const lifeEventInstances = Array.from(instanceData.values()).filter(
        (g) => selectedEvents.has(g.eventKey)
      );

      const result = await submitSurvey({
        selectedLifeEvents: Array.from(selectedEvents),
        lifeEventInstances: lifeEventInstances.length > 0 ? lifeEventInstances : undefined,
        customLifeEvent: customLifeEvent.trim() || undefined,
      });

      setSubmitSuccess(result.assignedQuestionCount);

      // Brief success display, then dismiss
      setTimeout(() => {
        onComplete(result.assignedQuestionCount);
      }, 2500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Something went wrong. Please try again.";
      toast.error(msg);
      setIsSubmitting(false);
    }
  };

  // Render an instanceable event's follow-up UI
  const renderInstanceFollowUp = (eventKey: string) => {
    const group = instanceData.get(eventKey);
    if (!group) return null;
    const labels = INSTANCE_LABELS[eventKey] || { singular: "person", plural: "person" };
    const ordinals = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"];

    return (
      <div className="ml-6 mt-2 space-y-3 border-l-2 border-legacy-purple/20 pl-4">
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">How many?</label>
          <select
            value={group.instances.length}
            onChange={(e) => setInstanceCount(eventKey, Number(e.target.value))}
            className="border rounded px-2 py-1 text-sm bg-white"
          >
            {Array.from({ length: 10 }, (_, i) => (
              <option key={i + 1} value={i + 1}>{i + 1}</option>
            ))}
          </select>
        </div>

        {group.instances.map((inst, idx) => (
          <div key={inst.ordinal} className="space-y-1">
            <Input
              placeholder={`What was your ${ordinals[idx] || `#${idx + 1}`} ${labels.singular} name?`}
              value={inst.name}
              onChange={(e) => updateInstanceName(eventKey, inst.ordinal, e.target.value)}
              className="text-sm"
            />
            {STATUS_EVENTS.has(eventKey) && (
              <select
                value={inst.status || ""}
                onChange={(e) => updateInstanceStatus(eventKey, inst.ordinal, e.target.value)}
                className="border rounded px-2 py-1 text-sm bg-white w-full"
              >
                <option value="">Select status...</option>
                {MARRIAGE_STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            )}
          </div>
        ))}
      </div>
    );
  };

  // Success state
  if (submitSuccess !== null) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div className="absolute inset-0 bg-black/50" />
        <div className="relative bg-white rounded-2xl shadow-2xl p-8 max-w-md mx-4 text-center animate-in fade-in zoom-in duration-300">
          <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-legacy-navy mb-2">
            Your personalized questions are ready!
          </h2>
          <p className="text-gray-600">
            {submitSuccess} questions have been selected just for you.
          </p>
        </div>
      </div>
    );
  }

  const stepEvents = getStepEvents(currentStep);
  const isLastStep = currentStep === totalSteps - 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" />

      {/* Card */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[85vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b bg-gradient-to-r from-legacy-navy to-legacy-purple text-white">
          <h2 className="text-lg font-bold">
            {isRetake ? "Update Your Life Events" : "Tell Us About Your Life"}
          </h2>
          <div className="flex items-center justify-between mt-1">
            <p className="text-sm text-white/80">{STEP_TITLES[currentStep]}</p>
            <span className="text-sm text-white/80">
              Step {currentStep + 1} of {totalSteps}
            </span>
          </div>
          {/* Progress bar */}
          <div className="mt-2 h-1.5 bg-white/20 rounded-full overflow-hidden">
            <div
              className="h-full bg-white rounded-full transition-all duration-300"
              style={{ width: `${((currentStep + 1) / totalSteps) * 100}%` }}
            />
          </div>
        </div>

        {/* Content — scrollable */}
        <div className="flex-1 overflow-auto px-6 py-4 space-y-3">
          {stepEvents.map((event) => (
            <div key={event.key}>
              <label className="flex items-start gap-3 cursor-pointer hover:bg-gray-50 rounded-lg p-2 -mx-2">
                <input
                  type="checkbox"
                  checked={selectedEvents.has(event.key)}
                  onChange={() => toggleEvent(event.key)}
                  className="mt-1 rounded border-gray-300 text-legacy-purple focus:ring-legacy-purple"
                />
                <div>
                  <span className="text-sm font-medium text-gray-900">
                    {event.label}
                  </span>
                </div>
              </label>

              {/* Instanceable follow-up */}
              {selectedEvents.has(event.key) &&
                INSTANCEABLE_EVENTS.has(event.key) &&
                renderInstanceFollowUp(event.key)}
            </div>
          ))}

          {/* Free-text on last step */}
          {isLastStep && (
            <div className="pt-3 border-t">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Any other event you consider a turning point?
              </label>
              <Textarea
                value={customLifeEvent}
                onChange={(e) => setCustomLifeEvent(e.target.value)}
                placeholder="Describe any other major turning point in your life (optional)..."
                rows={2}
                className="text-sm"
              />
            </div>
          )}
        </div>

        {/* Footer — navigation */}
        <div className="px-6 py-4 border-t bg-gray-50 flex items-center justify-between">
          <Button
            variant="ghost"
            onClick={handleBack}
            disabled={currentStep === 0 || isSubmitting}
            className={currentStep === 0 ? "invisible" : ""}
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            Back
          </Button>

          {isLastStep ? (
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="bg-legacy-purple hover:bg-legacy-navy"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Personalizing your questions...
                </>
              ) : (
                "Submit"
              )}
            </Button>
          ) : (
            <Button
              onClick={handleNext}
              className="bg-legacy-purple hover:bg-legacy-navy"
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default LifeEventsSurvey;
