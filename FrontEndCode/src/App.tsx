
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";

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

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/confirm-signup" element={<ConfirmSignup />} />
            <Route path="/legacy-create-choice" element={<LegacyCreateChoice />} />
            <Route path="/signup-create-legacy" element={<SignUpCreateLegacy />} />
            <Route path="/signup-start-their-legacy" element={<SignUpStartTheirLegacy />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/benefactor-dashboard" element={<BenefactorDashboard />} />
            <Route path="/manage-benefactors" element={<ManageBenefactors />} />
            <Route path="/response-viewer/:makerId" element={<ResponseViewer />} />
            <Route path="/record" element={<RecordResponse />} />
            <Route path="/record-conversation" element={<RecordConversation />} />
            <Route path="/question-themes" element={<QuestionThemes />} />
            <Route path="/test-s3" element={<TestS3 />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
