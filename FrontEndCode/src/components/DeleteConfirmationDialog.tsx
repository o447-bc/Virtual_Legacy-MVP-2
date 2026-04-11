import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AlertTriangle } from "lucide-react";
import { requestAccountDeletion } from "@/services/dataRetentionService";
import { useToast } from "@/hooks/use-toast";

/**
 * DeleteConfirmationDialog Component
 *
 * Confirmation dialog for account deletion. Shows warnings about the 30-day
 * grace period, permanence, and benefactor impact. Requires the user to type
 * "DELETE" to enable the confirm button.
 *
 * Requirements covered:
 * - 13.3: Confirmation dialog with grace period info and DELETE confirmation
 */

interface DeleteConfirmationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeletionRequested?: () => void;
}

export const DeleteConfirmationDialog: React.FC<
  DeleteConfirmationDialogProps
> = ({ open, onOpenChange, onDeletionRequested }) => {
  const [confirmText, setConfirmText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { toast } = useToast();

  const isConfirmed = confirmText === "DELETE";

  const handleConfirm = async () => {
    if (!isConfirmed || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await requestAccountDeletion();
      toast({
        title: "Deletion requested",
        description:
          "Your account is scheduled for deletion. You have 30 days to cancel.",
      });
      onOpenChange(false);
      setConfirmText("");
      onDeletionRequested?.();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to request deletion";
      toast({ title: "Error", description: message, variant: "destructive" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) setConfirmText("");
    onOpenChange(nextOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-5 w-5" />
            Delete Your Account
          </DialogTitle>
          <DialogDescription className="text-left space-y-3 pt-2">
            <span className="block font-semibold text-gray-900">
              This action cannot be undone after the grace period.
            </span>
            <span className="block text-sm text-gray-600">
              After you confirm, your account will be scheduled for permanent
              deletion in <strong>30 days</strong>. During this grace period you
              can cancel at any time.
            </span>
            <span className="block text-sm text-gray-600">
              When deletion completes, <strong>all</strong> your recordings,
              transcripts, AI conversation summaries, and account data will be
              permanently removed. Your benefactors will lose access to your
              shared content.
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 py-2">
          <label
            htmlFor="delete-confirm"
            className="text-sm font-medium text-gray-700"
          >
            Type <span className="font-mono font-bold">DELETE</span> to confirm
          </label>
          <Input
            id="delete-confirm"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder="DELETE"
            className="font-mono"
            autoComplete="off"
          />
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={!isConfirmed || isSubmitting}
          >
            {isSubmitting ? "Requesting…" : "Delete My Account"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
