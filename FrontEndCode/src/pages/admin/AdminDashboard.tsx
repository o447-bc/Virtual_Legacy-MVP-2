import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import { fetchStats, runMigration, type StatsData } from "@/services/adminService";
import {
  LayoutDashboard,
  CheckCircle,
  XCircle,
  Layers,
  BarChart3,
  AlertTriangle,
  Puzzle,
} from "lucide-react";

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [migrating, setMigrating] = useState(false);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      const data = await fetchStats();
      setStats(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load stats";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleMigrate = async () => {
    try {
      setMigrating(true);
      const result = await runMigration();
      toast.success(`Migration complete: ${result.updated} updated, ${result.skipped} skipped`);
      loadStats();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Migration failed";
      toast.error(msg);
    } finally {
      setMigrating(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-legacy-purple" />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="p-6">
        <p className="text-red-500">Failed to load dashboard data.</p>
        <Button onClick={loadStats} className="mt-2">Retry</Button>
      </div>
    );
  }

  const statCards = [
    { label: "Total Questions", value: stats.totalQuestions, icon: LayoutDashboard, color: "text-legacy-navy" },
    { label: "Valid", value: stats.validQuestions, icon: CheckCircle, color: "text-green-600" },
    { label: "Invalid", value: stats.invalidQuestions, icon: XCircle, color: "text-red-500" },
    { label: "Question Types", value: stats.questionTypes, icon: Layers, color: "text-blue-600" },
    { label: "Difficulty Levels", value: stats.difficultyLevels, icon: BarChart3, color: "text-purple-600" },
    { label: "Zero Coverage Keys", value: stats.zeroCoverageKeys, icon: AlertTriangle, color: stats.zeroCoverageKeys > 0 ? "text-amber-500" : "text-green-600" },
    { label: "Instanceable", value: stats.instanceableQuestions, icon: Puzzle, color: "text-indigo-600" },
  ];

  const gridTypes = Object.keys(stats.grid).sort();
  const difficulties = Array.from({ length: 10 }, (_, i) => String(i + 1));

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-legacy-navy">Admin Dashboard</h1>

      {/* Migration banner */}
      {stats.needsMigration > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center justify-between">
          <div>
            <p className="font-medium text-amber-800">Questions need initialization</p>
            <p className="text-sm text-amber-600">
              {stats.needsMigration} questions are missing life event attributes. Click to add defaults.
            </p>
          </div>
          <Button
            onClick={handleMigrate}
            disabled={migrating}
            className="bg-amber-600 hover:bg-amber-700"
          >
            {migrating ? "Migrating..." : "Initialize All Questions"}
          </Button>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {statCards.map(({ label, value, icon: Icon, color }) => (
          <Card key={label}>
            <CardContent className="p-4 text-center">
              <Icon className={`h-5 w-5 mx-auto mb-1 ${color}`} />
              <p className="text-2xl font-bold">{value}</p>
              <p className="text-xs text-gray-500">{label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Question Type × Difficulty Grid */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse bg-white rounded-lg shadow">
          <thead>
            <tr className="bg-legacy-navy text-white">
              <th className="px-3 py-2 text-left font-medium">Question Type</th>
              {difficulties.map((d) => (
                <th key={d} className="px-3 py-2 text-center font-medium w-16">
                  L{d}
                </th>
              ))}
              <th className="px-3 py-2 text-center font-medium w-20">Total</th>
            </tr>
          </thead>
          <tbody>
            {gridTypes.map((qtype, idx) => (
              <tr
                key={qtype}
                className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}
              >
                <td className="px-3 py-2 font-medium text-gray-900">
                  {stats.typeToTheme?.[qtype] || qtype}
                </td>
                {difficulties.map((d) => {
                  const count = stats.grid[qtype]?.[d] || 0;
                  return (
                    <td
                      key={d}
                      className={`px-3 py-2 text-center cursor-pointer hover:bg-legacy-purple/10 ${
                        count === 0 ? "text-gray-300 bg-gray-100" : "text-gray-700"
                      }`}
                      onClick={() =>
                        navigate(
                          `/admin/questions?questionType=${encodeURIComponent(qtype)}&difficulty=${d}`
                        )
                      }
                    >
                      {count || "—"}
                    </td>
                  );
                })}
                <td className="px-3 py-2 text-center font-semibold text-legacy-navy">
                  {stats.grid[qtype]?.total || 0}
                </td>
              </tr>
            ))}
            {/* Column totals */}
            <tr className="bg-legacy-navy/5 font-semibold">
              <td className="px-3 py-2 text-gray-700">Total</td>
              {difficulties.map((d) => (
                <td key={d} className="px-3 py-2 text-center text-gray-700">
                  {stats.difficultyTotals?.[d] || 0}
                </td>
              ))}
              <td className="px-3 py-2 text-center text-legacy-purple font-bold">
                {stats.grandTotal}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AdminDashboard;
