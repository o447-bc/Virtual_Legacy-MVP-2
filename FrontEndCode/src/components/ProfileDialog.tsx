import React, { useState, useEffect } from "react";
import { updateUserAttributes } from "aws-amplify/auth";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "@/components/ui/sonner";
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
import { Loader2 } from "lucide-react";

/**
 * ProfileDialog Component
 * 
 * Modal dialog for editing user profile information (firstName and lastName).
 * Integrates with AWS Amplify updateUserAttributes API and refreshes AuthContext.
 * 
 * Requirements covered:
 * - 2.3: Edit Profile dialog with firstName and lastName fields
 * - 2.4: Input validation (non-empty, max 50 characters)
 * - 2.5: Update user attributes in AWS Cognito
 * - 2.6: Refresh AuthContext after successful update
 * - 13.1: Error handling with toast notifications
 * - 13.6: User-friendly error messages
 */

interface ProfileDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentFirstName: string;
  currentLastName: string;
}

interface ValidationErrors {
  firstName?: string;
  lastName?: string;
}

export const ProfileDialog: React.FC<ProfileDialogProps> = ({
  open,
  onOpenChange,
  currentFirstName,
  currentLastName,
}) => {
  const { refreshUser } = useAuth();
  const [firstName, setFirstName] = useState(currentFirstName);
  const [lastName, setLastName] = useState(currentLastName);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});

  // Reset form when dialog opens with new values
  useEffect(() => {
    if (open) {
      setFirstName(currentFirstName);
      setLastName(currentLastName);
      setValidationErrors({});
    }
  }, [open, currentFirstName, currentLastName]);

  /**
   * Validate form inputs
   * Returns true if valid, false otherwise
   */
  const validateForm = (): boolean => {
    const errors: ValidationErrors = {};

    // Validate firstName
    if (!firstName.trim()) {
      errors.firstName = "First name is required";
    } else if (firstName.length > 50) {
      errors.firstName = "First name must be 50 characters or less";
    }

    // Validate lastName
    if (!lastName.trim()) {
      errors.lastName = "Last name is required";
    } else if (lastName.length > 50) {
      errors.lastName = "Last name must be 50 characters or less";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  /**
   * Handle form submission
   * Updates user attributes in AWS Cognito and refreshes AuthContext
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate inputs
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      // Update user attributes in AWS Cognito
      await updateUserAttributes({
        userAttributes: {
          given_name: firstName.trim(),
          family_name: lastName.trim(),
        },
      });

      // Refresh AuthContext to reflect new data
      await refreshUser();

      // Show success message
      toast.success("Profile updated successfully");

      // Close dialog
      onOpenChange(false);
    } catch (error: any) {
      // Log full error details for debugging (Requirements 13.5, 13.6)
      console.error("Profile update error:", error);

      // Display user-friendly error message without sensitive information (Requirements 13.1, 13.6, 13.7)
      let errorMessage = "Failed to update profile. Please try again.";
      
      // Provide specific guidance for known error types
      if (error.name === "NotAuthorizedException") {
        errorMessage = "Your session has expired. Please log in again.";
      } else if (error.name === "InvalidParameterException") {
        errorMessage = "Invalid profile information. Please check your inputs.";
      } else if (error.name === "LimitExceededException") {
        errorMessage = "Too many attempts. Please try again later.";
      }
      // Don't expose raw error messages that might contain sensitive info
      
      toast.error(errorMessage);

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
    setFirstName(currentFirstName);
    setLastName(currentLastName);
    setValidationErrors({});
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px] max-h-[90vh] overflow-y-auto w-[calc(100vw-2rem)] mx-4">
        <DialogHeader>
          <DialogTitle className="text-legacy-navy">Edit Profile</DialogTitle>
          <DialogDescription>
            Update your profile information. Changes will be saved to your account.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            {/* First Name Field */}
            <div className="grid gap-2">
              <label htmlFor="firstName" className="text-sm font-medium text-legacy-navy">
                First Name
              </label>
              <Input
                id="firstName"
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                disabled={isSubmitting}
                className={validationErrors.firstName ? "border-red-500 min-h-[44px]" : "min-h-[44px]"}
                placeholder="Enter your first name"
                maxLength={51} // Allow typing one extra to trigger validation
              />
              {validationErrors.firstName && (
                <p className="text-sm text-red-500">{validationErrors.firstName}</p>
              )}
            </div>

            {/* Last Name Field */}
            <div className="grid gap-2">
              <label htmlFor="lastName" className="text-sm font-medium text-legacy-navy">
                Last Name
              </label>
              <Input
                id="lastName"
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                disabled={isSubmitting}
                className={validationErrors.lastName ? "border-red-500 min-h-[44px]" : "min-h-[44px]"}
                placeholder="Enter your last name"
                maxLength={51} // Allow typing one extra to trigger validation
              />
              {validationErrors.lastName && (
                <p className="text-sm text-red-500">{validationErrors.lastName}</p>
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
                  Saving...
                </>
              ) : (
                "Save Changes"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
