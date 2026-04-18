import { useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toastError } from "@/utils/toastError";
import { toast } from "@/components/ui/sonner";
import {
  fetchFeedbackReports,
  updateFeedbackStatus,
  deleteFeedbackReport,
  type FeedbackReport,
} from "@/services/adminService";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  MessageSquare,
  ArrowUpDown,
  Archive,
  ArchiveRestore,
  Trash2,
  Loader2,
} from "lucide-react";

type SortColumn = keyof Pick<
  FeedbackReport,
  "aiClassification" | "aiSummary" | "submittedAt" | "status" | "userName" | "userEmail"
>;
type SortDirection = "asc" | "desc";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return iso;
  }
}

function classificationLabel(c: string): string {
  if (c === "bug") return "Bug";
  if (c === "feature_request") return "Feature";
  return "Unclassified";
}

function classificationBadgeClass(c: string): string {
  if (c === "bug") return "bg-red-100 text-red-700 border-red-200";
  if (c === "feature_request") return "bg-purple-100 text-purple-700 border-purple-200";
  return "bg-gray-100 text-gray-600 border-gray-200";
}

function statusBadgeClass(s: string): string {
  if (s === "active") return "bg-green-100 text-green-700 border-green-200";
  return "bg-gray-100 text-gray-500 border-gray-200";
}

const AdminFeedbackPage = () => {
  const [reports, setReports] = useState<FeedbackReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortColumn, setSortColumn] = useState<SortColumn>("submittedAt");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [selectedReport, setSelectedReport] = useState<FeedbackReport | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<Set<string>>(new Set());

  const loadReports = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchFeedbackReports();
      setReports(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load feedback reports";
      toastError(msg, "AdminFeedbackPage");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  const sortedReports = [...reports].sort((a, b) => {
    const aVal = (a[sortColumn] ?? "").toString().toLowerCase();
    const bVal = (b[sortColumn] ?? "").toString().toLowerCase();
    const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    return sortDirection === "asc" ? cmp : -cmp;
  });

  const handleArchiveToggle = async (report: FeedbackReport) => {
    const newStatus = report.status === "active" ? "archived" : "active";
    setActionLoading((prev) => new Set(prev).add(report.reportId));
    try {
      await updateFeedbackStatus(report.reportId, newStatus);
      setReports((prev) =>
        prev.map((r) =>
          r.reportId === report.reportId ? { ...r, status: newStatus } : r
        )
      );
      toast.success(newStatus === "archived" ? "Report archived" : "Report restored");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update status";
      toastError(msg, "AdminFeedbackPage");
    } finally {
      setActionLoading((prev) => {
        const next = new Set(prev);
        next.delete(report.reportId);
        return next;
      });
    }
  };

  const handleDelete = async (reportId: string) => {
    setConfirmDeleteId(null);
    setActionLoading((prev) => new Set(prev).add(reportId));
    try {
      await deleteFeedbackReport(reportId);
      setReports((prev) => prev.filter((r) => r.reportId !== reportId));
      toast.success("Report deleted");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete report";
      toastError(msg, "AdminFeedbackPage");
    } finally {
      setActionLoading((prev) => {
        const next = new Set(prev);
        next.delete(reportId);
        return next;
      });
    }
  };

  const columns: { key: SortColumn; label: string }[] = [
    { key: "aiClassification", label: "Type" },
    { key: "aiSummary", label: "Summary" },
    { key: "submittedAt", label: "Date" },
    { key: "status", label: "Status" },
    { key: "userName", label: "User" },
    { key: "userEmail", label: "Email" },
  ];

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-legacy-purple" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <MessageSquare className="h-6 w-6 text-legacy-purple" />
        <h1 className="text-2xl font-bold text-legacy-navy">
          Bugs and Feature Requests
        </h1>
        <span className="text-sm text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
          {reports.length}
        </span>
      </div>

      {reports.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <MessageSquare className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p>No feedback reports yet.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse bg-white rounded-lg shadow">
            <thead>
              <tr className="bg-legacy-navy text-white">
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className="px-3 py-2 text-left font-medium cursor-pointer select-none hover:bg-white/10"
                    onClick={() => handleSort(col.key)}
                  >
                    <span className="flex items-center gap-1">
                      {col.label}
                      <ArrowUpDown className="h-3 w-3 opacity-50" />
                      {sortColumn === col.key && (
                        <span className="text-xs opacity-75">
                          {sortDirection === "asc" ? "↑" : "↓"}
                        </span>
                      )}
                    </span>
                  </th>
                ))}
                <th className="px-3 py-2 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedReports.map((report, idx) => (
                <tr
                  key={report.reportId}
                  className={`${idx % 2 === 0 ? "bg-white" : "bg-gray-50"} hover:bg-legacy-purple/5 cursor-pointer transition-colors`}
                  onClick={() => setSelectedReport(report)}
                >
                  <td className="px-3 py-2">
                    <Badge
                      variant="outline"
                      className={classificationBadgeClass(report.aiClassification)}
                    >
                      {classificationLabel(report.aiClassification)}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 max-w-xs truncate text-gray-700">
                    {report.aiSummary || report.subject}
                  </td>
                  <td className="px-3 py-2 text-gray-700 whitespace-nowrap font-medium">
                    {formatDate(report.submittedAt)}
                  </td>
                  <td className="px-3 py-2">
                    <Badge variant="outline" className={statusBadgeClass(report.status)}>
                      {report.status === "active" ? "Active" : "Archived"}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-gray-700">{report.userName}</td>
                  <td className="px-3 py-2 text-gray-500 truncate max-w-[180px]">
                    {report.userEmail}
                  </td>
                  <td
                    className="px-3 py-2 text-right"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0"
                        disabled={actionLoading.has(report.reportId)}
                        onClick={() => handleArchiveToggle(report)}
                        title={report.status === "active" ? "Archive" : "Restore"}
                      >
                        {actionLoading.has(report.reportId) ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : report.status === "active" ? (
                          <Archive className="h-4 w-4 text-gray-500" />
                        ) : (
                          <ArchiveRestore className="h-4 w-4 text-gray-500" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0"
                        disabled={actionLoading.has(report.reportId)}
                        onClick={() => setConfirmDeleteId(report.reportId)}
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail Dialog */}
      <Dialog
        open={!!selectedReport}
        onOpenChange={(open) => {
          if (!open) setSelectedReport(null);
        }}
      >
        <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto w-[calc(100vw-2rem)] mx-4">
          {selectedReport && (
            <>
              <DialogHeader>
                <DialogTitle className="text-legacy-navy">
                  {selectedReport.subject}
                </DialogTitle>
                <DialogDescription>
                  {formatDate(selectedReport.submittedAt)}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge
                    variant="outline"
                    className={classificationBadgeClass(selectedReport.aiClassification)}
                  >
                    AI: {classificationLabel(selectedReport.aiClassification)}
                  </Badge>
                  <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                    User: {selectedReport.reportType === "bug" ? "Bug Report" : "Feature Request"}
                  </Badge>
                  <Badge
                    variant="outline"
                    className={statusBadgeClass(selectedReport.status)}
                  >
                    {selectedReport.status === "active" ? "Active" : "Archived"}
                  </Badge>
                </div>

                {selectedReport.aiSummary && (
                  <div>
                    <p className="text-xs text-gray-500 mb-1">AI Summary</p>
                    <p className="text-sm text-gray-700 italic">
                      {selectedReport.aiSummary}
                    </p>
                  </div>
                )}

                <div>
                  <p className="text-xs text-gray-500 mb-1">Description</p>
                  <div className="text-sm text-gray-800 whitespace-pre-wrap bg-gray-50 rounded-md p-3 border">
                    {selectedReport.description}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-xs text-gray-500">Submitted by</p>
                    <p className="text-gray-700">{selectedReport.userName}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Email</p>
                    <p className="text-gray-700">{selectedReport.userEmail}</p>
                  </div>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={!!confirmDeleteId}
        onOpenChange={(open) => {
          if (!open) setConfirmDeleteId(null);
        }}
      >
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle className="text-legacy-navy">Delete Report</DialogTitle>
            <DialogDescription>
              This will permanently delete this feedback report. This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" onClick={() => setConfirmDeleteId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => confirmDeleteId && handleDelete(confirmDeleteId)}
            >
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminFeedbackPage;
