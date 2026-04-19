import { useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import CreateLegacyFormFields from "@/components/signup/CreateLegacyFormFields";
import StartTheirLegacyFormFields from "@/components/signup/StartTheirLegacyFormFields";
import { trackEvent } from "@/lib/analytics";

type SignupModalVariant = "create-legacy" | "start-their-legacy";

interface SignupModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  variant: SignupModalVariant;
}

const SignupModal = ({ open, onOpenChange, variant }: SignupModalProps) => {
  useEffect(() => {
    if (open) trackEvent("signup_modal_open", { variant });
  }, [open, variant]);

  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) trackEvent("signup_modal_close", { variant });
    onOpenChange(isOpen);
  };

  const title =
    variant === "create-legacy"
      ? "Preserve Your Legacy"
      : "Help Someone You Love Preserve Theirs";

  const description =
    variant === "create-legacy"
      ? "Create an account to start recording your memories"
      : "Create an account to help preserve someone else's memories";

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg w-[95vw] max-h-[90vh] overflow-y-auto z-[60]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        {variant === "start-their-legacy" && (
          <div className="bg-gray-50 rounded-lg p-4 mb-2 space-y-2">
            <p className="text-sm font-medium text-legacy-navy">Here's how it works:</p>
            <div className="flex items-start gap-3">
              <span className="text-legacy-purple font-bold text-sm mt-0.5">1.</span>
              <p className="text-sm text-gray-600"><span className="font-medium">Create your account</span> — you sign up as the organizer</p>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-legacy-purple font-bold text-sm mt-0.5">2.</span>
              <p className="text-sm text-gray-600"><span className="font-medium">Invite your loved one</span> — send them an invitation to record their stories</p>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-legacy-purple font-bold text-sm mt-0.5">3.</span>
              <p className="text-sm text-gray-600"><span className="font-medium">Watch their stories</span> — see their recordings as they share them</p>
            </div>
            <p className="text-xs text-gray-400 italic mt-1">Example: You sign up, invite your dad, and he records his stories at his own pace. You'll see each one as he shares it.</p>
          </div>
        )}
        {variant === "create-legacy" ? (
          <CreateLegacyFormFields onSuccess={() => onOpenChange(false)} />
        ) : (
          <StartTheirLegacyFormFields onSuccess={() => onOpenChange(false)} />
        )}
      </DialogContent>
    </Dialog>
  );
};

export default SignupModal;
