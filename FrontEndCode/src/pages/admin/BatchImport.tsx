import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/sonner";
import LifeEventTagEditor from "@/components/admin/LifeEventTagEditor";
import { batchImport, fetchQuestions, type QuestionRecord } from "@/services/adminService";
import { VALID_PLACEHOLDERS } from "@/constants/lifeEventRegistry";
import { Trash2 } from "lucide-react";

const BatchImport = () => {
  const [rawInput, setRawInput] = useState("");
  const [questionType, setQuestionType] = useState("");
  const [themeName, setThemeName] = useState("");
  const [difficulty, setDifficulty] = useState(1);
  const [requiredLifeEvents, setRequiredLifeEvents] = useState<string[]>([]);
  const [isInstanceable, setIsInstanceable] = useState(false);
  const [instancePlaceholder, setInstancePlaceholder] = useState("");
  const [parsed, setParsed] = useState<string[]>([]);
  const [previewing, setPreviewing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [existingTexts, setExistingTexts] = useState<Set<string>>(new Set());
  const [existingTypes, setExistingTypes] = useState<string[]>([]);

  useEffect(() => {
    fetchQuestions().then((qs) => {
      setExistingTexts(new Set(qs.map((q) => q.questionText)));
      setExistingTypes([...new Set(qs.map((q) => q.questionType))]);
    }).catch(() => {});
  }, []);

  const handlePreview = () => {
    const text = rawInput.trim();
    if (!text) { toast.error("Paste some questions first"); return; }

    let questions: string[];
    try {
      const jsonParsed = JSON.parse(text);
      if (Array.isArray(jsonParsed)) {
        questions = jsonParsed.map((item: string | { question: string }) =>
          typeof item === "string" ? item : item.question || ""
        );
      } else {
        toast.error("JSON must be an array"); return;
      }
    } catch {
      questions = text.split("\n").filter((line) => line.trim() !== "");
    }

    questions = questions.map((q) => q.trim()).filter(Boolean);
    if (questions.length === 0) { toast.error("No questions found"); return; }

    setParsed(questions);
    setPreviewing(true);
  };

  const removeFromBatch = (index: number) => {
    setParsed((prev) => prev.filter((_, i) => i !== index));
  };

  const handleImport = async () => {
    if (!questionType.trim()) { toast.error("Question type is required"); return; }
    if (parsed.length === 0) { toast.error("No questions to import"); return; }

    try {
      setImporting(true);
      const result = await batchImport({
        questionType,
        Difficulty: difficulty,
        requiredLifeEvents,
        isInstanceable,
        instancePlaceholder: isInstanceable ? instancePlaceholder : "",
        questions: parsed,
      });
      toast.success(`Imported ${result.imported} questions`);
      setRawInput("");
      setParsed([]);
      setPreviewing(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Import failed";
      toast.error(msg);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="p-6 max-w-3xl">
      <h1 className="text-2xl font-bold text-legacy-navy mb-6">Batch Import</h1>

      {/* Help section */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-sm text-blue-800">
        <p className="font-medium mb-2">How batch import works</p>
        <ul className="space-y-1 list-disc list-inside text-blue-700">
          <li>Paste AI-generated questions into the text box — one question per line, or a JSON array</li>
          <li>Set the shared question type, difficulty, and life event tags — these apply to all questions in the batch</li>
          <li>Click Preview to see a table of parsed questions before importing</li>
          <li>Questions flagged as "Duplicate" already exist in the database — you can still import them or remove them from the batch</li>
          <li>Click Import to write all questions to the database with auto-generated IDs</li>
          <li>If any question fails validation, the entire batch is rejected — fix the issue and retry</li>
          <li>For instanceable questions, use placeholders in the text: <code className="bg-blue-100 px-1 rounded">{'{spouse_name}'}</code> for spouse questions, <code className="bg-blue-100 px-1 rounded">{'{child_name}'}</code> for children, <code className="bg-blue-100 px-1 rounded">{'{deceased_name}'}</code> for loss questions. Example: "What made you decide to marry {'{spouse_name}'}?"</li>
        </ul>
      </div>

      <div className="space-y-5">
        {/* Shared settings */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Question Type</label>
            <Input
              value={questionType}
              onChange={(e) => setQuestionType(e.target.value)}
              placeholder="e.g., divorce, career"
              list="batch-types"
            />
            <datalist id="batch-types">
              {existingTypes.map((t) => <option key={t} value={t} />)}
            </datalist>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Theme Name</label>
            <Input
              value={themeName}
              onChange={(e) => setThemeName(e.target.value)}
              placeholder="Display name"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Difficulty (1–10)</label>
          <Input
            type="number"
            min={1}
            max={10}
            value={difficulty}
            onChange={(e) => setDifficulty(Number(e.target.value))}
            className="w-24"
          />
        </div>

        <LifeEventTagEditor value={requiredLifeEvents} onChange={setRequiredLifeEvents} />

        <div className="flex items-center gap-3">
          <Switch checked={isInstanceable} onCheckedChange={setIsInstanceable} />
          <label
            className="text-sm font-medium text-gray-700 cursor-help"
            title="When enabled, this question gets repeated for each named person (e.g., each spouse or child). The question text must include a placeholder like {spouse_name} that gets replaced with the person's name. Most questions don't need this — only use it for questions specifically about a named individual."
          >
            Instanceable ⓘ
          </label>
        </div>

        {isInstanceable && (
          <select
            value={instancePlaceholder}
            onChange={(e) => setInstancePlaceholder(e.target.value)}
            className="border rounded-md px-3 py-2 text-sm bg-white"
          >
            <option value="">Select placeholder...</option>
            {VALID_PLACEHOLDERS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        )}

        {/* Paste area */}
        {!previewing && (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Paste questions (one per line, or JSON array)
              </label>
              <Textarea
                value={rawInput}
                onChange={(e) => setRawInput(e.target.value)}
                rows={10}
                placeholder={"What was your first day at work like?\nWho was your first boss?\nWhat did you learn from your first job?"}
              />
            </div>
            <Button onClick={handlePreview} disabled={!rawInput.trim()}>
              Preview
            </Button>
          </>
        )}

        {/* Preview table */}
        {previewing && (
          <>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">
                {parsed.length} questions to import
              </span>
              <Button variant="outline" size="sm" onClick={() => setPreviewing(false)}>
                Back to edit
              </Button>
            </div>

            <div className="bg-white rounded-lg shadow overflow-auto max-h-96">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b">
                    <th className="px-3 py-2 text-left w-8">#</th>
                    <th className="px-3 py-2 text-left">Question</th>
                    <th className="px-3 py-2 text-center w-20">Status</th>
                    <th className="px-3 py-2 w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {parsed.map((q, i) => {
                    const isDupe = existingTexts.has(q);
                    return (
                      <tr key={i} className={`border-b ${isDupe ? "bg-amber-50" : ""}`}>
                        <td className="px-3 py-2 text-gray-400">{i + 1}</td>
                        <td className="px-3 py-2">{q}</td>
                        <td className="px-3 py-2 text-center">
                          {isDupe ? (
                            <Badge className="bg-amber-100 text-amber-700">Duplicate</Badge>
                          ) : (
                            <Badge className="bg-green-100 text-green-700">New</Badge>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <button
                            onClick={() => removeFromBatch(i)}
                            className="text-gray-400 hover:text-red-500"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <Button
              onClick={handleImport}
              disabled={importing || parsed.length === 0 || !questionType.trim()}
              className="bg-legacy-purple hover:bg-legacy-navy"
            >
              {importing ? "Importing..." : `Import ${parsed.length} Questions`}
            </Button>
          </>
        )}
      </div>
    </div>
  );
};

export default BatchImport;
