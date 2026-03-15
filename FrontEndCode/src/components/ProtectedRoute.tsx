import { Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

interface ProtectedRouteProps {
  children: React.ReactNode;
  /** If set, only users with this personaType can access the route */
  requiredPersona?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredPersona }) => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return null; // or a spinner — avoids flash-redirect while auth state loads
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requiredPersona && user.personaType !== requiredPersona) {
    const fallback = user.personaType === 'legacy_benefactor'
      ? '/benefactor-dashboard'
      : '/dashboard';
    return <Navigate to={fallback} replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
