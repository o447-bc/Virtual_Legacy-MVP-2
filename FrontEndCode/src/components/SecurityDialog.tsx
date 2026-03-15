import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronDown, ChevronUp, Shield, Lock, Eye, Server } from "lucide-react";

/**
 * SecurityDialog Component
 * 
 * Modal dialog displaying security information with progressive disclosure.
 * Presents information in three levels: simple, detailed, and technical.
 * 
 * Requirements covered:
 * - 5.1: Security & Privacy menu item opens dialog
 * - 5.2: Progressive disclosure with three levels
 * - 5.3: Level 1 displayed by default
 * - 5.4: Simple, non-technical explanation in Level 1
 * - 5.5: Level 1 includes encryption and protection message
 * - 5.6: "Learn More" button to reveal Level 2
 * - 5.7: Level 2 provides detailed explanation
 * - 5.8: Level 2 references customer-managed keys and audit logging
 * - 5.9: "Technical Details" button to reveal Level 3
 * - 5.10: Level 3 provides technical details from Phase 1 security
 * - 5.11: Level 3 includes KMS, CloudTrail, GuardDuty, IAM details
 * - 5.12: Allow collapsing expanded sections
 * - 5.13: Include link to full security documentation
 */

interface SecurityDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const SecurityDialog: React.FC<SecurityDialogProps> = ({
  open,
  onOpenChange,
}) => {
  const [level2Open, setLevel2Open] = useState(false);
  const [level3Open, setLevel3Open] = useState(false);

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      setLevel2Open(false);
      setLevel3Open(false);
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto w-[calc(100vw-2rem)] mx-4">
        <DialogHeader>
          <DialogTitle className="text-legacy-navy flex items-center gap-2">
            <Shield className="h-5 w-5 text-legacy-purple" />
            Security & Privacy
          </DialogTitle>
          <DialogDescription>
            Learn how we protect your videos and personal information
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Level 1: Simple Explanation (Always Visible) */}
          <div className="space-y-3">
            <div className="flex items-start gap-3 p-4 bg-blue-50 rounded-lg border border-blue-100">
              <Lock className="h-5 w-5 text-legacy-purple mt-0.5 flex-shrink-0" />
              <div className="space-y-2">
                <p className="text-sm font-medium text-legacy-navy">
                  Your videos and personal information are encrypted and protected
                </p>
                <p className="text-sm text-gray-600">
                  We use industry-standard security measures to keep your data safe.
                </p>
                <p className="text-sm text-gray-600">
                  Only you and people you invite can access your content.
                </p>
              </div>
            </div>
          </div>

          {/* Level 2: Detailed Explanation (Expandable) */}
          <Collapsible open={level2Open} onOpenChange={setLevel2Open}>
            <CollapsibleTrigger asChild>
              <Button
                variant="outline"
                className="w-full justify-between hover:bg-legacy-purple/5 hover:border-legacy-purple min-h-[44px]"
              >
                <span className="flex items-center gap-2">
                  <Eye className="h-4 w-4" />
                  Learn More About Our Security
                </span>
                {level2Open ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-3">
              <div className="space-y-3 p-4 bg-purple-50 rounded-lg border border-purple-100">
                <div className="space-y-3">
                  <div>
                    <h4 className="text-sm font-semibold text-legacy-navy mb-1">
                      Customer-Managed Encryption
                    </h4>
                    <p className="text-sm text-gray-600">
                      Your data is encrypted using keys that we control, not default cloud provider keys.
                      This gives us greater control over your data security.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold text-legacy-navy mb-1">
                      Audit Logging
                    </h4>
                    <p className="text-sm text-gray-600">
                      All access to your data is logged for security monitoring. We can track who accessed
                      what and when, ensuring accountability.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold text-legacy-navy mb-1">
                      Threat Detection
                    </h4>
                    <p className="text-sm text-gray-600">
                      Automated systems continuously monitor for suspicious activity and potential security
                      threats, alerting us immediately if anything unusual is detected.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold text-legacy-navy mb-1">
                      Access Controls
                    </h4>
                    <p className="text-sm text-gray-600">
                      Strict permissions ensure only authorized services can access your data. We follow
                      the principle of least privilege, granting only the minimum access necessary.
                    </p>
                  </div>
                </div>
              </div>
            </CollapsibleContent>
          </Collapsible>

          {/* Level 3: Technical Details (Expandable, only when Level 2 is open) */}
          {level2Open && (
            <Collapsible open={level3Open} onOpenChange={setLevel3Open}>
              <CollapsibleTrigger asChild>
                <Button
                  variant="outline"
                  className="w-full justify-between hover:bg-legacy-purple/5 hover:border-legacy-purple min-h-[44px]"
                >
                  <span className="flex items-center gap-2">
                    <Server className="h-4 w-4" />
                    Technical Details
                  </span>
                  {level3Open ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-3">
                <div className="space-y-3 p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <p className="text-xs font-semibold text-legacy-navy uppercase tracking-wide mb-2">
                    Cybersecurity Details
                  </p>

                  <div className="space-y-2 text-sm text-gray-700">
                    <div className="flex items-start gap-2">
                      <span className="text-legacy-purple font-mono text-xs mt-0.5">•</span>
                      <p>
                        <span className="font-semibold">Customer-managed cryptographic keys with automatic annual rotation:</span> All
                        encryption operations use organization-controlled master keys rather than provider-managed defaults. Automatic
                        yearly rotation of key material is enabled to limit exposure duration, align with cryptographic best practices,
                        and reduce risk if a key is ever suspected to be compromised.
                      </p>
                    </div>

                    <div className="flex items-start gap-2">
                      <span className="text-legacy-purple font-mono text-xs mt-0.5">•</span>
                      <p>
                        <span className="font-semibold">Database encryption at rest:</span> Every database table storing user data—including
                        personal questions, video responses, and associated metadata—is fully encrypted at rest using customer-managed keys.
                        This ensures that stored personal content remains protected even if physical or logical access to the underlying
                        storage is obtained.
                      </p>
                    </div>

                    <div className="flex items-start gap-2">
                      <span className="text-legacy-purple font-mono text-xs mt-0.5">•</span>
                      <p>
                        <span className="font-semibold">Object storage encryption at rest:</span> All video files and related objects in
                        persistent storage are encrypted using customer-managed keys. Server-side encryption with efficient key handling is
                        configured to balance strong protection with operational cost-effectiveness, preventing unauthorized access to raw
                        video content.
                      </p>
                    </div>

                    <div className="flex items-start gap-2">
                      <span className="text-legacy-purple font-mono text-xs mt-0.5">•</span>
                      <p>
                        <span className="font-semibold">Comprehensive audit logging of data plane activities:</span> Full logging is enabled
                        for all API-level access and management events related to data storage, retrieval, and modification. These detailed
                        audit trails support forensic investigation, compliance reporting, and detection of anomalous or unauthorized access
                        attempts to sensitive user videos.
                      </p>
                    </div>

                    <div className="flex items-start gap-2">
                      <span className="text-legacy-purple font-mono text-xs mt-0.5">•</span>
                      <p>
                        <span className="font-semibold">Real-time threat detection and alerting:</span> Continuous monitoring is implemented
                        for malicious activity, unusual behavior patterns, and potential compromise indicators across the environment. Automated
                        alerts are generated for suspicious events, enabling rapid response to threats targeting user data or application components.
                      </p>
                    </div>

                    <div className="flex items-start gap-2">
                      <span className="text-legacy-purple font-mono text-xs mt-0.5">•</span>
                      <p>
                        <span className="font-semibold">Principle of least privilege for application identities:</span> All serverless functions,
                        compute instances, and automated processes operate under tightly scoped permissions. Access is granted only to the specific
                        resources and actions required for legitimate operation—no broad or wildcard permissions are used—significantly reducing the
                        blast radius of any credential compromise.
                      </p>
                    </div>

                    <div className="flex items-start gap-2">
                      <span className="text-legacy-purple font-mono text-xs mt-0.5">•</span>
                      <p>
                        <span className="font-semibold">Point-in-time recovery for critical data stores:</span> Continuous or frequent point-in-time
                        recovery is activated on primary data tables. This capability allows restoration to a known good state in the event of
                        accidental deletion, corruption, ransomware encryption, or other destructive incidents affecting user responses.
                      </p>
                    </div>

                    <div className="flex items-start gap-2">
                      <span className="text-legacy-purple font-mono text-xs mt-0.5">•</span>
                      <p>
                        <span className="font-semibold">Object versioning and protection:</span> Versioning is enabled on all storage buckets holding
                        user videos and attachments. This safeguards against accidental overwrites, malicious deletions, or unintended modifications
                        by preserving historical versions and allowing recovery of prior states when needed.
                      </p>
                    </div>
                  </div>

                  <div className="mt-3 pt-3 border-t border-gray-300">
                    <p className="text-xs text-gray-600 italic">
                      These controls form a defense-in-depth foundation focused on protecting highly personal and sensitive video content throughout
                      its lifecycle. They emphasize encryption, access minimization, visibility, recoverability, and proactive threat monitoring—core
                      pillars of modern application security.
                    </p>
                  </div>
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
