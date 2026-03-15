import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/sonner";
import { useAuth } from "@/contexts/AuthContext";
import { Header } from "@/components/Header";
import {
  getAssignments,
  updateAssignment,
  resendInvitation,
  Assignment,
  AccessCondition
} from "@/services/assignmentService";
import {
  Users,
  Plus,
  Edit,
  Trash2,
  Ban,
  Mail,
  Search,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  ArrowLeft
} from "lucide-react";
import { CreateAssignmentDialog } from "@/components/CreateAssignmentDialog";

/**
 * ManageBenefactors Page Component
 * 
 * Allows Legacy Makers to view and manage their benefactor assignments.
 * Features:
 * - Display all assignments in a table
 * - Filter and sort assignments
 * - Create new assignments
 * - Edit, revoke, delete assignments
 * - Resend invitations to unregistered benefactors
 */
const ManageBenefactors: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  // State management
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [filteredAssignments, setFilteredAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filter and sort state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'email' | 'status' | 'date'>('date');
  
  // Confirmation dialog state
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    title: string;
    description: string;
    action: () => void;
    variant?: 'default' | 'destructive';
  }>({
    open: false,
    title: '',
    description: '',
    action: () => {},
    variant: 'default'
  });

  // Create assignment dialog state
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  // Redirect non-legacy-makers
  useEffect(() => {
    if (!user) {
      navigate("/login");
      return;
    }
    
    if (user.personaType !== 'legacy_maker') {
      navigate("/benefactor-dashboard");
      return;
    }
  }, [user, navigate]);

  // Fetch assignments on mount
  useEffect(() => {
    const fetchAssignments = async () => {
      if (!user?.id) return;
      
      try {
        setLoading(true);
        setError(null);
        const response = await getAssignments(user.id);
        setAssignments(response.assignments || []);
      } catch (err: any) {
        console.error('Error fetching assignments:', err);
        setError(err.message || 'Failed to load assignments');
        toast.error('Failed to load assignments');
      } finally {
        setLoading(false);
      }
    };

    fetchAssignments();
  }, [user?.id]);

  // Apply filters and sorting
  useEffect(() => {
    let filtered = [...assignments];

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(assignment =>
        assignment.benefactor_email.toLowerCase().includes(query) ||
        assignment.benefactor_first_name?.toLowerCase().includes(query) ||
        assignment.benefactor_last_name?.toLowerCase().includes(query)
      );
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(assignment => 
        assignment.assignment_status === statusFilter
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'email':
          return a.benefactor_email.localeCompare(b.benefactor_email);
        case 'status':
          return a.assignment_status.localeCompare(b.assignment_status);
        case 'date':
        default:
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });

    setFilteredAssignments(filtered);
  }, [assignments, searchQuery, statusFilter, sortBy]);

  /**
   * Format access conditions for display
   */
  const formatAccessConditions = (conditions: AccessCondition[]): string => {
    if (!conditions || conditions.length === 0) return 'None';
    
    return conditions.map(condition => {
      switch (condition.condition_type) {
        case 'immediate':
          return 'Immediate Access';
        case 'time_delayed':
          return `Time-Delayed (${new Date(condition.activation_date!).toLocaleDateString()})`;
        case 'inactivity_trigger':
          return `Inactivity (${condition.inactivity_months} months)`;
        case 'manual_release':
          return condition.released_at ? 'Manual Release (Released)' : 'Manual Release (Pending)';
        default:
          return 'Unknown';
      }
    }).join(', ');
  };

  /**
   * Get status badge variant
   */
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge className="bg-green-100 text-green-800 hover:bg-green-100"><CheckCircle className="w-3 h-3 mr-1" />Active</Badge>;
      case 'pending':
        return <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100"><Clock className="w-3 h-3 mr-1" />Pending</Badge>;
      case 'declined':
        return <Badge className="bg-red-100 text-red-800 hover:bg-red-100"><XCircle className="w-3 h-3 mr-1" />Declined</Badge>;
      case 'revoked':
        return <Badge className="bg-gray-100 text-gray-800 hover:bg-gray-100"><Ban className="w-3 h-3 mr-1" />Revoked</Badge>;
      case 'expired':
        return <Badge className="bg-gray-100 text-gray-800 hover:bg-gray-100"><AlertCircle className="w-3 h-3 mr-1" />Expired</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  /**
   * Get account status badge
   */
  const getAccountStatusBadge = (status: string) => {
    if (status === 'registered') {
      return <Badge variant="outline" className="bg-blue-50 text-blue-700">Registered</Badge>;
    }
    return <Badge variant="outline" className="bg-orange-50 text-orange-700">Invitation Pending</Badge>;
  };

  /**
   * Handle edit assignment
   */
  const handleEdit = (assignment: Assignment) => {
    // TODO: Edit functionality - would need to populate CreateAssignmentDialog with existing data
    toast.info('Edit functionality will be available soon');
  };

  /**
   * Handle revoke assignment
   */
  const handleRevoke = (assignment: Assignment) => {
    setConfirmDialog({
      open: true,
      title: 'Revoke Assignment',
      description: `Are you sure you want to revoke access for ${assignment.benefactor_email}? They will immediately lose access to your content.`,
      variant: 'destructive',
      action: async () => {
        try {
          await updateAssignment('revoke', assignment.related_user_id);
          toast.success('Assignment revoked successfully');
          
          // Refresh assignments
          const response = await getAssignments(user!.id);
          setAssignments(response.assignments || []);
        } catch (err: any) {
          console.error('Error revoking assignment:', err);
          toast.error(err.message || 'Failed to revoke assignment');
        }
      }
    });
  };

  /**
   * Handle delete assignment
   */
  const handleDelete = (assignment: Assignment) => {
    setConfirmDialog({
      open: true,
      title: 'Delete Assignment',
      description: `Are you sure you want to delete the assignment for ${assignment.benefactor_email}? This action cannot be undone.`,
      variant: 'destructive',
      action: async () => {
        try {
          await updateAssignment('delete', assignment.related_user_id);
          toast.success('Assignment deleted successfully');
          
          // Refresh assignments
          const response = await getAssignments(user!.id);
          setAssignments(response.assignments || []);
        } catch (err: any) {
          console.error('Error deleting assignment:', err);
          toast.error(err.message || 'Failed to delete assignment');
        }
      }
    });
  };

  /**
   * Handle resend invitation
   */
  const handleResendInvitation = (assignment: Assignment) => {
    setConfirmDialog({
      open: true,
      title: 'Resend Invitation',
      description: `Resend invitation email to ${assignment.benefactor_email}?`,
      variant: 'default',
      action: async () => {
        try {
          await resendInvitation(assignment.related_user_id);
          toast.success('Invitation resent successfully');
        } catch (err: any) {
          console.error('Error resending invitation:', err);
          toast.error(err.message || 'Failed to resend invitation');
        }
      }
    });
  };

  /**
   * Handle create assignment
   */
  const handleCreateAssignment = () => {
    setCreateDialogOpen(true);
  };

  /**
   * Handle successful assignment creation
   */
  const handleAssignmentCreated = async () => {
    // Refresh assignments list
    if (user?.id) {
      try {
        const response = await getAssignments(user.id);
        setAssignments(response.assignments || []);
      } catch (err: any) {
        console.error('Error refreshing assignments:', err);
      }
    }
  };

  // Early return for authentication checks
  if (!user || user.personaType !== 'legacy_maker') {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <main className="container mx-auto px-4 py-8">
        {/* Back to Dashboard Button */}
        <div className="mb-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/dashboard')}
            className="text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Return to Dashboard
          </Button>
        </div>

        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Users className="h-8 w-8 text-legacy-purple" />
            <h1 className="text-3xl font-bold text-gray-900">Manage Benefactors</h1>
          </div>
          <p className="text-gray-600">
            Control who can access your legacy content and configure access conditions
          </p>
        </div>

        {/* Create Assignment Button */}
        <div className="mb-6">
          <Button
            onClick={handleCreateAssignment}
            className="bg-legacy-purple hover:bg-legacy-navy"
          >
            <Plus className="mr-2 h-4 w-4" />
            Create Assignment
          </Button>
        </div>

        {/* Filters and Search */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search by email or name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* Status Filter */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="declined">Declined</SelectItem>
                <SelectItem value="revoked">Revoked</SelectItem>
              </SelectContent>
            </Select>

            {/* Sort By */}
            <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
              <SelectTrigger>
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="date">Date (Newest First)</SelectItem>
                <SelectItem value="email">Email (A-Z)</SelectItem>
                <SelectItem value="status">Status</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Assignments Table */}
        <div className="bg-white rounded-lg shadow">
          {loading ? (
            <div className="p-8 text-center">
              <p className="text-gray-600">Loading assignments...</p>
            </div>
          ) : error ? (
            <div className="p-8 text-center">
              <p className="text-red-600 mb-4">Error: {error}</p>
              <Button
                onClick={() => window.location.reload()}
                className="bg-legacy-purple hover:bg-legacy-navy"
              >
                Retry
              </Button>
            </div>
          ) : filteredAssignments.length === 0 ? (
            <div className="p-8 text-center">
              <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {assignments.length === 0 ? 'No Assignments Yet' : 'No Matching Assignments'}
              </h3>
              <p className="text-gray-600 mb-4">
                {assignments.length === 0
                  ? 'Create your first benefactor assignment to get started'
                  : 'Try adjusting your filters to see more results'}
              </p>
              {assignments.length === 0 && (
                <Button
                  onClick={handleCreateAssignment}
                  className="bg-legacy-purple hover:bg-legacy-navy"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Create Assignment
                </Button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Benefactor</TableHead>
                    <TableHead>Account Status</TableHead>
                    <TableHead>Assignment Status</TableHead>
                    <TableHead>Access Conditions</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredAssignments.map((assignment) => {
                    const displayName = assignment.benefactor_first_name && assignment.benefactor_last_name
                      ? `${assignment.benefactor_first_name} ${assignment.benefactor_last_name}`
                      : assignment.benefactor_email;
                    
                    const showEmail = assignment.benefactor_first_name && assignment.benefactor_last_name;
                    const canEdit = assignment.assignment_status === 'pending';
                    const canDelete = assignment.assignment_status === 'pending';
                    const canRevoke = assignment.assignment_status === 'active';
                    const canResend = assignment.account_status === 'invitation_pending' && 
                                     assignment.assignment_status === 'pending';

                    return (
                      <TableRow key={`${assignment.initiator_id}-${assignment.related_user_id}`}>
                        <TableCell>
                          <div>
                            <div className="font-medium text-gray-900">{displayName}</div>
                            {showEmail && (
                              <div className="text-sm text-gray-500">{assignment.benefactor_email}</div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          {getAccountStatusBadge(assignment.account_status)}
                        </TableCell>
                        <TableCell>
                          {getStatusBadge(assignment.assignment_status)}
                        </TableCell>
                        <TableCell>
                          <div className="text-sm text-gray-600 max-w-xs">
                            {formatAccessConditions(assignment.access_conditions)}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm text-gray-600">
                            {new Date(assignment.created_at).toLocaleDateString()}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            {canEdit && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEdit(assignment)}
                                title="Edit access conditions"
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                            )}
                            {canRevoke && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleRevoke(assignment)}
                                title="Revoke access"
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              >
                                <Ban className="h-4 w-4" />
                              </Button>
                            )}
                            {canDelete && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDelete(assignment)}
                                title="Delete assignment"
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            )}
                            {canResend && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleResendInvitation(assignment)}
                                title="Resend invitation"
                              >
                                <Mail className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </div>

        {/* Summary Stats */}
        {!loading && !error && assignments.length > 0 && (
          <div className="mt-6 text-sm text-gray-600">
            Showing {filteredAssignments.length} of {assignments.length} assignment{assignments.length !== 1 ? 's' : ''}
          </div>
        )}
      </main>

      {/* Confirmation Dialog */}
      <AlertDialog open={confirmDialog.open} onOpenChange={(open) => setConfirmDialog({ ...confirmDialog, open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{confirmDialog.title}</AlertDialogTitle>
            <AlertDialogDescription>
              {confirmDialog.description}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                confirmDialog.action();
                setConfirmDialog({ ...confirmDialog, open: false });
              }}
              className={confirmDialog.variant === 'destructive' ? 'bg-red-600 hover:bg-red-700' : ''}
            >
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Create Assignment Dialog */}
      <CreateAssignmentDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={handleAssignmentCreated}
      />
    </div>
  );
};

export default ManageBenefactors;
