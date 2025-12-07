import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ClerkProvider } from "@clerk/clerk-react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { clerkConfig } from "@/lib/clerk";
import Index from "./pages/Index";
import Process from "./pages/Process";
import Demo from "./pages/Demo";
import SignIn from "./pages/SignIn";
import SignUp from "./pages/SignUp";
import Dashboard from "./pages/Dashboard";
import Training from "./pages/Training";
import Activity from "./pages/Activity";
import NotFound from "./pages/NotFound";
import ProtectedRoute from "./components/layout/ProtectedRoute";

const queryClient = new QueryClient();

// Main app content (without ClerkProvider wrapper)
const AppContent = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/process" element={<Process />} />
          <Route path="/demo" element={<Demo />} />
          <Route path="/sign-in" element={<SignIn />} />
          <Route path="/sign-up" element={<SignUp />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/training"
            element={
              <ProtectedRoute>
                <Training />
              </ProtectedRoute>
            }
          />
          <Route
            path="/activity"
            element={
              <ProtectedRoute>
                <Activity />
              </ProtectedRoute>
            }
          />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

const App = () => {
  // Only wrap with ClerkProvider if Clerk is properly configured
  // This prevents the app from crashing when publishableKey is missing
  if (clerkConfig.isConfigured && clerkConfig.publishableKey) {
    return (
      <ClerkProvider publishableKey={clerkConfig.publishableKey}>
        <AppContent />
      </ClerkProvider>
    );
  }

  // Render app without ClerkProvider when not configured
  // The Header component will show fallback Sign In button
  console.warn(
    "[App] Clerk not configured. App will run without authentication features."
  );
  return <AppContent />;
};

export default App;
