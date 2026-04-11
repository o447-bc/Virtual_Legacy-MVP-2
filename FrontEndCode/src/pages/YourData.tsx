import React, { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/Header";
import { useAuth } from "@/contexts/AuthContext";
import { useSubscription } from "@/contexts/SubscriptionContext";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { useNavigate } from "react-router-dom";
import {
  Download,
  FileText,
  Trash2,
  Shield,
  Heart,
  ArrowLeft,
  Loader2,
  ExternalLink,
  XCircle,
} from "lucide-react";
import {
  requestDataExport,
  requestGdprExport,
  getExportStatus,
  getDeletionStatus,
  cancelAccountDeletion,
  type ExportStatusResponse,
  type DeletionStatusResponse,
} from "@/services/dataRetentionService";
import { DeleteConfirmationDialog } from "@/components/DeleteConfirmationDialog";

/**
 * YourData Page
 *
 * Data & Privacy page showing export controls, deletion controls,
 * trust statement, and rights information.
 *
 * Requirements covered:
 * - 13.1–13.4: Export and deletion controls
 * - 15.1–15.8: Data retention policy page
 */
const YourData: React.FC = () => {
  const { user } = useAuth();
  const subscription = useSubscription();
  const { toast } = useToast();
  const navigate = useNavigate();

  const isLegacyMaker = user?.personaType === "legacy_maker";

  // --- Export state ---
  const [exportStatus, setExportStatus] = useState<ExportStatusResponse | null>(
    null
  );
  const [exportLoading, setExportLoading] = useState(false);
  const [exportPolling, setExportPolling] = useState(false);

  // --- Deletion state ---
  const [deletionStatus, setDeletionStatus] =
    useState<DeletionStatusResponse | null>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [cancellingDeletion, setCancellingDeletion] = useState(false);

  // --- Polling ---
  const fetchExportStatus = useCallback(async () => {
    try {
      const status = await getExportStatus();
      setExportStatus(status);
      if (status.status === "processing" || status.status === "pending_retrieval") {
        setExportPolling(true);
      } else {
        setExportPolling(false);
      }
    } catch {
      setExportPolling(false);
    }
  }, []);

  const fetchDeletionStatus = useCallback(async () => {
    try {
      const status = await getDeletionStatus();
      setDeletionStatus(status);
    } catch {
      // No pending deletion
    }
  }, []);

  useEffect(() => {
    if (isLegacyMaker) {
      fetchExportStatus();
      fetchDeletionStatus();
    }
  }, [isLegacyMaker, fetchExportStatus, fetchDeletionStatus]);

  useEffect(() => {
    if (!exportPolling) return;
    const interval = setInterval(fetchExportStatus, 10000);
    return () => clearInterval(interval);
  }, [exportPolling, fetchExportStatus]);

  // --- Handlers ---
  const handleFullExport = async () => {
    setExportLoading(true);
    try {
      await requestDataExport();
      toast({
        title: "Export started",
        description: "We'll email you when your download is ready.",
      });
      fetchExportStatus();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to start export";
      toast({ title: "Error", description: message, variant: "destructive" });
    } finally {
      setExportLoading(false);
    }
  };

  const handleGdprExport = async () => {
    setExportLoading(true);
    try {
      await requestGdprExport();
      toast({
        title: "Export started",
        description: "We'll email you when your data file is ready.",
      });
      fetchExportStatus();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to start export";
      toast({ title: "Error", description: message, variant: "destructive" });
    } finally {
      setExportLoading(false);
    }
  };

  const handleCancelDeletion = async () => {
    setCancellingDeletion(true);
    try {
      await cancelAccountDeletion();
      toast({
        title: "Deletion canceled",
        description: "Your account and content are safe.",
      });
      setDeletionStatus(null);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to cancel deletion";
      toast({ title: "Error", description: message, variant: "destructive" });
    } finally {
      setCancellingDeletion(false);
    }
  };

  const isPendingDeletion = deletionStatus?.status === "pending";
  const hasActiveExport =
    exportStatus?.status === "processing" ||
    exportStatus?.status === "pending_retrieval";

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-3xl mx-auto px-4 py-8">
        {/* Back button */}
        <Button
          variant="ghost"
          className="mb-4 text-legacy-purple"
          onClick={() => navigate(-1)}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>

        <h1 className="text-2xl font-bold text-legacy-navy mb-2">
          Your Data
        </h1>

        {/* Trust Statement */}
        <Card className="mb-6 border-legacy-purple/20">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <Heart className="h-5 w-5 text-legacy-purple mt-0.5 shrink-0" />
              <div>
                <p className="text-sm text-gray-700">
                  Your stories are always yours. All recordings remain
                  accessible regardless of your plan. We never delete your
                  content unless you explicitly ask us to.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Storage Explanation */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Shield className="h-5 w-5 text-legacy-purple" />
              How We Protect Your Content
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-gray-600">
            <p>
              Your recordings are encrypted and stored securely. Over time,
              content you and your benefactors haven't accessed recently is
              moved to lower-cost archival storage — this keeps costs
              sustainable while preserving everything.
            </p>
            <p>
              If archived content is requested, it's automatically retrieved.
              You or your benefactors may see a short wait the first time.
            </p>
          </CardContent>
        </Card>

        {/* Export Section — legacy_maker only */}
        {isLegacyMaker && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Download className="h-5 w-5 text-legacy-purple" />
                Download Your Legacy
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Active export status */}
              {hasActiveExport && exportStatus && (
                <div className="rounded-md bg-blue-50 p-4 text-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                    <span className="font-medium text-blue-800">
                      {exportStatus.status === "pending_retrieval"
                        ? "Retrieving archived content…"
                        : "Preparing your export…"}
                    </span>
                  </div>
                  <p className="text-blue-700">
                    We'll email you when your download is ready.
                  </p>
                </div>
              )}

              {/* Ready export */}
              {exportStatus?.status === "ready" && exportStatus.downloadUrl && (
                <div className="rounded-md bg-green-50 p-4 text-sm">
                  <p className="font-medium text-green-800 mb-2">
                    Your export is ready!
                  </p>
                  <a
                    href={exportStatus.downloadUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-green-700 underline"
                  >
                    Download now
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              )}

              {/* Export buttons */}
              {!hasActiveExport && (
                <div className="space-y-3">
                  {subscription.isPremium ? (
                    <Button
                      onClick={handleFullExport}
                      disabled={exportLoading}
                      className="w-full bg-legacy-purple hover:bg-legacy-purple/90"
                    >
                      {exportLoading ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="mr-2 h-4 w-4" />
                      )}
                      Download My Legacy
                      <Badge className="ml-2 bg-white/20 text-white text-xs">
                        Premium
                      </Badge>
                    </Button>
                  ) : (
                    <div className="rounded-md bg-gray-50 border p-4 text-sm text-gray-600">
                      <p className="mb-2">
                        Full export (videos + transcripts) is available on the
                        Premium plan.
                      </p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigate("/pricing")}
                      >
                        View Plans
                      </Button>
                    </div>
                  )}

                  <Button
                    variant="outline"
                    onClick={handleGdprExport}
                    disabled={exportLoading}
                    className="w-full"
                  >
                    {exportLoading ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <FileText className="mr-2 h-4 w-4" />
                    )}
                    Download My Data (Text Only)
                  </Button>
                  <p className="text-xs text-gray-500">
                    Includes transcripts, summaries, and profile data in JSON
                    format. Available on all plans.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Deletion Section — legacy_maker only */}
        {isLegacyMaker && (
          <Card className="mb-6 border-red-200">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2 text-red-700">
                <Trash2 className="h-5 w-5" />
                Delete Your Account
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {isPendingDeletion && deletionStatus ? (
                <div className="rounded-md bg-red-50 p-4 text-sm space-y-3">
                  <p className="font-medium text-red-800">
                    Your account is scheduled for deletion.
                  </p>
                  {deletionStatus.graceEndDate && (
                    <p className="text-red-700">
                      Deletion date:{" "}
                      <strong>
                        {new Date(
                          deletionStatus.graceEndDate
                        ).toLocaleDateString()}
                      </strong>
                    </p>
                  )}
                  <Button
                    variant="outline"
                    onClick={handleCancelDeletion}
                    disabled={cancellingDeletion}
                    className="border-red-300 text-red-700 hover:bg-red-50"
                  >
                    {cancellingDeletion ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <XCircle className="mr-2 h-4 w-4" />
                    )}
                    Cancel Deletion
                  </Button>
                </div>
              ) : (
                <>
                  <p className="text-sm text-gray-600">
                    Permanently delete your account and all associated data.
                    You'll have a 30-day grace period to change your mind.
                  </p>
                  <Button
                    variant="destructive"
                    onClick={() => setShowDeleteDialog(true)}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete My Account
                  </Button>
                </>
              )}
            </CardContent>
          </Card>
        )}

        {/* Rights Section */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Your Rights</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-gray-600 space-y-2">
            <p>
              Under GDPR and CCPA, you have the right to access, export, and
              delete your personal data. SoulReel is committed to making these
              rights easy to exercise.
            </p>
            <ul className="list-disc list-inside space-y-1">
              <li>Export your data at any time (text export on all plans)</li>
              <li>Request account deletion with a 30-day safety window</li>
              <li>
                Your benefactors keep access to shared content unless you
                delete your account
              </li>
            </ul>
          </CardContent>
        </Card>
      </main>

      <DeleteConfirmationDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        onDeletionRequested={() => fetchDeletionStatus()}
      />
    </div>
  );
};

export default YourData;
