import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { SubscriptionProvider } from "./contexts/SubscriptionContext";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminGate from "./components/AdminGate";
import AdminLayout from "./components/AdminLayout";

// Pages
import Home from "./pages/Home";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import ConfirmSignup from "./pages/ConfirmSignup";
import LegacyCreateChoice from "./pages/LegacyCreateChoice";
import SignUpCreateLegacy from "./pages/SignUpCreateLegacy";
import SignUpStartTheirLegacy from "./pages/SignUpStartTheirLegacy";
import Dashboard from "./pages/Dashboard";
import BenefactorDashboard from "./pages/BenefactorDashboard";
import ManageBenefactors from "./pages/ManageBenefactors";
import ResponseViewer from "./pages/ResponseViewer";
import RecordResponse from "./pages/RecordResponse";
import RecordConversation from "./pages/RecordConversation";
import QuestionThemes from "./pages/QuestionThemes";
import LifeStoryReflections from "./pages/LifeStoryReflections";
import LifeEvents from "./pages/LifeEvents";
import PersonalInsights from "./pages/PersonalInsights";
import NotFound from "./pages/NotFound";
import PricingPage from "./pages/PricingPage";
import { TestS3 } from "./pages/TestS3";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import YourData from "./pages/YourData";

// Admin pages
import AdminDashboard from "./pages/admin/AdminDashboard";
import QuestionBrowse from "./pages/admin/QuestionBrowse";
import QuestionCreate from "./pages/admin/QuestionCreate";
import BatchImport from "./pages/admin/BatchImport";
import AssignmentSimulator from "./pages/admin/AssignmentSimulator";
import CoverageReport from "./pages/admin/CoverageReport";
import ThemeSettings from "./pages/admin/ThemeSettings";
import ExportView from "./pages/admin/ExportView";
import AssessmentManager from "./pages/admin/AssessmentManager";
import SystemSettings from "./pages/admin/SystemSettings";
import AdminFeedbackPage from "./pages/admin/AdminFeedbackPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <SubscriptionProvider>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/confirm-signup" element={<ConfirmSignup />} />
            <Route path="/legacy-create-choice" element={<LegacyCreateChoice />} />
            <Route path="/signup-create-legacy" element={<SignUpCreateLegacy />} />
            <Route path="/signup-start-their-legacy" element={<SignUpStartTheirLegacy />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/pricing" element={<PricingPage />} />

            {/* Protected routes — require authentication */}
            <Route path="/dashboard" element={<ProtectedRoute requiredPersona="legacy_maker"><Dashboard /></ProtectedRoute>} />
            <Route path="/life-story-reflections" element={<ProtectedRoute requiredPersona="legacy_maker"><LifeStoryReflections /></ProtectedRoute>} />
            <Route path="/life-events" element={<ProtectedRoute requiredPersona="legacy_maker"><LifeEvents /></ProtectedRoute>} />
            <Route path="/personal-insights" element={<ProtectedRoute requiredPersona="legacy_maker"><PersonalInsights /></ProtectedRoute>} />
            <Route path="/benefactor-dashboard" element={<ProtectedRoute requiredPersona="legacy_benefactor"><BenefactorDashboard /></ProtectedRoute>} />
            <Route path="/manage-benefactors" element={<ProtectedRoute requiredPersona="legacy_maker"><ManageBenefactors /></ProtectedRoute>} />
            <Route path="/response-viewer/:makerId" element={<ProtectedRoute><ResponseViewer /></ProtectedRoute>} />
            <Route path="/record" element={<ProtectedRoute requiredPersona="legacy_maker"><RecordResponse /></ProtectedRoute>} />
            <Route path="/record-conversation" element={<ProtectedRoute requiredPersona="legacy_maker"><RecordConversation /></ProtectedRoute>} />
            <Route path="/question-themes" element={<ProtectedRoute requiredPersona="legacy_maker"><QuestionThemes /></ProtectedRoute>} />
            <Route path="/your-data" element={<ProtectedRoute><YourData /></ProtectedRoute>} />
            <Route path="/test-s3" element={<ProtectedRoute><TestS3 /></ProtectedRoute>} />

            {/* Admin routes — require SoulReelAdmins Cognito group */}
            <Route path="/admin" element={<AdminGate><AdminLayout /></AdminGate>}>
              <Route index element={<AdminDashboard />} />
              <Route path="questions" element={<QuestionBrowse />} />
              <Route path="create" element={<QuestionCreate />} />
              <Route path="batch" element={<BatchImport />} />
              <Route path="simulate" element={<AssignmentSimulator />} />
              <Route path="coverage" element={<CoverageReport />} />
              <Route path="themes" element={<ThemeSettings />} />
              <Route path="export" element={<ExportView />} />
              <Route path="assessments" element={<AssessmentManager />} />
              <Route path="feedback" element={<AdminFeedbackPage />} />
              <Route path="settings" element={<SystemSettings />} />
            </Route>

            <Route path="*" element={<NotFound />} />
          </Routes>
          </SubscriptionProvider>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
