/**
 * Displays inline validation warnings for question tagging issues.
 * Warnings are advisory — they don't block saving.
 */
import { AlertTriangle } from "lucide-react";
import {
  ALL_LIFE_EVENT_KEYS,
  INSTANCEABLE_KEY_TO_PLACEHOLDER,
} from "@/constants/lifeEventRegistry";

interface QuestionData {
  questionText: string;
  requiredLifeEvents: string[];
  isInstanceable: boolean;
  instancePlaceholder: string;
  questionType: string;
}

interface QuestionValidationWarningsProps {
  question: QuestionData;
  existingTypes?: string[];
  /** Existing question texts for duplicate detection (optional) */
  existingTexts?: { questionId: string; text: string }[];
  /** Current questionId to exclude from duplicate check */
  currentQuestionId?: string;
}

function getWarnings(
  q: QuestionData,
  existingTypes: string[],
  existingTexts: { questionId: string; text: string }[],
  currentQuestionId?: string
): string[] {
  const warnings: string[] = [];

  // Instanceable without placeholder in text
  if (q.isInstanceable && q.instancePlaceholder && q.questionText) {
    if (!q.questionText.includes(q.instancePlaceholder)) {
      warnings.push(
        `This question is marked as instanceable but the question text does not contain the placeholder token "${q.instancePlaceholder}".`
      );
    }
  }

  // Instanceable without matching life event key
  if (q.isInstanceable) {
    const expectedKeys = Object.keys(INSTANCEABLE_KEY_TO_PLACEHOLDER).filter(
      (k) => INSTANCEABLE_KEY_TO_PLACEHOLDER[k] === q.instancePlaceholder
    );
    const hasMatch = expectedKeys.some((k) =>
      q.requiredLifeEvents.includes(k)
    );
    if (!hasMatch && expectedKeys.length > 0) {
      warnings.push(
        `Instanceable questions should include the matching life event key in requiredLifeEvents (expected one of: ${expectedKeys.join(", ")}).`
      );
    }
  }

  // Placeholder set but not instanceable
  if (!q.isInstanceable && q.instancePlaceholder) {
    warnings.push(
      "This question has a placeholder set but is not marked as instanceable."
    );
  }

  // Instanceable but no placeholder
  if (q.isInstanceable && !q.instancePlaceholder) {
    warnings.push(
      "This question is marked as instanceable but has no placeholder selected."
    );
  }

  // Unrecognized life event keys
  const invalid = q.requiredLifeEvents.filter(
    (k) => !ALL_LIFE_EVENT_KEYS.includes(k)
  );
  if (invalid.length > 0) {
    warnings.push(`Unrecognized life event key(s): ${invalid.join(", ")}`);
  }

  // Case-sensitive questionType mismatch
  if (q.questionType && existingTypes.length > 0) {
    const match = existingTypes.find(
      (t) =>
        t.toLowerCase() === q.questionType.toLowerCase() &&
        t !== q.questionType
    );
    if (match) {
      warnings.push(
        `A similar question type "${match}" already exists. Question types are case-sensitive — please verify this is intentional.`
      );
    }
  }

  // Duplicate question text
  if (q.questionText && existingTexts.length > 0) {
    const dupes = existingTexts.filter(
      (e) =>
        e.text === q.questionText &&
        e.questionId !== currentQuestionId
    );
    if (dupes.length > 0) {
      warnings.push(
        `Duplicate question text found in: ${dupes.map((d) => d.questionId).join(", ")}`
      );
    }
  }

  return warnings;
}

const QuestionValidationWarnings: React.FC<QuestionValidationWarningsProps> = ({
  question,
  existingTypes = [],
  existingTexts = [],
  currentQuestionId,
}) => {
  const warnings = getWarnings(
    question,
    existingTypes,
    existingTexts,
    currentQuestionId
  );

  if (warnings.length === 0) return null;

  return (
    <div className="space-y-1.5 mt-2">
      {warnings.map((w, i) => (
        <div
          key={i}
          className="flex items-start gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2"
        >
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{w}</span>
        </div>
      ))}
    </div>
  );
};

export default QuestionValidationWarnings;
export { getWarnings };
