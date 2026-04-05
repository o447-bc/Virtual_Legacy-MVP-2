import { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/sonner";
import { fetchQuestions, type QuestionRecord } from "@/services/adminService";
import { Search, ChevronUp, ChevronDown } from "lucide-react";

type SortField = "questionType" | "Difficulty" | "Valid" | "lastModifiedAt";
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
      result = result.filter((q) => q.Difficulty === Number(filterDifficulty));
    }
    if (filterValid === "valid") result = result.filter((q) => q.Valid === 1);
    if (filterValid === "invalid") result = result.filter((q) => q.Valid !== 1);
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
            <option key={t} value={t}>{t}</option>
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
                onClick={() => toggleSort("Difficulty")}
              >
                Level <SortIcon field="Difficulty" />
              </th>
              <th
                className="px-3 py-2 text-center font-medium text-gray-600 cursor-pointer hover:text-legacy-purple"
                onClick={() => toggleSort("Valid")}
              >
                Valid <SortIcon field="Valid" />
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
              >
                <td className="px-3 py-2 text-xs text-gray-500 font-mono">{q.questionId}</td>
                <td className="px-3 py-2">{q.questionType}</td>
                <td className="px-3 py-2 text-center">{q.Difficulty}</td>
                <td className="px-3 py-2 text-center">
                  {q.Valid === 1 ? (
                    <Badge className="bg-green-100 text-green-700 hover:bg-green-100">Valid</Badge>
                  ) : (
                    <Badge className="bg-red-100 text-red-700 hover:bg-red-100">Invalid</Badge>
                  )}
                </td>
                <td className="px-3 py-2 max-w-md truncate">{q.Question}</td>
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
    </div>
  );
};

export default QuestionBrowse;
