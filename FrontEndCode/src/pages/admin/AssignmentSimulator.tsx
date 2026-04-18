import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toastError } from "@/utils/toastError";
import { simulate, type SimulateResult } from "@/services/adminService";
import {
  LIFE_EVENT_REGISTRY,
  LIFE_EVENT_CATEGORIES,
} from "@/constants/lifeEventRegistry";

const AssignmentSimulator = () => {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<SimulateResult | null>(null);
  const [loading, setLoading] = useState(false);

  const toggle = (key: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const handleSimulate = async () => {
    try {
      setLoading(true);
      const data = await simulate([...selected]);
      setResult(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Simulation failed";
      toastError(msg, 'AssignmentSimulator');
    } finally {
      setLoading(false);
    }
  };

  const grouped: Record<string, typeof LIFE_EVENT_REGISTRY> = {};
  for (const cat of LIFE_EVENT_CATEGORIES) {
    const items = LIFE_EVENT_REGISTRY.filter((e) => e.category === cat);
    if (items.length > 0) grouped[cat] = items;
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-legacy-navy mb-6">Assignment Simulator</h1>
      <p className="text-sm text-gray-500 mb-4">
        Select life events to see which questions would be assigned to a user with those selections.
      </p>

      {/* Help section */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-sm text-blue-800">
        <p className="font-medium mb-2">How the simulator works</p>
        <ul className="space-y-1 list-disc list-inside text-blue-700">
          <li>Check the life events a hypothetical user would select in the survey</li>
          <li>Click Simulate to see exactly which questions they'd be assigned</li>
          <li>Questions with no life event tags (universal) are always included for everyone</li>
          <li>Questions with tags are only included when ALL their required events are checked</li>
          <li>If no questions are tagged yet, every simulation returns all questions — that's expected</li>
          <li>Use this to verify your tagging is correct before it affects real users</li>
        </ul>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: checkboxes */}
        <div className="space-y-4">
          {Object.entries(grouped).map(([category, items]) => (
            <div key={category}>
              <h3 className="text-sm font-semibold text-gray-600 mb-2">{category}</h3>
              <div className="space-y-1">
                {items.map((entry) => (
                  <label
                    key={entry.key}
                    className="flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-50 px-2 py-1 rounded"
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(entry.key)}
                      onChange={() => toggle(entry.key)}
                      className="rounded border-gray-300 text-legacy-purple"
                    />
                    <span className="font-mono text-xs text-gray-400">{entry.key}</span>
                    <span className="text-gray-700">{entry.label}</span>
                  </label>
                ))}
              </div>
            </div>
          ))}

          <Button
            onClick={handleSimulate}
            disabled={loading}
            className="bg-legacy-purple hover:bg-legacy-navy"
          >
            {loading ? "Simulating..." : `Simulate (${selected.size} events)`}
          </Button>
        </div>

        {/* Right: results */}
        <div>
          {result && (
            <div className="space-y-4">
              <div className="bg-white rounded-lg shadow p-4">
                <p className="text-lg font-bold text-legacy-navy">
                  {result.totalCount} questions assigned
                </p>
                <p className="text-sm text-gray-500">
                  Across {Object.keys(result.byQuestionType).length} question types
                </p>
              </div>

              {Object.entries(result.byQuestionType)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([qtype, data]) => (
                  <div key={qtype} className="bg-white rounded-lg shadow">
                    <div className="px-4 py-3 border-b flex items-center justify-between">
                      <span className="font-medium text-gray-900">{qtype}</span>
                      <Badge className="bg-purple-100 text-purple-700">{data.count}</Badge>
                    </div>
                    <div className="px-4 py-2 max-h-48 overflow-auto">
                      {data.questions.map((q) => (
                        <div key={q.questionId} className="py-1.5 border-b last:border-0 text-sm">
                          <span className="text-gray-500 font-mono text-xs mr-2">
                            {q.questionId}
                          </span>
                          <span className="text-gray-700">{q.questionText}</span>
                          {q.isInstanceable && (
                            <Badge className="bg-indigo-100 text-indigo-600 text-[10px] ml-2">
                              {q.instancePlaceholder}
                            </Badge>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          )}

          {!result && !loading && (
            <div className="text-center text-gray-400 py-12">
              Select life events and click Simulate to see results
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AssignmentSimulator;
