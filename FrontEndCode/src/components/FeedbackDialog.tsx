import React, { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { submitFeedback } from "@/services/adminService";
import { toastError } from "@/utils/toastError";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Loader2, CheckCircle } from "lucide-react";

interface FeedbackDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface ValidationErrors {
  reportType?: string;
  subject?: string;
  description?: string;
}

export const FeedbackDialog: React.FC<FeedbackDialogProps> = ({
  open,
  onOpenChange,
}) => {
  const { user } = useAuth();

  const [reportType, setReportType] = useState<string>("");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});

  // Pre-filled user info
  const userEmail = user?.email || "";
  const userName =
    user?.firstName && user?.lastName
      ? `${user.firstName} ${user.lastName}`
      : user?.firstName
        ? user.firstName
        : "Anonymous";

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      setReportType("");
      setSubject("");
      setDescription("");
      setValidationErrors({});
      setIsSubmitting(false);
      setIsSuccess(false);
    }
  }, [open]);

  // Auto-close after success
  useEffect(() => {
    if (isSuccess) {
      const timer = setTimeout(() => onOpenChange(false), 2500);
      return () => clearTimeout(timer);
    }
  }, [isSuccess, onOpenChange]);

  const validateForm = (): boolean => {
    const errors: ValidationErrors = {};

    if (!reportType) {
      errors.reportType = "Please select a report type";
    }
    if (!subject.trim()) {
      errors.subject = "Subject is required";
    } else if (subject.length > 200) {
      errors.subject = "Subject must be 200 characters or less";
    }
    if (!description.trim()) {
      errors.description = "Description is required";
    } else if (description.trim().length < 10) {
      errors.description = "Description must be at least 10 characters";
    } else if (description.length > 5000) {
      errors.description = "Description must be 5000 characters or less";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      await submitFeedback({
        reportType: reportType as "bug" | "feature",
        subject: subject.trim(),
        description: description.trim(),
        userEmail,
        userName,
      });
      setIsSuccess(true);
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : "Failed to submit feedback. Please try again.";
      toastError(msg, "FeedbackDialog");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        if (!isSubmitting) onOpenChange(value);
      }}
    >
      <DialogContent className="sm:max-w-[540px] max-h-[90vh] overflow-y-auto w-[calc(100vw-2rem)] mx-4">
        <DialogHeader>
          <DialogTitle className="text-legacy-navy">
            Report a Bug or Suggest a Feature
          </DialogTitle>
          <DialogDescription>
            We appreciate you taking the time to help us improve SoulReel. Every
            report is read and helps us make things better for everyone.
          </DialogDescription>
        </DialogHeader>

        {isSuccess ? (
          <div className="flex flex-col items-center justify-center py-8 gap-4">
            <CheckCircle className="h-12 w-12 text-green-500" />
            <p className="text-center text-legacy-navy font-medium">
              Thank you for your feedback
            </p>
            <p className="text-center text-sm text-gray-600">
              We read every report and it helps us make SoulReel better for
              everyone.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="grid gap-4 py-4">
              {/* Report Type */}
              <div className="grid gap-2">
                <label
                  htmlFor="feedbackReportType"
                  className="text-sm font-medium text-legacy-navy"
                >
                  Report Type
                </label>
                <Select
                  value={reportType}
                  onValueChange={(v) => {
                    setReportType(v);
                    if (validationErrors.reportType) {
                      setValidationErrors((prev) => {
                        const next = { ...prev };
                        delete next.reportType;
                        return next;
                      });
                    }
                  }}
                  disabled={isSubmitting}
                >
                  <SelectTrigger
                    id="feedbackReportType"
                    className={`min-h-[44px] ${validationErrors.reportType ? "border-red-500" : ""}`}
                    aria-invalid={!!validationErrors.reportType}
                    aria-describedby={
                      validationErrors.reportType
                        ? "feedbackReportType-error"
                        : undefined
                    }
                  >
                    <SelectValue placeholder="Select a type..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bug">Bug Report</SelectItem>
                    <SelectItem value="feature">Feature Request</SelectItem>
                  </SelectContent>
                </Select>
                {validationErrors.reportType && (
                  <p
                    id="feedbackReportType-error"
                    className="text-sm text-red-500"
                  >
                    {validationErrors.reportType}
                  </p>
                )}
              </div>

              {/* Subject */}
              <div className="grid gap-2">
                <label
                  htmlFor="feedbackSubject"
                  className="text-sm font-medium text-legacy-navy"
                >
                  Subject
                </label>
                <Input
                  id="feedbackSubject"
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  disabled={isSubmitting}
                  className={`min-h-[44px] ${validationErrors.subject ? "border-red-500" : ""}`}
                  placeholder="Brief summary of the issue or idea"
                  maxLength={201}
                  aria-invalid={!!validationErrors.subject}
                  aria-describedby={
                    validationErrors.subject
                      ? "feedbackSubject-error"
                      : undefined
                  }
                />
                {validationErrors.subject && (
                  <p id="feedbackSubject-error" className="text-sm text-red-500">
                    {validationErrors.subject}
                  </p>
                )}
              </div>

              {/* Description */}
              <div className="grid gap-2">
                <label
                  htmlFor="feedbackDescription"
                  className="text-sm font-medium text-legacy-navy"
                >
                  Description
                </label>
                <Textarea
                  id="feedbackDescription"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={isSubmitting}
                  className={`min-h-[120px] ${validationErrors.description ? "border-red-500" : ""}`}
                  placeholder="Tell us more about what happened or what you'd like to see..."
                  maxLength={5001}
                  aria-invalid={!!validationErrors.description}
                  aria-describedby={
                    validationErrors.description
                      ? "feedbackDescription-error"
                      : undefined
                  }
                />
                {validationErrors.description && (
                  <p
                    id="feedbackDescription-error"
                    className="text-sm text-red-500"
                  >
                    {validationErrors.description}
                  </p>
                )}
                <p className="text-xs text-gray-500">
                  {description.length}/5000 characters
                </p>
              </div>

              {/* Pre-filled user info (read-only) */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="grid gap-1">
                  <label className="text-xs text-gray-500">Your Name</label>
                  <p className="text-sm text-legacy-navy">{userName}</p>
                </div>
                <div className="grid gap-1">
                  <label className="text-xs text-gray-500">Your Email</label>
                  <p className="text-sm text-legacy-navy truncate">{userEmail}</p>
                </div>
              </div>
            </div>

            <DialogFooter className="flex-col sm:flex-row gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isSubmitting}
                className="min-h-[44px] w-full sm:w-auto"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting}
                className="bg-legacy-purple hover:bg-legacy-purple/90 min-h-[44px] w-full sm:w-auto"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  "Submit Feedback"
                )}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
};
