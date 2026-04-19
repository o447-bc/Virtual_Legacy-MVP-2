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
      : "Start Legacy for Someone Else";

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
