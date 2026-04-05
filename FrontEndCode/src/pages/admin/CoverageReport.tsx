import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/sonner";
import { fetchCoverage, type CoverageData } from "@/services/adminService";
import { LIFE_EVENT_REGISTRY, LIFE_EVENT_CATEGORIES } from "@/constants/lifeEventRegistry";

const CoverageReport = () => {
  const [data, setData] = useState<CoverageData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCoverage()
      .then(setData)
      .catch((err) => toast.error(err.message || "Failed to load coverage"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-legacy-purple" />
      </div>
    );
  }

  if (!data) return <div className="p-6 text-red-500">Failed to load coverage data.</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-legacy-navy mb-2">Life Event Coverage</h1>
      <p className="text-sm text-gray-500 mb-6">
        Universal questions (no tags): <span className="font-semibold">{data.universalCount}</span>
      </p>

      <div className="space-y-6">
        {LIFE_EVENT_CATEGORIES.map((cat) => {
          const items = LIFE_EVENT_REGISTRY.filter((e) => e.category === cat);
          if (items.length === 0) return null;
          return (
            <div key={cat}>
              <h3 className="text-sm font-semibold text-gray-600 mb-2">{cat}</h3>
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b">
                      <th className="px-4 py-2 text-left">Key</th>
                      <th className="px-4 py-2 text-left">Label</th>
                      <th className="px-4 py-2 text-center">Total</th>
                      <th className="px-4 py-2 text-center">Instanceable</th>
                      <th className="px-4 py-2 text-center">Non-inst.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((entry) => {
                      const cov = data.coverage[entry.key] || { total: 0, instanceable: 0, nonInstanceable: 0 };
                      const isZero = cov.total === 0;
                      return (
                        <tr key={entry.key} className={isZero ? "bg-red-50" : ""}>
                          <td className="px-4 py-2 font-mono text-xs text-gray-500">{entry.key}</td>
                          <td className="px-4 py-2 text-gray-700">{entry.label}</td>
                          <td className="px-4 py-2 text-center">
                            {isZero ? (
                              <Badge className="bg-red-100 text-red-700">0</Badge>
                            ) : (
                              <span className="font-semibold">{cov.total}</span>
                            )}
                          </td>
                          <td className="px-4 py-2 text-center text-gray-600">{cov.instanceable}</td>
                          <td className="px-4 py-2 text-center text-gray-600">{cov.nonInstanceable}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CoverageReport;
