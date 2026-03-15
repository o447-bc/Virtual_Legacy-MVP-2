import React, { useState } from 'react';
import { format } from 'date-fns';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { toast } from "@/components/ui/sonner";
import { createAssignment, AccessCondition } from "@/services/assignmentService";
import { CalendarIcon, Info } from "lucide-react";
import { cn } from "@/lib/utils";

interface CreateAssignmentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

interface FormErrors {
  email?: string;
  conditions?: string;
  activationDate?: string;
  inactivityMonths?: string;
  checkInInterval?: string;
}

/**
 * CreateAssignmentDialog Component
 * 
 * Dialog for creating new benefactor assignments with access conditions.
 * Supports multiple access condition types:
 * - Immediate access
 * - Time-delayed access (with future date selection)
 * - Inactivity trigger (with duration and check-in interval)
 * - Manual release
 */
export const CreateAssignmentDialog: React.FC<CreateAssignmentDialogProps> = ({
  open,
  onOpenChange,
  onSuccess
}) => {
  // Form state
  const [benefactorEmail, setBenefactorEmail] = useState('');
  const [selectedCondition, setSelectedCondition] = useState<string>('');
  const [activationDate, setActivationDate] = useState<Date | undefined>(undefined);
  const [activationTime, setActivationTime] = useState('12:00');
  const [inactivityMonths, setInactivityMonths] = useState('6');
  const [checkInInterval, setCheckInInterval] = useState('30');
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  /**
   * Reset form to initial state
   */
  const resetForm = () => {
    setBenefactorEmail('');
    setSelectedCondition('');
    setActivationDate(undefined);
    setActivationTime('12:00');
    setInactivityMonths('6');
    setCheckInInterval('30');
    setErrors({});
    setIsSubmitting(false);
  };

  /**
   * Handle dialog close
   */
  const handleClose = () => {
    if (!isSubmitting) {
      resetForm();
      onOpenChange(false);
    }
  };

  /**
   * Select a single access condition (radio behavior)
   */
  const selectCondition = (conditionType: string) => {
    setSelectedCondition(conditionType);
    if (errors.conditions) {
      setErrors({ ...errors, conditions: undefined });
    }
  };

  /**
   * Validate email format
   */
  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  /**
   * Validate form inputs
   */
  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    // Validate email
    if (!benefactorEmail.trim()) {
      newErrors.email = 'Email address is required';
    } else if (!validateEmail(benefactorEmail)) {
      newErrors.email = 'Please enter a valid email address';
    }

    // Validate at least one condition selected
    if (!selectedCondition) {
      newErrors.conditions = 'Please select an access condition';
    }

    // Validate time-delayed condition
    if (selectedCondition === 'time_delayed') {
      if (!activationDate) {
        newErrors.activationDate = 'Activation date is required for time-delayed access';
      } else {
        // Combine date and time
        const [hours, minutes] = activationTime.split(':').map(Number);
        const selectedDateTime = new Date(activationDate);
        selectedDateTime.setHours(hours, minutes, 0, 0);
        
        // Check if date is in the future
        if (selectedDateTime <= new Date()) {
          newErrors.activationDate = 'Activation date must be in the future';
        }
      }
    }

    // Validate inactivity trigger condition
    if (selectedCondition === 'inactivity_trigger') {
      const months = parseInt(inactivityMonths);
      if (isNaN(months) || months < 1 || months > 24) {
        newErrors.inactivityMonths = 'Duration must be between 1 and 24 months';
      }

      const interval = parseInt(checkInInterval);
      if (isNaN(interval) || interval < 1) {
        newErrors.checkInInterval = 'Check-in interval must be at least 1 day';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  /**
   * Build access conditions array from form state
   */
  const buildAccessConditions = (): AccessCondition[] => {
    if (selectedCondition === 'immediate') {
      return [{ condition_type: 'immediate' }];
    }

    if (selectedCondition === 'time_delayed' && activationDate) {
      const [hours, minutes] = activationTime.split(':').map(Number);
      const selectedDateTime = new Date(activationDate);
      selectedDateTime.setHours(hours, minutes, 0, 0);
      return [{ condition_type: 'time_delayed', activation_date: selectedDateTime.toISOString() }];
    }

    if (selectedCondition === 'inactivity_trigger') {
      return [{
        condition_type: 'inactivity_trigger',
        inactivity_months: parseInt(inactivityMonths),
        check_in_interval_days: parseInt(checkInInterval)
      }];
    }

    if (selectedCondition === 'manual_release') {
      return [{ condition_type: 'manual_release' }];
    }

    return [];
  };

  /**
   * Handle form submission
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate form
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      // Build access conditions
      const accessConditions = buildAccessConditions();

      // Call API
      const response = await createAssignment(benefactorEmail, accessConditions);

      // Show success message
      if (response.benefactor_registered) {
        toast.success(`Assignment created! Notification sent to ${benefactorEmail}`);
      } else {
        toast.success(`Assignment created! Invitation sent to ${benefactorEmail}`);
      }

      // Reset form and close dialog
      resetForm();
      onOpenChange(false);

      // Trigger parent refresh
      if (onSuccess) {
        onSuccess();
      }

    } catch (error: any) {
      console.error('Error creating assignment:', error);
      toast.error(error.message || 'Failed to create assignment');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Benefactor Assignment</DialogTitle>
          <DialogDescription>
            Assign a benefactor to access your legacy content with specific access conditions.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Email Input */}
          <div className="space-y-2">
            <Label htmlFor="email">
              Benefactor Email Address <span className="text-red-500">*</span>
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="benefactor@example.com"
              value={benefactorEmail}
              onChange={(e) => {
                setBenefactorEmail(e.target.value);
                if (errors.email) {
                  setErrors({ ...errors, email: undefined });
                }
              }}
              className={errors.email ? 'border-red-500' : ''}
              disabled={isSubmitting}
            />
            {errors.email && (
              <p className="text-sm text-red-500">{errors.email}</p>
            )}
          </div>

          {/* Access Conditions */}
          <div className="space-y-4">
            <div>
              <Label className="text-base">
                Access Condition <span className="text-red-500">*</span>
              </Label>
              <p className="text-sm text-gray-500 mt-1">
                Select the condition that must be met for the benefactor to access your content.
              </p>
            </div>

            {errors.conditions && (
              <p className="text-sm text-red-500">{errors.conditions}</p>
            )}

            <RadioGroup
              value={selectedCondition}
              onValueChange={selectCondition}
              disabled={isSubmitting}
              className="space-y-3"
            >
              {/* Immediate Access */}
              <div className={`flex items-start space-x-3 p-4 border rounded-lg cursor-pointer transition-colors ${selectedCondition === 'immediate' ? 'border-legacy-purple bg-purple-50' : 'hover:bg-gray-50'}`}>
                <RadioGroupItem value="immediate" id="immediate" className="mt-0.5" />
                <div className="flex-1">
                  <Label htmlFor="immediate" className="text-sm font-medium cursor-pointer">
                    Immediate Access
                  </Label>
                  <p className="text-sm text-gray-500 mt-1">
                    Benefactor can access your content immediately upon accepting the assignment.
                  </p>
                </div>
              </div>

              {/* Time-Delayed Access */}
              <div className={`flex items-start space-x-3 p-4 border rounded-lg cursor-pointer transition-colors ${selectedCondition === 'time_delayed' ? 'border-legacy-purple bg-purple-50' : 'hover:bg-gray-50'}`}>
                <RadioGroupItem value="time_delayed" id="time_delayed" className="mt-0.5" />
                <div className="flex-1 space-y-3">
                  <div>
                    <Label htmlFor="time_delayed" className="text-sm font-medium cursor-pointer">
                      Time-Delayed Access
                    </Label>
                    <p className="text-sm text-gray-500 mt-1">
                      Content becomes accessible after a specific date and time.
                    </p>
                  </div>

                  {selectedCondition === 'time_delayed' && (
                    <div className="space-y-3 pl-6 border-l-2 border-gray-200" onClick={(e) => e.stopPropagation()}>
                      <div className="space-y-2">
                        <Label htmlFor="activation-date">
                          Activation Date <span className="text-red-500">*</span>
                        </Label>
                        <Popover>
                          <PopoverTrigger asChild>
                            <Button
                              id="activation-date"
                              variant="outline"
                              className={cn(
                                "w-full justify-start text-left font-normal",
                                !activationDate && "text-muted-foreground",
                                errors.activationDate && "border-red-500"
                              )}
                              disabled={isSubmitting}
                            >
                              <CalendarIcon className="mr-2 h-4 w-4" />
                              {activationDate ? format(activationDate, "PPP") : "Select date"}
                            </Button>
                          </PopoverTrigger>
                          <PopoverContent className="w-auto p-0" align="start">
                            <Calendar
                              mode="single"
                              selected={activationDate}
                              onSelect={(date) => {
                                setActivationDate(date);
                                if (errors.activationDate) {
                                  setErrors({ ...errors, activationDate: undefined });
                                }
                              }}
                              disabled={(date) => date < new Date()}
                              initialFocus
                            />
                          </PopoverContent>
                        </Popover>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="activation-time">
                          Activation Time <span className="text-red-500">*</span>
                        </Label>
                        <Input
                          id="activation-time"
                          type="time"
                          value={activationTime}
                          onChange={(e) => {
                            setActivationTime(e.target.value);
                            if (errors.activationDate) {
                              setErrors({ ...errors, activationDate: undefined });
                            }
                          }}
                          disabled={isSubmitting}
                        />
                      </div>

                      {errors.activationDate && (
                        <p className="text-sm text-red-500">{errors.activationDate}</p>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Inactivity Trigger */}
              <div className={`flex items-start space-x-3 p-4 border rounded-lg cursor-pointer transition-colors ${selectedCondition === 'inactivity_trigger' ? 'border-legacy-purple bg-purple-50' : 'hover:bg-gray-50'}`}>
                <RadioGroupItem value="inactivity_trigger" id="inactivity_trigger" className="mt-0.5" />
                <div className="flex-1 space-y-3">
                  <div>
                    <Label htmlFor="inactivity_trigger" className="text-sm font-medium cursor-pointer">
                      Inactivity Trigger
                    </Label>
                    <p className="text-sm text-gray-500 mt-1">
                      Content becomes accessible if you don't respond to check-in emails for a specified period.
                    </p>
                  </div>

                  {selectedCondition === 'inactivity_trigger' && (
                    <div className="space-y-3 pl-6 border-l-2 border-gray-200" onClick={(e) => e.stopPropagation()}>
                      <div className="space-y-2">
                        <Label htmlFor="inactivity-months">
                          Inactivity Duration (months) <span className="text-red-500">*</span>
                        </Label>
                        <Input
                          id="inactivity-months"
                          type="number"
                          min="1"
                          max="24"
                          value={inactivityMonths}
                          onChange={(e) => {
                            setInactivityMonths(e.target.value);
                            if (errors.inactivityMonths) {
                              setErrors({ ...errors, inactivityMonths: undefined });
                            }
                          }}
                          placeholder="6"
                          className={errors.inactivityMonths ? 'border-red-500' : ''}
                          disabled={isSubmitting}
                        />
                        <p className="text-xs text-gray-500">Must be between 1 and 24 months</p>
                        {errors.inactivityMonths && (
                          <p className="text-sm text-red-500">{errors.inactivityMonths}</p>
                        )}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="check-in-interval">
                          Check-in Interval (days) <span className="text-red-500">*</span>
                        </Label>
                        <Input
                          id="check-in-interval"
                          type="number"
                          min="1"
                          value={checkInInterval}
                          onChange={(e) => {
                            setCheckInInterval(e.target.value);
                            if (errors.checkInInterval) {
                              setErrors({ ...errors, checkInInterval: undefined });
                            }
                          }}
                          placeholder="30"
                          className={errors.checkInInterval ? 'border-red-500' : ''}
                          disabled={isSubmitting}
                        />
                        <p className="text-xs text-gray-500">How often you'll receive check-in emails</p>
                        {errors.checkInInterval && (
                          <p className="text-sm text-red-500">{errors.checkInInterval}</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Manual Release */}
              <div className={`flex items-start space-x-3 p-4 border rounded-lg cursor-pointer transition-colors ${selectedCondition === 'manual_release' ? 'border-legacy-purple bg-purple-50' : 'hover:bg-gray-50'}`}>
                <RadioGroupItem value="manual_release" id="manual_release" className="mt-0.5" />
                <div className="flex-1">
                  <Label htmlFor="manual_release" className="text-sm font-medium cursor-pointer">
                    I'll Decide When
                  </Label>
                  <p className="text-sm text-gray-500 mt-1">
                    Access is granted only when you personally choose to share it.
                  </p>
                  <div className="flex items-start gap-2 mt-2 p-2 bg-blue-50 rounded">
                    <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-blue-700">
                      You can release access from the Manage Benefactors page at any time.
                    </p>
                  </div>
                </div>
              </div>
            </RadioGroup>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="bg-legacy-purple hover:bg-legacy-navy"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Creating...' : 'Create Assignment'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
