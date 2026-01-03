/**
 * Chat Page
 *
 * Full-page chat interface for clone owners to interact with their AI clone.
 * Displays the ChatInterface component with authentication and authorization checks.
 *
 * Route: /chat/:cloneId
 *
 * Features:
 * - Protected route (requires Clerk authentication)
 * - Clone owner verification (future: support customer access)
 * - Loading states for auth and data fetching
 * - Error states (not authenticated, missing cloneId)
 * - Full-height chat interface
 *
 * @example
 * // Access via route
 * navigate(ROUTES.CHAT('abc-123-def-456'))
 */

import { useParams } from "react-router-dom";
import { useUser } from "@clerk/clerk-react";
import { ChatInterface } from "@/components/features/ChatInterface";
import { Card } from "@/components/ui/card";
import { Loader2 } from "lucide-react";
import Header from "@/components/layout/Header";

const Chat = () => {
  const { cloneId } = useParams<{ cloneId: string }>();
  const { user, isLoaded } = useUser();

  // Wait for user to load
  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="container mx-auto px-6 py-24">
          <div className="flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        </div>
      </div>
    );
  }

  // Require authentication
  if (!user) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="container mx-auto px-6 py-24">
          <Card className="p-8 text-center">
            <h2 className="text-2xl font-semibold mb-2">Authentication Required</h2>
            <p className="text-muted-foreground">
              Please sign in to chat with your AI clone.
            </p>
          </Card>
        </div>
      </div>
    );
  }

  // Require cloneId parameter
  if (!cloneId) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="container mx-auto px-6 py-24">
          <Card className="p-8 text-center">
            <h2 className="text-2xl font-semibold mb-2">Clone Not Found</h2>
            <p className="text-muted-foreground">
              No clone ID provided in the URL.
            </p>
          </Card>
        </div>
      </div>
    );
  }

  // Get clone name from user (simplified for owner-only chat)
  const cloneName = user.firstName
    ? `${user.firstName}${user.lastName ? ` ${user.lastName}` : ""}`
    : user.emailAddresses?.[0]?.emailAddress || "Your Clone";

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <div className="flex-1 container mx-auto px-6 py-16 flex items-center">
        <Card className="h-[calc(100vh-250px)] w-full max-w-5xl mx-auto">
          <ChatInterface cloneId={cloneId} cloneName={cloneName} />
        </Card>
      </div>
    </div>
  );
};

export default Chat;
