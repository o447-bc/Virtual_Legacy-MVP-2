import React, { useState, useEffect } from "react";
import { Navigate } from "react-router-dom";
import { fetchAuthSession } from "aws-amplify/auth";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "@/components/ui/sonner";

interface AdminGateProps {
  children: React.ReactNode;
}

const ADMIN_GROUP = "SoulReelAdmins";

const AdminGate: React.FC<AdminGateProps> = ({ children }) => {
  const { user, isLoading: authLoading } = useAuth();
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const checkAdminGroup = async () => {
      if (!user) {
        setIsAdmin(false);
        setChecking(false);
        return;
      }

      try {
        const session = await fetchAuthSession();
        const payload = session.tokens?.idToken?.payload;
        const groups = (payload?.["cognito:groups"] as string[] | undefined) || [];
        setIsAdmin(groups.includes(ADMIN_GROUP));
      } catch (err) {
        console.error("Error checking admin group:", err);
        setIsAdmin(false);
      } finally {
        setChecking(false);
      }
    };

    if (!authLoading) {
      checkAdminGroup();
    }
  }, [user, authLoading]);

  // Still loading auth or checking admin status
  if (authLoading || checking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-legacy-purple" />
      </div>
    );
  }

  // Not authenticated
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Authenticated but not admin
  if (!isAdmin) {
    toast.error("Access denied — admin privileges required");
    const fallback =
      user.personaType === "legacy_benefactor"
        ? "/benefactor-dashboard"
        : "/dashboard";
    return <Navigate to={fallback} replace />;
  }

  return <>{children}</>;
};

export default AdminGate;
