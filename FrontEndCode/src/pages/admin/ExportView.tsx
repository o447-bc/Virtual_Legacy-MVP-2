import { useState } from "react";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import { toastError } from "@/utils/toastError";
import { exportQuestions } from "@/services/adminService";
import { Download } from "lucide-react";

const ExportView = () => {
  const [exporting, setExporting] = useState(false);

  const handleExport = async (format: "csv" | "json") => {
    try {
      setExporting(true);
      const data = await exportQuestions(format);

      let blob: Blob;
      let filename: string;

      if (format === "csv") {
        blob = new Blob([data as string], { type: "text/csv" });
        filename = "questions_export.csv";
      } else {
        blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        filename = "questions_export.json";
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);

      toast.success(`Exported as ${format.toUpperCase()}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Export failed";
      toastError(msg, 'ExportView');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="p-6 max-w-lg">
      <h1 className="text-2xl font-bold text-legacy-navy mb-6">Export Questions</h1>
      <p className="text-sm text-gray-500 mb-6">
        Download the entire question bank as CSV or JSON for backup or offline review.
      </p>

      <div className="space-y-4">
        <Button
          onClick={() => handleExport("csv")}
          disabled={exporting}
          className="w-full justify-start gap-3 bg-legacy-purple hover:bg-legacy-navy"
        >
          <Download className="h-4 w-4" />
          {exporting ? "Exporting..." : "Export as CSV"}
        </Button>

        <Button
          onClick={() => handleExport("json")}
          disabled={exporting}
          variant="outline"
          className="w-full justify-start gap-3"
        >
          <Download className="h-4 w-4" />
          {exporting ? "Exporting..." : "Export as JSON"}
        </Button>
      </div>
    </div>
  );
};

export default ExportView;
