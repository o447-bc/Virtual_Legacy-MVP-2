import React from "react";
import { Crown } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface UpgradePromptDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  message: string;
  previewQuestion?: string;
  questionCount?: number;
  onUpgrade: () => void;
}

export const UpgradePromptDialog: React.FC<UpgradePromptDialogProps> = ({
  open,
  onOpenChange,
  title,
  message,
  previewQuestion,
  questionCount,
  onUpgrade,
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-legacy-navy">
            <Crown className="h-5 w-5 text-legacy-purple" />
            {title}
          </DialogTitle>
          <DialogDescription className="text-base text-gray-600 pt-2">
            {message}
          </DialogDescription>
        </DialogHeader>

        {previewQuestion && (
          <div className="border-l-4 border-legacy-purple bg-purple-50 rounded-r-md p-4 my-2">
            <p className="text-sm italic text-gray-700">"{previewQuestion}"</p>
          </div>
        )}

        {questionCount != null && questionCount > 0 && (
          <p className="text-sm font-medium text-legacy-purple">
            {questionCount} questions are waiting for you
          </p>
        )}

        <DialogFooter className="flex flex-col sm:flex-row gap-2 pt-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="sm:order-1"
          >
            Maybe Later
          </Button>
          <Button
            onClick={onUpgrade}
            className="bg-legacy-purple hover:bg-legacy-purple/90 text-white sm:order-2"
          >
            <Crown className="h-4 w-4 mr-1" />
            Upgrade to Premium
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
