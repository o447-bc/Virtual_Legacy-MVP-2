import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext-simple";
import { QuestionsProvider } from "./contexts/QuestionsContext";

// Pages
import Home from "./pages/Home-fixed";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <QuestionsProvider>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="*" element={<div style={{padding: '20px'}}>404 - Page not found</div>} />
            </Routes>
          </QuestionsProvider>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;