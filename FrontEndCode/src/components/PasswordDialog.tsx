import React, { useState, useEffect } from "react";
import { updatePassword } from "aws-amplify/auth";
import { toast } from "@/components/ui/sonner";
import { toastError } from "@/utils/toastError";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loader2, Eye, EyeOff } from "lucide-react";

/**
 * PasswordDialog Component
 * 
 * Modal dialog for changing user password.
 * Integrates with AWS Amplify updatePassword API.
 * 
 * Requirements covered:
 * - 2.7: Change Password dialog with current, new, and confirm password fields
 * - 2.8: Display password requirements as helper text
 * - 2.9: Validate password meets AWS Cognito requirements
 * - 2.10: Display success message on successful change
 * - 13.2: Error handling with toast notifications
 * - 13.6: User-friendly error messages
 */

interface PasswordDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface ValidationErrors {
  currentPassword?: string;
  newPassword?: string;
  confirmPassword?: string;
}

export const PasswordDialog: React.FC<PasswordDialogProps> = ({
  open,
  onOpenChange,
}) => {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setValidationErrors({});
      setShowCurrentPassword(false);
      setShowNewPassword(false);
      setShowConfirmPassword(false);
    }
  }, [open]);

  /**
   * Validate password meets AWS Cognito requirements
   * - Minimum 8 characters
   * - At least one uppercase letter
   * - At least one lowercase letter
   * - At least one number
   * - At least one special character
   */
  const validatePassword = (password: string): string | null => {
    if (password.length < 8) {
      return "Password must be at least 8 characters long";
    }
    if (!/[A-Z]/.test(password)) {
      return "Password must contain at least one uppercase letter";
    }
    if (!/[a-z]/.test(password)) {
      return "Password must contain at least one lowercase letter";
    }
    if (!/[0-9]/.test(password)) {
      return "Password must contain at least one number";
    }
    if (!/[^A-Za-z0-9]/.test(password)) {
      return "Password must contain at least one special character";
    }
    return null;
  };

  /**
   * Validate form inputs
   * Returns true if valid, false otherwise
   */
  const validateForm = (): boolean => {
    const errors: ValidationErrors = {};

    // Validate current password
    if (!currentPassword) {
      errors.currentPassword = "Current password is required";
    }

    // Validate new password
    if (!newPassword) {
      errors.newPassword = "New password is required";
    } else {
      const passwordError = validatePassword(newPassword);
      if (passwordError) {
        errors.newPassword = passwordError;
      }
    }

    // Validate confirm password
    if (!confirmPassword) {
      errors.confirmPassword = "Please confirm your new password";
    } else if (newPassword !== confirmPassword) {
      errors.confirmPassword = "Passwords do not match";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  /**
   * Handle form submission
   * Updates password using AWS Amplify updatePassword API
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate inputs
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      // Update password in AWS Cognito
      await updatePassword({
        oldPassword: currentPassword,
        newPassword: newPassword,
      });

      // Show success message
      toast.success("Password changed successfully");

      // Close dialog
      onOpenChange(false);
    } catch (error: any) {
      // Log full error details for debugging (Requirements 13.5, 13.6)
      console.error("Password change error:", error);

      // Display user-friendly error message without sensitive information (Requirements 13.2, 13.6, 13.7)
      let errorMessage = "Failed to change password. Please try again.";
      
      // Provide specific guidance for known error types
      if (error.name === "NotAuthorizedException" || error.message?.includes("Incorrect")) {
        errorMessage = "Current password is incorrect. Please try again.";
      } else if (error.name === "InvalidPasswordException") {
        errorMessage = "New password does not meet security requirements.";
      } else if (error.name === "LimitExceededException") {
        errorMessage = "Too many attempts. Please try again later.";
      } else if (error.name === "InvalidParameterException") {
        errorMessage = "Invalid password format. Please check the requirements.";
      }
      // Don't expose raw error messages that might contain sensitive info
      
      toastError(errorMessage, 'PasswordDialog');

      // Keep dialog open to allow retry
    } finally {
      setIsSubmitting(false);
    }
  };

  /**
   * Handle cancel action
   * Resets form and closes dialog
   */
  const handleCancel = () => {
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setValidationErrors({});
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px] max-h-[90vh] overflow-y-auto w-[calc(100vw-2rem)] mx-4">
        <DialogHeader>
          <DialogTitle className="text-legacy-navy">Change Password</DialogTitle>
          <DialogDescription>
            Enter your current password and choose a new password.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            {/* Current Password Field */}
            <div className="grid gap-2">
              <label htmlFor="currentPassword" className="text-sm font-medium text-legacy-navy">
                Current Password
              </label>
              <div className="relative">
                <Input
                  id="currentPassword"
                  type={showCurrentPassword ? "text" : "password"}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  disabled={isSubmitting}
                  className={validationErrors.currentPassword ? "border-red-500 pr-10 min-h-[44px]" : "pr-10 min-h-[44px]"}
                  placeholder="Enter current password"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 min-h-[44px] min-w-[44px] flex items-center justify-center"
                  tabIndex={-1}
                  aria-label={showCurrentPassword ? "Hide password" : "Show password"}
                >
                  {showCurrentPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {validationErrors.currentPassword && (
                <p className="text-sm text-red-500">{validationErrors.currentPassword}</p>
              )}
            </div>

            {/* New Password Field */}
            <div className="grid gap-2">
              <label htmlFor="newPassword" className="text-sm font-medium text-legacy-navy">
                New Password
              </label>
              <div className="relative">
                <Input
                  id="newPassword"
                  type={showNewPassword ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  disabled={isSubmitting}
                  className={validationErrors.newPassword ? "border-red-500 pr-10 min-h-[44px]" : "pr-10 min-h-[44px]"}
                  placeholder="Enter new password"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 min-h-[44px] min-w-[44px] flex items-center justify-center"
                  tabIndex={-1}
                  aria-label={showNewPassword ? "Hide password" : "Show password"}
                >
                  {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {validationErrors.newPassword && (
                <p className="text-sm text-red-500">{validationErrors.newPassword}</p>
              )}
              <p className="text-xs text-gray-600">
                Password must be at least 8 characters and include uppercase, lowercase, number, and special character.
              </p>
            </div>

            {/* Confirm Password Field */}
            <div className="grid gap-2">
              <label htmlFor="confirmPassword" className="text-sm font-medium text-legacy-navy">
                Confirm New Password
              </label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isSubmitting}
                  className={validationErrors.confirmPassword ? "border-red-500 pr-10 min-h-[44px]" : "pr-10 min-h-[44px]"}
                  placeholder="Confirm new password"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 min-h-[44px] min-w-[44px] flex items-center justify-center"
                  tabIndex={-1}
                  aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                >
                  {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {validationErrors.confirmPassword && (
                <p className="text-sm text-red-500">{validationErrors.confirmPassword}</p>
              )}
            </div>
          </div>

          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
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
                  Changing...
                </>
              ) : (
                "Change Password"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
