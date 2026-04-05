import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { toast } from "@/components/ui/sonner";
import LifeEventTagEditor from "@/components/admin/LifeEventTagEditor";
import QuestionValidationWarnings from "@/components/admin/QuestionValidationWarnings";
import { createQuestion, fetchQuestions, type QuestionRecord } from "@/services/adminService";
import { VALID_PLACEHOLDERS } from "@/constants/lifeEventRegistry";

const QuestionCreate = () => {
  const navigate = useNavigate();
  const [questionType, setQuestionType] = useState("");
  const [themeName, setThemeName] = useState("");
  const [difficulty, setDifficulty] = useState(1);
  const [questionText, setQuestionText] = useState("");
  const [requiredLifeEvents, setRequiredLifeEvents] = useState<string[]>([]);
  const [isInstanceable, setIsInstanceable] = useState(false);
  const [instancePlaceholder, setInstancePlaceholder] = useState("");
  const [saving, setSaving] = useState(false);

  // For validation warnings
  const [existingQuestions, setExistingQuestions] = useState<QuestionRecord[]>([]);
  const [existingTypes, setExistingTypes] = useState<string[]>([]);

  useEffect(() => {
    fetchQuestions().then((qs) => {
      setExistingQuestions(qs);
      setExistingTypes([...new Set(qs.map((q) => q.questionType))]);
    }).catch(() => {});
  }, []);

  const handleSubmit = async () => {
    if (!questionText.trim() || !questionType.trim()) {
      toast.error("Question text and question type are required");
      return;
    }
    try {
      setSaving(true);
      const result = await createQuestion({
        questionType,
        themeName: themeName || questionType,
        difficulty,
        questionText,
        requiredLifeEvents,
        isInstanceable,
        instancePlaceholder: isInstanceable ? instancePlaceholder : "",
      } as Partial<QuestionRecord>);
      toast.success(`Created: ${result.questionId}`);
      navigate("/admin/questions");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create question";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-legacy-navy mb-6">Create Question</h1>

      <div className="space-y-5">
        {/* Question Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Question Type (questionType)
          </label>
          <Input
            value={questionType}
            onChange={(e) => setQuestionType(e.target.value)}
            placeholder="e.g., childhood, divorce, career"
            list="existing-types"
          />
          <datalist id="existing-types">
            {existingTypes.map((t) => (
              <option key={t} value={t} />
            ))}
          </datalist>
        </div>

        {/* Theme Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Theme Name (display label)
          </label>
          <Input
            value={themeName}
            onChange={(e) => setThemeName(e.target.value)}
            placeholder="e.g., Childhood Memories, Divorce"
          />
        </div>

        {/* Difficulty */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Difficulty (1–10)
          </label>
          <Input
            type="number"
            min={1}
            max={10}
            value={difficulty}
            onChange={(e) => setDifficulty(Number(e.target.value))}
          />
        </div>

        {/* Question Text */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Question Text
          </label>
          <Textarea
            value={questionText}
            onChange={(e) => setQuestionText(e.target.value)}
            placeholder="Enter the question text..."
            rows={3}
          />
        </div>

        {/* Life Event Tags */}
        <LifeEventTagEditor
          value={requiredLifeEvents}
          onChange={setRequiredLifeEvents}
        />

        {/* Instanceable */}
        <div className="flex items-center gap-3">
          <Switch
            checked={isInstanceable}
            onCheckedChange={setIsInstanceable}
          />
          <label
            className="text-sm font-medium text-gray-700 cursor-help"
            title="When enabled, this question gets repeated for each named person (e.g., each spouse or child). The question text must include a placeholder like {spouse_name} that gets replaced with the person's name. Most questions don't need this — only use it for questions specifically about a named individual."
          >
            Instanceable (per-person question) ⓘ
          </label>
        </div>

        {isInstanceable && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Instance Placeholder
            </label>
            <select
              value={instancePlaceholder}
              onChange={(e) => setInstancePlaceholder(e.target.value)}
              className="border rounded-md px-3 py-2 text-sm bg-white w-full"
            >
              <option value="">Select placeholder...</option>
              {VALID_PLACEHOLDERS.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Use this placeholder in your question text. Example: "What made you decide to marry {'{spouse_name}'}?" — the app replaces it with the person's actual name.
            </p>
          </div>
        )}

        {/* Validation Warnings */}
        <QuestionValidationWarnings
          question={{
            questionText,
            requiredLifeEvents,
            isInstanceable,
            instancePlaceholder: isInstanceable ? instancePlaceholder : "",
            questionType,
          }}
          existingTypes={existingTypes}
          existingTexts={existingQuestions.map((q) => ({
            questionId: q.questionId,
            text: q.questionText,
          }))}
        />

        {/* Submit */}
        <div className="flex gap-3 pt-2">
          <Button
            onClick={handleSubmit}
            disabled={saving || !questionText.trim() || !questionType.trim()}
            className="bg-legacy-purple hover:bg-legacy-navy"
          >
            {saving ? "Creating..." : "Create Question"}
          </Button>
          <Button variant="outline" onClick={() => navigate("/admin/questions")}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
};

export default QuestionCreate;
