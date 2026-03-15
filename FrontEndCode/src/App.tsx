import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";

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
import NotFound from "./pages/NotFound";
import { TestS3 } from "./pages/TestS3";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";

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

            {/* Protected routes — require authentication */}
            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/benefactor-dashboard" element={<ProtectedRoute requiredPersona="legacy_benefactor"><BenefactorDashboard /></ProtectedRoute>} />
            <Route path="/manage-benefactors" element={<ProtectedRoute><ManageBenefactors /></ProtectedRoute>} />
            <Route path="/response-viewer/:makerId" element={<ProtectedRoute><ResponseViewer /></ProtectedRoute>} />
            <Route path="/record" element={<ProtectedRoute><RecordResponse /></ProtectedRoute>} />
            <Route path="/record-conversation" element={<ProtectedRoute><RecordConversation /></ProtectedRoute>} />
            <Route path="/question-themes" element={<ProtectedRoute><QuestionThemes /></ProtectedRoute>} />
            <Route path="/test-s3" element={<ProtectedRoute><TestS3 /></ProtectedRoute>} />

            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
