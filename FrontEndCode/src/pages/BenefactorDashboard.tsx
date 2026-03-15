import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "@/components/ui/sonner";
import { useAuth } from "@/contexts/AuthContext";
import { sendInvite } from "@/services/inviteService";
import { getRelationships, Relationship } from "@/services/relationshipService";
import { ProgressBar } from "@/components/ProgressBar";
import { getUserProgress, ProgressData } from "@/services/progressService";
import { Header } from "@/components/Header";
import { 
  getBenefactorAssignments, 
  acceptAssignment, 
  declineAssignment, 
  validateAccess,
  Assignment,
  ValidateAccessResponse 
} from "@/services/assignmentService";
import { CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';

interface FormState {
  email: string;
  isLoading: boolean;
  isSubmitted: boolean;
}

const BenefactorDashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [formState, setFormState] = useState<FormState>({
    email: '',
    isLoading: false,
    isSubmitted: false
  });
  const [emailError, setEmailError] = useState('');
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [relationshipsLoading, setRelationshipsLoading] = useState(true);
  const [makerProgress, setMakerProgress] = useState<Record<string, ProgressData>>({});
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [assignmentsLoading, setAssignmentsLoading] = useState(true);
  const [accessStatus, setAccessStatus] = useState<Record<string, ValidateAccessResponse>>({});
  
  const validateEmail = (email: string): boolean => {
    if (!email.trim()) {
      setEmailError('Email is required');
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setEmailError('Please enter a valid email address');
      return false;
    }
    // Check for test email addresses
    const testEmails = ['legacymaker1@o447.net', 'legacymaker2@o447.net'];
    if (!testEmails.includes(email.toLowerCase().trim())) {
      setEmailError('For testing, please use legacyMaker1@o447.net or legacyMaker2@o447.net');
      return false;
    }
    setEmailError('');
    return true;
  };

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setFormState(prev => ({ ...prev, email: value }));
    if (emailError && value) {
      validateEmail(value);
    }
  };

  const handleSendInvite = async () => {
    if (!validateEmail(formState.email) || !user?.email) {
      return;
    }

    setFormState(prev => ({ ...prev, isLoading: true }));
    
    try {
      const result = await sendInvite({
        benefactor_email: user.email.toLowerCase(),
        invitee_email: formState.email.trim().toLowerCase()
      });
      
      setFormState(prev => ({ 
        ...prev, 
        isLoading: false, 
        isSubmitted: true,
        email: '' 
      }));
      setEmailError('');
      
      toast.success(`Invitation sent to ${result.sent_to}!`);
      
      // Refresh relationships after successful invite
      setTimeout(refreshRelationships, 1000);
      
    } catch (error: any) {
      setFormState(prev => ({ ...prev, isLoading: false }));
      const errorMessage = error.message || 'Failed to send invitation. Please try again.';
      toast.error(errorMessage);
      console.error('Error sending invite:', error);
    }
  };

  const resetForm = () => {
    setFormState({ email: '', isLoading: false, isSubmitted: false });
    setEmailError('');
  };

  // Fetch relationships on component mount
  useEffect(() => {
    const fetchRelationships = async () => {
      if (user?.id) {
        try {
          setRelationshipsLoading(true);
          const response = await getRelationships(user.id);
          setRelationships(response.relationships || []);
        } catch (error) {
          console.error('Error fetching relationships:', error);
          toast.error('Failed to load relationships');
        } finally {
          setRelationshipsLoading(false);
        }
      }
    };

    fetchRelationships();
  }, [user?.id]);

  // Fetch assignments where user is the benefactor
  useEffect(() => {
    const fetchAssignments = async () => {
      if (user?.id) {
        try {
          setAssignmentsLoading(true);
          const response = await getBenefactorAssignments();
          setAssignments(response.assignments || []);
        } catch (error) {
          console.error('Error fetching assignments:', error);
          toast.error('Failed to load assignments');
        } finally {
          setAssignmentsLoading(false);
        }
      }
    };

    fetchAssignments();
  }, [user?.id]);

  // Validate access for each assignment
  useEffect(() => {
    const validateAllAccess = async () => {
      if (!user?.id || assignments.length === 0) return;
      
      const statusMap: Record<string, ValidateAccessResponse> = {};
      
      for (const assignment of assignments) {
        try {
          const result = await validateAccess(user.id, assignment.initiator_id);
          statusMap[assignment.initiator_id] = result;
        } catch (error) {
          console.error(`Error validating access for ${assignment.initiator_id}:`, error);
        }
      }
      
      setAccessStatus(statusMap);
    };
    
    validateAllAccess();
  }, [user?.id, assignments]);

  // Fetch progress for all makers
  useEffect(() => {
    const fetchAllProgress = async () => {
      if (relationships.length === 0) return;
      
      const progressMap: Record<string, ProgressData> = {};
      
      for (const rel of relationships) {
        const data = await getUserProgress(rel.related_user_id);
        progressMap[rel.related_user_id] = data;
      }
      
      setMakerProgress(progressMap);
    };
    
    fetchAllProgress();
  }, [relationships]);

  // Refresh relationships after sending invite
  const refreshRelationships = async () => {
    if (user?.id) {
      try {
        const response = await getRelationships(user.id);
        setRelationships(response.relationships || []);
      } catch (error) {
        console.error('Error refreshing relationships:', error);
      }
    }
  };

  // Refresh assignments
  const refreshAssignments = async () => {
    if (user?.id) {
      try {
        const response = await getBenefactorAssignments();
        setAssignments(response.assignments || []);
      } catch (error) {
        console.error('Error refreshing assignments:', error);
      }
    }
  };

  // Handle accepting an assignment
  const handleAcceptAssignment = async (initiatorId: string, makerName: string) => {
    try {
      await acceptAssignment(initiatorId);
      toast.success(`Assignment from ${makerName} accepted!`);
      await refreshAssignments();
    } catch (error: any) {
      toast.error(error.message || 'Failed to accept assignment');
      console.error('Error accepting assignment:', error);
    }
  };

  // Handle declining an assignment
  const handleDeclineAssignment = async (initiatorId: string, makerName: string) => {
    try {
      await declineAssignment(initiatorId);
      toast.success(`Assignment from ${makerName} declined`);
      await refreshAssignments();
    } catch (error: any) {
      toast.error(error.message || 'Failed to decline assignment');
      console.error('Error declining assignment:', error);
    }
  };

  // Format condition description
  const formatConditionDescription = (condition: any): string => {
    switch (condition.condition_type) {
      case 'immediate':
        return 'Immediate access';
      case 'time_delayed':
        return `Access after ${new Date(condition.activation_date).toLocaleDateString()}`;
      case 'inactivity_trigger':
        return `Access after ${condition.inactivity_months} months of inactivity`;
      case 'manual_release':
        return 'Access upon manual release';
      default:
        return 'Unknown condition';
    }
  };
  
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <main className="container mx-auto px-4 py-8">
        {/* Assignments from Legacy Makers Section */}
        {assignments.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h2 className="text-2xl font-semibold mb-4">Assignments from Legacy Makers</h2>
            <p className="text-gray-600 mb-6">
              Legacy Makers who have assigned you access to their content
            </p>
            {assignmentsLoading ? (
              <p className="text-gray-600">Loading assignments...</p>
            ) : (
              <div className="space-y-4">
                {assignments.map((assignment, index) => {
                  const makerName = assignment.maker_first_name && assignment.maker_last_name
                    ? `${assignment.maker_first_name} ${assignment.maker_last_name}`
                    : assignment.maker_email || 'Unknown';
                  
                  const access = accessStatus[assignment.initiator_id];
                  const isPending = assignment.assignment_status === 'pending';
                  const isActive = assignment.assignment_status === 'active';
                  const hasAccess = access?.hasAccess === true;
                  
                  return (
                    <div 
                      key={index} 
                      className="border rounded-lg p-4"
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h3 className="font-medium text-gray-900">
                            {makerName}
                          </h3>
                          {assignment.maker_first_name && assignment.maker_last_name && (
                            <p className="text-sm text-gray-500">
                              {assignment.maker_email}
                            </p>
                          )}
                          
                          {/* Assignment Status */}
                          <div className="mt-2 flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-700">Status:</span>
                            {isPending && (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                <Clock className="w-3 h-3 mr-1" />
                                Pending Acceptance
                              </span>
                            )}
                            {isActive && hasAccess && (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                <CheckCircle className="w-3 h-3 mr-1" />
                                Access Available
                              </span>
                            )}
                            {isActive && !hasAccess && (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                <AlertCircle className="w-3 h-3 mr-1" />
                                Access Pending
                              </span>
                            )}
                            {assignment.assignment_status === 'declined' && (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                <XCircle className="w-3 h-3 mr-1" />
                                Declined
                              </span>
                            )}
                            {assignment.assignment_status === 'revoked' && (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                Revoked
                              </span>
                            )}
                          </div>

                          {/* Access Conditions */}
                          {assignment.access_conditions && assignment.access_conditions.length > 0 && (
                            <div className="mt-3">
                              <p className="text-sm font-medium text-gray-700 mb-1">Access Conditions:</p>
                              <ul className="text-sm text-gray-600 space-y-1">
                                {assignment.access_conditions.map((condition, idx) => (
                                  <li key={idx} className="flex items-start">
                                    <span className="mr-2">•</span>
                                    <span>{formatConditionDescription(condition)}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Unmet Conditions */}
                          {isActive && !hasAccess && access?.unmet_conditions && access.unmet_conditions.length > 0 && (
                            <div className="mt-3 p-3 bg-blue-50 rounded-md">
                              <p className="text-sm font-medium text-blue-900 mb-2">
                                Conditions not yet met:
                              </p>
                              <ul className="text-sm text-blue-800 space-y-1">
                                {access.unmet_conditions.map((condition, idx) => (
                                  <li key={idx} className="flex items-start">
                                    <span className="mr-2">•</span>
                                    <span>{condition.reason}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          <p className="text-sm text-gray-600 mt-2">
                            Assigned: {new Date(assignment.created_at).toLocaleDateString()}
                          </p>
                        </div>

                        {/* Action Buttons */}
                        <div className="ml-4 flex flex-col gap-2">
                          {isPending && (
                            <>
                              <Button
                                onClick={() => handleAcceptAssignment(assignment.initiator_id, makerName)}
                                className="bg-green-600 hover:bg-green-700 text-white"
                                size="sm"
                              >
                                Accept
                              </Button>
                              <Button
                                onClick={() => handleDeclineAssignment(assignment.initiator_id, makerName)}
                                variant="outline"
                                className="border-red-300 text-red-600 hover:bg-red-50"
                                size="sm"
                              >
                                Decline
                              </Button>
                            </>
                          )}
                          {isActive && hasAccess && (
                            <Button
                              onClick={() => navigate(`/response-viewer/${assignment.initiator_id}`, {
                                state: { 
                                  makerEmail: assignment.maker_email,
                                  makerFirstName: assignment.maker_first_name,
                                  makerLastName: assignment.maker_last_name
                                }
                              })}
                              className="bg-legacy-purple hover:bg-legacy-navy"
                              size="sm"
                            >
                              View Content
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* My Legacy Makers Section */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-2xl font-semibold mb-4">My Legacy Makers</h2>
          {relationshipsLoading ? (
            <p className="text-gray-600">Loading relationships...</p>
          ) : relationships.length > 0 ? (
            <div className="space-y-4">
              {relationships.map((relationship, index) => {
                const displayName = relationship.related_user_first_name && relationship.related_user_last_name
                  ? `${relationship.related_user_first_name} ${relationship.related_user_last_name}`
                  : relationship.related_user_email || relationship.related_user_id;
                
                return (
                  <div 
                    key={index} 
                    className="border rounded-lg p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                    onClick={() => navigate(`/response-viewer/${relationship.related_user_id}`, {
                      state: { 
                        makerEmail: relationship.related_user_email || relationship.related_user_id,
                        makerFirstName: relationship.related_user_first_name,
                        makerLastName: relationship.related_user_last_name
                      }
                    })}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h3 className="font-medium text-gray-900">
                          {displayName}
                        </h3>
                        {relationship.related_user_first_name && relationship.related_user_last_name && (
                          <p className="text-sm text-gray-500">
                            {relationship.related_user_email}
                          </p>
                        )}
                        {makerProgress[relationship.related_user_id] && (
                          <div className="mt-3">
                            <ProgressBar 
                              completed={makerProgress[relationship.related_user_id].completed}
                              total={makerProgress[relationship.related_user_id].total}
                              className="max-w-md"
                            />
                          </div>
                        )}
                        <p className="text-sm text-gray-600 mt-2">
                          Status: {relationship.status}
                        </p>
                        <p className="text-sm text-gray-600">
                          Connected: {new Date(relationship.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        Active
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-600 mb-2">No legacy makers connected yet</p>
              <p className="text-sm text-gray-500">Send an invitation below to get started</p>
            </div>
          )}
        </div>

        {/* Invite Section */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-2xl font-semibold mb-4">Invite a Legacy Maker</h2>
          <p className="text-gray-600 mb-6">
            Help someone preserve their memories by inviting them to create their Virtual Legacy
          </p>
          
          <div className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="inviteEmail">Email Address</Label>
                <Input
                  id="inviteEmail"
                  type="email"
                  placeholder="legacyMaker1@o447.net or legacyMaker2@o447.net"
                  value={formState.email}
                  onChange={handleEmailChange}
                  disabled={formState.isLoading}
                  className={emailError ? 'border-red-500' : ''}
                />
                {emailError && <p className="text-sm text-red-500">{emailError}</p>}
                <p className="text-xs text-gray-500">
                  For testing: Use legacyMaker1@o447.net or legacyMaker2@o447.net
                </p>
              </div>
              
              <Button 
                onClick={handleSendInvite}
                disabled={formState.isLoading || !formState.email.trim()}
                className="w-full bg-legacy-purple hover:bg-legacy-navy disabled:opacity-50"
              >
                {formState.isLoading ? 'Sending Invitation...' : 'Send Invitation'}
              </Button>
              
              {formState.isSubmitted && (
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-gray-900">Invitation Sent!</h4>
                      <p className="text-sm text-gray-600">The invitation has been sent successfully.</p>
                    </div>
                    <Button 
                      onClick={resetForm}
                      className="bg-legacy-purple hover:bg-legacy-navy"
                    >
                      Send Another
                    </Button>
                  </div>
                </div>
              )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default BenefactorDashboard;