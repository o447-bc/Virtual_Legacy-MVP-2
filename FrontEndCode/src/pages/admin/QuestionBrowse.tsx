import { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { toast } from "@/components/ui/sonner";
import { fetchQuestions, updateQuestion, type QuestionRecord } from "@/services/adminService";
import { Search, ChevronUp, ChevronDown, X } from "lucide-react";
import LifeEventTagEditor from "@/components/admin/LifeEventTagEditor";
import QuestionValidationWarnings from "@/components/admin/QuestionValidationWarnings";
import { VALID_PLACEHOLDERS } from "@/constants/lifeEventRegistry";

type SortField = "questionType" | "difficulty" | "active" | "lastModifiedAt";
type SortDir = "asc" | "desc";

const QuestionBrowse = () => {
  const [searchParams] = useSearchParams();
  const [questions, setQuestions] = useState<QuestionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState(searchParams.get("questionType") || "");
  const [filterDifficulty, setFilterDifficulty] = useState(searchParams.get("difficulty") || "");
  const [filterValid, setFilterValid] = useState<"all" | "valid" | "invalid">("all");
  const [filterTagged, setFilterTagged] = useState<"all" | "tagged" | "untagged">("all");
  const [sortField, setSortField] = useState<SortField>("questionType");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [page, setPage] = useState(0);
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionRecord | null>(null);
  const [editData, setEditData] = useState<Partial<QuestionRecord>>({});
  const [saving, setSaving] = useState(false);
  const pageSize = 25;

  useEffect(() => {
    loadQuestions();
  }, []);

  const loadQuestions = async () => {
    try {
      setLoading(true);
      const data = await fetchQuestions();
      setQuestions(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load questions";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  // Distinct question types for filter dropdown
  const questionTypes = useMemo(
    () => [...new Set(questions.map((q) => q.questionType))].sort(),
    [questions]
  );

  // Map questionType -> themeName for friendly display
  const typeToTheme = useMemo(() => {
    const map: Record<string, string> = {};
    for (const q of questions) {
      if (q.questionType && q.themeName && !map[q.questionType]) {
        map[q.questionType] = q.themeName;
      }
    }
    return map;
  }, [questions]);

  // Filter + sort
  const filtered = useMemo(() => {
    let result = [...questions];

    if (search) {
      const lower = search.toLowerCase();
      result = result.filter((q) => q.Question.toLowerCase().includes(lower));
    }
    if (filterType) {
      result = result.filter((q) => q.questionType === filterType);
    }
    if (filterDifficulty) {
      result = result.filter((q) => q.difficulty === Number(filterDifficulty));
    }
    if (filterValid === "valid") result = result.filter((q) => q.active === true);
    if (filterValid === "invalid") result = result.filter((q) => q.active !== true);
    if (filterTagged === "tagged")
      result = result.filter((q) => q.requiredLifeEvents?.length > 0);
    if (filterTagged === "untagged")
      result = result.filter((q) => !q.requiredLifeEvents?.length);

    result.sort((a, b) => {
      const aVal = a[sortField] ?? "";
      const bVal = b[sortField] ?? "";
      if (aVal < bVal) return sortDir === "asc" ? -1 : 1;
      if (aVal > bVal) return sortDir === "asc" ? 1 : -1;
      return 0;
    });

    return result;
  }, [questions, search, filterType, filterDifficulty, filterValid, filterTagged, sortField, sortDir]);

  const paged = filtered.slice(page * pageSize, (page + 1) * pageSize);
  const totalPages = Math.ceil(filtered.length / pageSize);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  const SortIcon = ({ field }: { field: SortField }) =>
    sortField === field ? (
      sortDir === "asc" ? <ChevronUp className="h-3 w-3 inline ml-1" /> : <ChevronDown className="h-3 w-3 inline ml-1" />
    ) : null;

  const existingTypes = useMemo(
    () => [...new Set(questions.map((q) => q.questionType))],
    [questions]
  );

  const openEdit = (q: QuestionRecord) => {
    setSelectedQuestion(q);
    setEditData({ ...q });
  };

  const closeEdit = () => {
    setSelectedQuestion(null);
    setEditData({});
  };

  const handleSave = async () => {
    if (!selectedQuestion) return;
    try {
      setSaving(true);
      await updateQuestion(selectedQuestion.questionId, editData);
      toast.success("Question updated");
      closeEdit();
      loadQuestions();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Update failed";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleValid = async (q: QuestionRecord) => {
    try {
      await updateQuestion(q.questionId, { active: !q.active } as Partial<QuestionRecord>);
      toast.success(q.active ? "Marked as invalid" : "Marked as valid");
      loadQuestions();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Update failed";
      toast.error(msg);
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
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-legacy-navy">Questions</h1>
        <span className="text-sm text-gray-500">{filtered.length} questions</span>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search question text..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            className="pl-9"
          />
        </div>

        <select
          value={filterType}
          onChange={(e) => { setFilterType(e.target.value); setPage(0); }}
          className="border rounded-md px-3 py-2 text-sm bg-white"
        >
          <option value="">All Types</option>
          {questionTypes.map((t) => (
            <option key={t} value={t}>{typeToTheme[t] || t}</option>
          ))}
        </select>

        <select
          value={filterDifficulty}
          onChange={(e) => { setFilterDifficulty(e.target.value); setPage(0); }}
          className="border rounded-md px-3 py-2 text-sm bg-white"
        >
          <option value="">All Levels</option>
          {Array.from({ length: 10 }, (_, i) => (
            <option key={i + 1} value={i + 1}>Level {i + 1}</option>
          ))}
        </select>

        <select
          value={filterValid}
          onChange={(e) => { setFilterValid(e.target.value as typeof filterValid); setPage(0); }}
          className="border rounded-md px-3 py-2 text-sm bg-white"
        >
          <option value="all">All Status</option>
          <option value="valid">Valid Only</option>
          <option value="invalid">Invalid Only</option>
        </select>

        <select
          value={filterTagged}
          onChange={(e) => { setFilterTagged(e.target.value as typeof filterTagged); setPage(0); }}
          className="border rounded-md px-3 py-2 text-sm bg-white"
        >
          <option value="all">All Tags</option>
          <option value="tagged">Has Life Events</option>
          <option value="untagged">No Life Events</option>
        </select>
      </div>

      {/* Table */}
      <div className="overflow-x-auto bg-white rounded-lg shadow">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b">
              <th className="px-3 py-2 text-left font-medium text-gray-600">ID</th>
              <th
                className="px-3 py-2 text-left font-medium text-gray-600 cursor-pointer hover:text-legacy-purple"
                onClick={() => toggleSort("questionType")}
              >
                Type <SortIcon field="questionType" />
              </th>
              <th
                className="px-3 py-2 text-center font-medium text-gray-600 cursor-pointer hover:text-legacy-purple"
                onClick={() => toggleSort("difficulty")}
              >
                Level <SortIcon field="difficulty" />
              </th>
              <th
                className="px-3 py-2 text-center font-medium text-gray-600 cursor-pointer hover:text-legacy-purple"
                onClick={() => toggleSort("active")}
              >
                Valid <SortIcon field="active" />
              </th>
              <th className="px-3 py-2 text-left font-medium text-gray-600">Question</th>
              <th className="px-3 py-2 text-center font-medium text-gray-600">Tags</th>
            </tr>
          </thead>
          <tbody>
            {paged.map((q, idx) => (
              <tr
                key={q.questionId}
                className={`border-b hover:bg-gray-50 cursor-pointer ${idx % 2 === 0 ? "" : "bg-gray-50/50"}`}
                onClick={() => openEdit(q)}
              >
                <td className="px-3 py-2 text-xs text-gray-500 font-mono">{q.questionId}</td>
                <td className="px-3 py-2">{typeToTheme[q.questionType] || q.questionType}</td>
                <td className="px-3 py-2 text-center">{q.difficulty}</td>
                <td className="px-3 py-2 text-center">
                  {q.active ? (
                    <Badge className="bg-green-100 text-green-700 hover:bg-green-100">Valid</Badge>
                  ) : (
                    <Badge className="bg-red-100 text-red-700 hover:bg-red-100">Invalid</Badge>
                  )}
                </td>
                <td className="px-3 py-2 max-w-md truncate">{q.questionText}</td>
                <td className="px-3 py-2 text-center">
                  {q.requiredLifeEvents?.length > 0 ? (
                    <Badge className="bg-purple-100 text-purple-700 hover:bg-purple-100">
                      {q.requiredLifeEvents.length}
                    </Badge>
                  ) : (
                    <span className="text-gray-300">—</span>
                  )}
                </td>
              </tr>
            ))}
            {paged.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-gray-400">
                  No questions match your filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500">
            Page {page + 1} of {totalPages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Edit Panel (slide-over) */}
      {selectedQuestion && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/30" onClick={closeEdit} />
          <div className="relative w-full max-w-lg bg-white shadow-xl overflow-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between z-10">
              <h2 className="text-lg font-bold text-legacy-navy">Edit Question</h2>
              <button onClick={closeEdit} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 space-y-5">
              {/* Read-only ID */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Question ID</label>
                <p className="text-sm font-mono text-gray-700">{selectedQuestion.questionId}</p>
              </div>

              {/* Question Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Question Type</label>
                <Input
                  value={editData.questionType || ""}
                  onChange={(e) => setEditData({ ...editData, questionType: e.target.value })}
                />
              </div>

              {/* Theme Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Theme Name</label>
                <Input
                  value={editData.themeName || ""}
                  onChange={(e) => setEditData({ ...editData, themeName: e.target.value })}
                />
              </div>

              {/* Difficulty */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Difficulty (1–10)</label>
                <Input
                  type="number"
                  min={1}
                  max={10}
                  value={editData.difficulty || 1}
                  onChange={(e) => setEditData({ ...editData, difficulty: Number(e.target.value) })}
                />
              </div>

              {/* Active toggle */}
              <div className="flex items-center gap-3">
                <Switch
                  checked={editData.active ?? true}
                  onCheckedChange={(v) => setEditData({ ...editData, active: v })}
                />
                <label className="text-sm font-medium text-gray-700">
                  {editData.active ? "Valid (active)" : "Invalid (inactive)"}
                </label>
              </div>

              {/* Question Text */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Question Text</label>
                <Textarea
                  value={editData.questionText || ""}
                  onChange={(e) => setEditData({ ...editData, questionText: e.target.value })}
                  rows={4}
                />
              </div>

              {/* Life Event Tags */}
              <LifeEventTagEditor
                value={editData.requiredLifeEvents || []}
                onChange={(keys) => setEditData({ ...editData, requiredLifeEvents: keys })}
              />

              {/* Instanceable */}
              <div className="flex items-center gap-3">
                <Switch
                  checked={editData.isInstanceable ?? false}
                  onCheckedChange={(v) => setEditData({ ...editData, isInstanceable: v })}
                />
                <label
                  className="text-sm font-medium text-gray-700 cursor-help"
                  title="When enabled, this question gets repeated for each named person (e.g., each spouse or child). The question text must include a placeholder like {spouse_name} that gets replaced with the person's name. Most questions don't need this — only use it for questions specifically about a named individual."
                >
                  Instanceable ⓘ
                </label>
              </div>

              {editData.isInstanceable && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Placeholder</label>
                  <select
                    value={editData.instancePlaceholder || ""}
                    onChange={(e) => setEditData({ ...editData, instancePlaceholder: e.target.value })}
                    className="border rounded-md px-3 py-2 text-sm bg-white w-full"
                  >
                    <option value="">Select...</option>
                    {VALID_PLACEHOLDERS.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    Use this placeholder in the question text. Example: "What made you decide to marry {'{spouse_name}'}?"
                  </p>
                </div>
              )}

              {/* Validation Warnings */}
              <QuestionValidationWarnings
                question={{
                  questionText: editData.questionText || "",
                  requiredLifeEvents: editData.requiredLifeEvents || [],
                  isInstanceable: editData.isInstanceable ?? false,
                  instancePlaceholder: editData.instancePlaceholder || "",
                  questionType: editData.questionType || "",
                }}
                existingTypes={existingTypes}
                currentQuestionId={selectedQuestion.questionId}
              />

              {/* Audit info */}
              {selectedQuestion.lastModifiedBy && (
                <div className="text-xs text-gray-400 pt-2 border-t">
                  Last modified by {selectedQuestion.lastModifiedBy} on{" "}
                  {selectedQuestion.lastModifiedAt ? new Date(selectedQuestion.lastModifiedAt).toLocaleString() : "—"}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                <Button
                  onClick={handleSave}
                  disabled={saving}
                  className="bg-legacy-purple hover:bg-legacy-navy"
                >
                  {saving ? "Saving..." : "Save Changes"}
                </Button>
                <Button variant="outline" onClick={closeEdit}>
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuestionBrowse;
