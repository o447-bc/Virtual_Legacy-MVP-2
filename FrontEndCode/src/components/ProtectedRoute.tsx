import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

interface ProtectedRouteProps {
  children: React.ReactNode;
  /** If set, only users with this personaType can access the route */
  requiredPersona?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredPersona }) => {
  const { user, isLoading, hasCompletedSurvey } = useAuth();
  const location = useLocation();

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

  // Redirect legacy makers to dashboard (which shows survey overlay) if survey not completed
  // Skip for the dashboard itself, admin routes, and if the user dismissed the survey this session
  const surveyDismissedThisSession = (() => {
    try { return sessionStorage.getItem('surveyDismissed') === 'true'; } catch { return false; }
  })();

  if (
    user.personaType === 'legacy_maker' &&
    hasCompletedSurvey === false &&
    !surveyDismissedThisSession &&
    location.pathname !== '/dashboard' &&
    !location.pathname.startsWith('/admin')
  ) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
