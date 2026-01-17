/**
 * ChatInterface Component
 *
 * Main chat container that manages the conversational interface between the clone owner and their AI clone.
 * Handles session management, message state, and real-time chat interactions.
 *
 * Features:
 * - Auto-creates/resumes single persistent session per clone owner
 * - "New Conversation" button to start fresh sessions
 * - Real-time message sending with typing indicators
 * - Feedback submission (thumbs up/down)
 * - RAG source display
 * - Error handling with user-friendly toasts
 *
 * @example
 * <ChatInterface cloneId="abc-123" cloneName="Tiffany" />
 */

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ChatMessage, ChatSession } from "@/types";
import { apiClient } from "@/api/client";
import { ChatMessageBubble } from "./ChatMessageBubble";
import { ChatInput } from "./ChatInput";
import { TypingIndicator } from "./TypingIndicator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Loader2, Plus } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { usePendingFeedback } from "@/hooks/usePendingFeedback";

interface ChatInterfaceProps {
  cloneId: string;
  cloneName?: string;
}

export const ChatInterface = ({
  cloneId,
  cloneName = "AI",
}: ChatInterfaceProps) => {
  const [sessionId, setSessionId] = useState<number | undefined>(undefined);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Pending feedback hook for batch submission with 4-second delay
  const {
    setContentRating,
    setStyleRating,
    setContentFeedbackText,
    setStyleFeedbackText,
    getPendingFeedback,
    isSubmitted,
  } = usePendingFeedback();

  // Create or resume session
  const { data: session, isLoading: sessionLoading, error: sessionError, isError: sessionHasError } = useQuery<ChatSession>({
    queryKey: ["chatSession", cloneId],
    queryFn: async () => {
      console.log("🔵 Creating/resuming session for cloneId:", cloneId);
      const newSession = await apiClient.chat.createSession(cloneId);
      console.log("✅ Session created/resumed:", newSession);
      return newSession;
    },
    retry: 2, // Retry failed requests twice
    onError: (error) => {
      console.error("❌ Session creation failed:", error);
      toast({
        title: "Failed to create chat session",
        description: error instanceof Error ? error.message : "Could not connect to chat service. Please refresh the page.",
        variant: "destructive",
      });
    },
  });

  // FIX BUG #1: Extract sessionId from query result (no side effects in queryFn)
  useEffect(() => {
    console.log("🔍 Session data changed:", session);
    if (session?.id) {
      console.log("✅ Setting sessionId:", session.id);
      setSessionId(session.id);
    } else if (session) {
      console.error("⚠️ Session exists but has no id:", session);
    }
  }, [session]);

  // FIX BUG #3, #4, #5: Load messages with error handling, loading state, and cleanup
  useEffect(() => {
    if (!sessionId) return;

    let isMounted = true; // Cleanup flag
    setIsLoadingMessages(true);

    apiClient.chat
      .getMessages(sessionId)
      .then((loadedMessages) => {
        if (isMounted) {
          setMessages(loadedMessages);
          setIsLoadingMessages(false);
        }
      })
      .catch((error) => {
        if (isMounted) {
          console.error("Failed to load messages:", error);
          setIsLoadingMessages(false);
          toast({
            title: "Error loading messages",
            description: "Could not load conversation history.",
            variant: "destructive",
          });
        }
      });

    // Cleanup: prevent state updates after unmount
    return () => {
      isMounted = false;
    };
  }, [sessionId, toast]);

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: (content: string) => {
      if (!sessionId) throw new Error("No session available");
      return apiClient.chat.sendMessage(sessionId, { content });
    },
    onMutate: (content: string) => {
      // Optimistic update: Show user message immediately
      const optimisticUserMessage: ChatMessage = {
        id: `temp-user-${Date.now()}`,
        sessionId: sessionId!,
        role: 'external_user',
        content: content,
        createdAt: new Date().toISOString(),
        externalUserName: 'You',
      };

      setMessages((prev) => [...prev, optimisticUserMessage]);
      setIsTyping(true);
    },
    onSuccess: (data) => {
      // Update optimistic message with server data but keep client timestamp
      setMessages((prev) => {
        const updated = prev.map(msg =>
          msg.id.startsWith('temp-user-')
            ? { ...data.userMessage, createdAt: msg.createdAt }
            : msg
        );
        // Add the clone response
        return [...updated, data.cloneMessage];
      });
      setIsTyping(false);
    },
    onError: (error) => {
      // Remove optimistic message on error
      setMessages((prev) => prev.filter(msg => !msg.id.startsWith('temp-user-')));
      setIsTyping(false);
      toast({
        title: "Error",
        description: "Failed to send message. Please try again.",
        variant: "destructive",
      });
      console.error("Send message error:", error);
    },
  });

  // Feedback is now handled by usePendingFeedback hook with batch submission

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isTyping]);

  const handleSend = (content: string) => {
    sendMessageMutation.mutate(content);
  };

  const handleNewConversation = async () => {
    try {
      // Create new session (closes existing active sessions on backend)
      const newSession = await apiClient.chat.createNewSession();
      setMessages([]);
      setSessionId(newSession.id);
      queryClient.setQueryData(["chatSession", cloneId], newSession);
      toast({
        title: "New conversation started",
        description: "Your previous conversation has been saved.",
      });
    } catch (error) {
      console.error("Error creating new conversation:", error);
      toast({
        title: "Error",
        description: "Failed to start new conversation. Please try again.",
        variant: "destructive",
      });
    }
  };

  // Debug logging for disabled state
  useEffect(() => {
    console.log("💬 Chat input state:", {
      sessionId,
      isPending: sendMessageMutation.isPending,
      isTyping,
      disabled: sendMessageMutation.isPending || isTyping || !sessionId,
    });
  }, [sessionId, sendMessageMutation.isPending, isTyping]);

  if (sessionLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        <p className="ml-2 text-sm text-muted-foreground">Loading chat session...</p>
      </div>
    );
  }

  // Show error state if session creation failed
  if (sessionHasError) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="p-8 max-w-md text-center border-destructive">
          <h3 className="text-lg font-semibold mb-2 text-destructive">Failed to Connect</h3>
          <p className="text-sm text-muted-foreground mb-4">
            {sessionError instanceof Error ? sessionError.message : "Could not establish chat session. Please try refreshing the page."}
          </p>
          <Button onClick={() => queryClient.invalidateQueries({ queryKey: ["chatSession", cloneId] })}>
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border/50">
        <div>
          <h2 className="text-xl font-semibold">{cloneName}</h2>
          <p className="text-sm text-muted-foreground">AI Clone</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleNewConversation}
          className="gap-2"
        >
          <Plus className="w-4 h-4" />
          New Conversation
        </Button>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4">
        {isLoadingMessages ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : messages.length === 0 && !isTyping ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <h3 className="text-2xl font-semibold mb-3 bg-gradient-to-r from-primary to-purple-600 bg-clip-text text-transparent">
              Start a conversation
            </h3>
            <p className="text-muted-foreground max-w-md">
              How can I help? Happy to reply based on my experience and knowledge.
            </p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <ChatMessageBubble
                key={message.id}
                message={message}
                isUser={message.role === "external_user"}
                cloneName={cloneName}
                pendingFeedback={getPendingFeedback(message.id)}
                isSubmitted={isSubmitted(message.id)}
                onContentRating={(rating) => setContentRating(message.id, rating)}
                onStyleRating={(rating) => setStyleRating(message.id, rating)}
                onContentNote={(text) => setContentFeedbackText(message.id, text)}
                onStyleNote={(text) => setStyleFeedbackText(message.id, text)}
              />
            ))}
            {isTyping && <TypingIndicator />}
            <div ref={scrollRef} />
          </>
        )}
      </ScrollArea>

      {/* Input */}
      <ChatInput
        onSend={handleSend}
        disabled={sendMessageMutation.isPending || isTyping || !sessionId}
        placeholder="Type your message..."
      />
    </div>
  );
};
