import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { toast } from "@/components/ui/sonner";
import { toastError } from "@/utils/toastError";
import LifeEventTagEditor from "@/components/admin/LifeEventTagEditor";
import { fetchQuestions, applyThemeDefaults, type QuestionRecord } from "@/services/adminService";
import { VALID_PLACEHOLDERS } from "@/constants/lifeEventRegistry";

interface ThemeInfo {
  questionType: string;
  count: number;
  currentTags: string[];
  currentInstanceable: boolean;
  currentPlaceholder: string;
  currentPromptDescription: string;
}

const ThemeSettings = () => {
  const [themes, setThemes] = useState<ThemeInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingTheme, setEditingTheme] = useState<string | null>(null);
  const [editTags, setEditTags] = useState<string[]>([]);
  const [editInstanceable, setEditInstanceable] = useState(false);
  const [editPlaceholder, setEditPlaceholder] = useState("");
  const [editPromptDescription, setEditPromptDescription] = useState("");
  const [applying, setApplying] = useState(false);

  const loadThemes = async () => {
    try {
      setLoading(true);
      const questions = await fetchQuestions();
      const map = new Map<string, QuestionRecord[]>();
      for (const q of questions) {
        const list = map.get(q.questionType) || [];
        list.push(q);
        map.set(q.questionType, list);
      }
      const result: ThemeInfo[] = [];
      for (const [qtype, qs] of map.entries()) {
        const first = qs[0];
        result.push({
          questionType: qtype,
          count: qs.length,
          currentTags: first.requiredLifeEvents || [],
          currentInstanceable: first.isInstanceable || false,
          currentPlaceholder: first.instancePlaceholder || "",
          currentPromptDescription: first.promptDescription || "",
        });
      }
      setThemes(result.sort((a, b) => a.questionType.localeCompare(b.questionType)));
    } catch (err: unknown) {
      toastError(err instanceof Error ? err.message : "Failed to load themes", 'ThemeSettings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadThemes(); }, []);

  const startEdit = (t: ThemeInfo) => {
    setEditingTheme(t.questionType);
    setEditTags([...t.currentTags]);
    setEditInstanceable(t.currentInstanceable);
    setEditPlaceholder(t.currentPlaceholder);
    setEditPromptDescription(t.currentPromptDescription);
  };

  const handleApply = async () => {
    if (!editingTheme) return;
    const theme = themes.find((t) => t.questionType === editingTheme);
    if (!confirm(`Apply these settings to all ${theme?.count || 0} questions in "${editingTheme}"?`)) return;

    try {
      setApplying(true);
      const result = await applyThemeDefaults(editingTheme, {
        requiredLifeEvents: editTags,
        isInstanceable: editInstanceable,
        instancePlaceholder: editInstanceable ? editPlaceholder : "",
        promptDescription: editPromptDescription,
      });
      toast.success(`Updated ${result.questionsUpdated} questions`);
      setEditingTheme(null);
      loadThemes();
    } catch (err: unknown) {
      toastError(err instanceof Error ? err.message : "Failed to apply", 'ThemeSettings');
    } finally {
      setApplying(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-legacy-purple" />
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-legacy-navy mb-6">Theme Settings</h1>

      <div className="space-y-3">
        {themes.map((t) => (
          <div key={t.questionType} className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between mb-2">
              <div>
                <span className="font-medium text-gray-900">{t.questionType}</span>
                <span className="text-sm text-gray-500 ml-2">({t.count} questions)</span>
              </div>
              <Button variant="outline" size="sm" onClick={() => startEdit(t)}>
                Edit Tags
              </Button>
            </div>
            <div className="text-xs text-gray-500">
              Tags: {t.currentTags.length > 0 ? t.currentTags.join(", ") : "none"}
              {t.currentInstanceable && ` | Instanceable: ${t.currentPlaceholder}`}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Prompt: {t.currentPromptDescription
                ? (t.currentPromptDescription.length > 100
                    ? t.currentPromptDescription.slice(0, 100) + "..."
                    : t.currentPromptDescription)
                : "No prompt description"}
            </div>

            {editingTheme === t.questionType && (
              <div className="mt-4 pt-4 border-t space-y-4">
                <LifeEventTagEditor value={editTags} onChange={setEditTags} />
                <div className="flex items-center gap-3">
                  <Switch checked={editInstanceable} onCheckedChange={setEditInstanceable} />
                  <label
                    className="text-sm cursor-help"
                    title="When enabled, this question gets repeated for each named person (e.g., each spouse or child). The question text must include a placeholder like {spouse_name} that gets replaced with the person's name. Most questions don't need this — only use it for questions specifically about a named individual."
                  >
                    Instanceable ⓘ
                  </label>
                </div>
                {editInstanceable && (
                  <select
                    value={editPlaceholder}
                    onChange={(e) => setEditPlaceholder(e.target.value)}
                    className="border rounded-md px-3 py-2 text-sm bg-white"
                  >
                    <option value="">Select placeholder...</option>
                    {VALID_PLACEHOLDERS.map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                )}
                <div>
                  <textarea
                    aria-label="Prompt description"
                    placeholder="Describe the theme context for the AI interviewer..."
                    value={editPromptDescription}
                    onChange={(e) => setEditPromptDescription(e.target.value)}
                    className="w-full border rounded-md px-3 py-2 text-sm"
                    rows={3}
                  />
                  <div className={`text-xs mt-1 ${editPromptDescription.length > 1000 ? "text-red-600" : "text-gray-500"}`}>
                    {editPromptDescription.length}/1000
                  </div>
                  {editPromptDescription.length > 1000 && (
                    <div className="text-xs text-red-600 mt-1">Prompt description must be 1000 characters or fewer</div>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={handleApply}
                    disabled={applying || editPromptDescription.length > 1000}
                    className="bg-legacy-purple hover:bg-legacy-navy"
                  >
                    {applying ? "Applying..." : `Apply to ${t.count} Questions`}
                  </Button>
                  <Button variant="outline" onClick={() => setEditingTheme(null)}>Cancel</Button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ThemeSettings;
