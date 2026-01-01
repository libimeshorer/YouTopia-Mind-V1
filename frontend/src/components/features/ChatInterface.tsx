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
  const scrollRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Create or resume session
  const { data: session, isLoading: sessionLoading } = useQuery<ChatSession>({
    queryKey: ["chatSession", cloneId],
    queryFn: async () => {
      const newSession = await apiClient.chat.createSession(cloneId);
      setSessionId(newSession.id);
      return newSession;
    },
  });

  // Load messages when session is ready
  useEffect(() => {
    if (sessionId) {
      apiClient.chat.getMessages(sessionId).then((loadedMessages) => {
        setMessages(loadedMessages);
      });
    }
  }, [sessionId]);

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: (content: string) => {
      if (!sessionId) throw new Error("No session available");
      return apiClient.chat.sendMessage(sessionId, { content });
    },
    onMutate: () => {
      setIsTyping(true);
    },
    onSuccess: (data) => {
      // Add both messages to state
      setMessages((prev) => [...prev, data.userMessage, data.cloneMessage]);
      setIsTyping(false);
    },
    onError: (error) => {
      setIsTyping(false);
      toast({
        title: "Error",
        description: "Failed to send message. Please try again.",
        variant: "destructive",
      });
      console.error("Send message error:", error);
    },
  });

  // Submit feedback mutation
  const feedbackMutation = useMutation({
    mutationFn: ({ messageId, rating }: { messageId: string; rating: number }) =>
      apiClient.chat.submitFeedback(messageId, rating),
    onSuccess: (_, variables) => {
      // Update message in state
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === variables.messageId
            ? { ...msg, feedbackRating: variables.rating }
            : msg
        )
      );
      toast({
        title: "Feedback submitted",
        description: "Thank you for your feedback!",
      });
    },
  });

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isTyping]);

  const handleSend = (content: string) => {
    sendMessageMutation.mutate(content);
  };

  const handleFeedback = (messageId: string, rating: number) => {
    feedbackMutation.mutate({ messageId, rating });
  };

  const handleNewConversation = () => {
    // Clear messages and create new session
    setMessages([]);
    setSessionId(undefined);
    queryClient.invalidateQueries({ queryKey: ["chatSession", cloneId] });
    toast({
      title: "New conversation started",
      description: "Your previous conversation has been saved.",
    });
  };

  if (sessionLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border/50">
        <div>
          <h2 className="text-xl font-semibold">{cloneName}</h2>
          <p className="text-sm text-muted-foreground">AI Assistant</p>
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
        {messages.length === 0 && !isTyping ? (
          <Card className="p-8 text-center border-border/50 bg-gradient-secondary">
            <h3 className="text-lg font-semibold mb-2">Start a conversation</h3>
            <p className="text-sm text-muted-foreground">
              Ask me anything! I'm here to help based on your knowledge and experience.
            </p>
          </Card>
        ) : (
          <>
            {messages.map((message) => (
              <ChatMessageBubble
                key={message.id}
                message={message}
                isUser={message.role === "external_user"}
                cloneName={cloneName}
                onFeedback={
                  message.role === "clone"
                    ? (rating) => handleFeedback(message.id, rating)
                    : undefined
                }
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
