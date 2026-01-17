/**
 * ChatMessageBubble Component
 *
 * Renders an individual chat message with appropriate styling based on sender (user vs clone).
 * Displays message content, metadata, RAG sources (for clone responses), and feedback controls.
 *
 * Features:
 * - User messages: Right-aligned with purple gradient background
 * - Clone messages: Left-aligned with card styling
 * - Expandable RAG sources (show/hide toggle)
 * - Dual-dimension feedback: Content rating + Style rating
 * - Inline feedback notes that appear after rating
 * - Batch submission with 4-second delay (misclick protection)
 * - Timestamp and performance metrics display
 *
 * @example
 * <ChatMessageBubble
 *   message={chatMessage}
 *   isUser={false}
 *   cloneName="Tiffany"
 *   pendingFeedback={pending}
 *   onContentRating={(rating) => setContentRating(message.id, rating)}
 *   onStyleRating={(rating) => setStyleRating(message.id, rating)}
 *   onContentNote={(text) => setContentFeedbackText(message.id, text)}
 *   onStyleNote={(text) => setStyleFeedbackText(message.id, text)}
 * />
 */

import { ChatMessage, PendingFeedback } from "@/types";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ThumbsUp, ThumbsDown, User, ChevronDown, ChevronUp, Check, X } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useState } from "react";

interface ChatMessageBubbleProps {
  message: ChatMessage;
  isUser: boolean;
  cloneName?: string;
  pendingFeedback?: PendingFeedback;
  isSubmitted?: boolean;
  onContentRating?: (rating: number) => void;
  onStyleRating?: (rating: number) => void;
  onContentNote?: (text: string) => void;
  onStyleNote?: (text: string) => void;
}

export const ChatMessageBubble = ({
  message,
  isUser,
  cloneName = "AI",
  pendingFeedback,
  isSubmitted = false,
  onContentRating,
  onStyleRating,
  onContentNote,
  onStyleNote,
}: ChatMessageBubbleProps) => {
  const [showSources, setShowSources] = useState(false);

  // Determine current feedback state (from pending or saved message)
  const contentRating = pendingFeedback?.contentRating ?? message.feedbackRating ?? null;
  const styleRating = pendingFeedback?.styleRating ?? message.styleRating ?? null;
  const contentNote = pendingFeedback?.contentFeedbackText ?? message.contentFeedbackText ?? "";
  const styleNote = pendingFeedback?.styleFeedbackText ?? message.styleFeedbackText ?? "";

  // Check if feedback has been given (either pending or saved)
  const hasContentRating = contentRating !== null && contentRating !== undefined;
  const hasStyleRating = styleRating !== null && styleRating !== undefined;

  const hasSources = !isUser && message.ragContext && message.ragContext.chunks.length > 0;

  // Handle rating clicks
  const handleContentRating = (rating: number) => {
    if (onContentRating && !isSubmitted) {
      // If clicking the same rating, keep it (don't toggle off)
      onContentRating(rating);
    }
  };

  const handleStyleRating = (rating: number) => {
    if (onStyleRating && !isSubmitted) {
      onStyleRating(rating);
    }
  };

  // Handle note input
  const handleContentNoteChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (onContentNote && !isSubmitted) {
      onContentNote(e.target.value);
    }
  };

  const handleStyleNoteChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (onStyleNote && !isSubmitted) {
      onStyleNote(e.target.value);
    }
  };

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"} mb-4`}>
      {/* Avatar */}
      <Avatar className="w-8 h-8">
        <AvatarFallback className={isUser ? "bg-primary/20" : "bg-secondary/20"}>
          <User className="w-4 h-4" />
        </AvatarFallback>
      </Avatar>

      {/* Message Content */}
      <div className={`flex flex-col max-w-[70%] ${isUser ? "items-end" : "items-start"}`}>
        {/* Message Bubble */}
        <Card
          className={`p-4 ${
            isUser
              ? "bg-gradient-primary text-white"
              : "bg-card border-border/50"
          }`}
        >
          <p className={`text-sm whitespace-pre-wrap ${isUser ? "text-white" : "text-foreground"}`}>
            {message.content}
          </p>
        </Card>

        {/* RAG Sources (Clone messages only) */}
        {hasSources && (
          <div className="mt-2 w-full">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowSources(!showSources)}
              className="text-xs text-muted-foreground h-6 px-2"
            >
              {showSources ? (
                <>
                  <ChevronUp className="w-3 h-3 mr-1" />
                  Hide sources
                </>
              ) : (
                <>
                  <ChevronDown className="w-3 h-3 mr-1" />
                  Show sources ({message.ragContext!.chunks.length})
                </>
              )}
            </Button>

            {showSources && (
              <Card className="mt-1 p-3 bg-muted/50 border-border/30">
                <p className="text-xs font-semibold mb-2 text-muted-foreground">
                  Sources used:
                </p>
                <div className="space-y-2">
                  {message.ragContext!.chunks.map((chunk, idx) => (
                    <div key={idx} className="text-xs">
                      <p className="text-muted-foreground line-clamp-2">
                        "{chunk.content}"
                      </p>
                      <p className="text-xs text-muted-foreground/70 mt-1">
                        {chunk.metadata?.source || "Unknown source"} • {Math.round(chunk.score * 100)}% relevant
                      </p>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        )}

        {/* Metadata & Feedback */}
        <div className="flex flex-col gap-1 mt-1 text-xs text-muted-foreground">
          {/* Timestamp row */}
          <div className="flex items-center gap-2">
            <span>
              {new Date(message.createdAt).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>

            {/* Performance metrics (Clone messages only) */}
            {!isUser && message.responseTimeMs && (
              <span className="text-muted-foreground/70">
                • {(message.responseTimeMs / 1000).toFixed(1)}s
              </span>
            )}
          </div>

          {/* Feedback row (Clone messages only) */}
          {!isUser && (
            <div className="flex items-center gap-3 flex-wrap">
              {/* Content rating section */}
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground/70 mr-1">Accurate?</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className={`h-6 w-6 p-0 ${
                    contentRating === 1
                      ? "bg-primary/20 text-primary"
                      : "hover:bg-primary/10"
                  } ${isSubmitted ? "cursor-default" : ""}`}
                  onClick={() => handleContentRating(1)}
                  disabled={isSubmitted}
                >
                  {isSubmitted && contentRating === 1 ? (
                    <Check className="w-3 h-3" />
                  ) : (
                    <ThumbsUp className="w-3 h-3" />
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className={`h-6 w-6 p-0 ${
                    contentRating === -1
                      ? "bg-destructive/20 text-destructive"
                      : "hover:bg-destructive/10"
                  } ${isSubmitted ? "cursor-default" : ""}`}
                  onClick={() => handleContentRating(-1)}
                  disabled={isSubmitted}
                >
                  {isSubmitted && contentRating === -1 ? (
                    <Check className="w-3 h-3" />
                  ) : (
                    <ThumbsDown className="w-3 h-3" />
                  )}
                </Button>

                {/* Content note input (shows after rating) */}
                {hasContentRating && !isSubmitted && (
                  <Input
                    type="text"
                    placeholder="Add a note..."
                    value={contentNote}
                    onChange={handleContentNoteChange}
                    className="h-6 w-32 text-xs bg-transparent border-0 border-b border-muted rounded-none px-1 focus-visible:ring-0 focus-visible:border-primary"
                  />
                )}
                {hasContentRating && isSubmitted && contentNote && (
                  <span className="text-muted-foreground/70 italic truncate max-w-[120px]">
                    "{contentNote}"
                  </span>
                )}
              </div>

              {/* Style rating section */}
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground/70 mr-1">Sounds like me?</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className={`h-6 w-6 p-0 ${
                    styleRating === 1
                      ? "bg-primary/20 text-primary"
                      : "hover:bg-primary/10"
                  } ${isSubmitted ? "cursor-default" : ""}`}
                  onClick={() => handleStyleRating(1)}
                  disabled={isSubmitted}
                >
                  {isSubmitted && styleRating === 1 ? (
                    <Check className="w-3 h-3" />
                  ) : (
                    <ThumbsUp className="w-3 h-3" />
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className={`h-6 w-6 p-0 ${
                    styleRating === -1
                      ? "bg-destructive/20 text-destructive"
                      : "hover:bg-destructive/10"
                  } ${isSubmitted ? "cursor-default" : ""}`}
                  onClick={() => handleStyleRating(-1)}
                  disabled={isSubmitted}
                >
                  {isSubmitted && styleRating === -1 ? (
                    <Check className="w-3 h-3" />
                  ) : (
                    <ThumbsDown className="w-3 h-3" />
                  )}
                </Button>

                {/* Style note input (shows after rating) */}
                {hasStyleRating && !isSubmitted && (
                  <Input
                    type="text"
                    placeholder="Add a note..."
                    value={styleNote}
                    onChange={handleStyleNoteChange}
                    className="h-6 w-32 text-xs bg-transparent border-0 border-b border-muted rounded-none px-1 focus-visible:ring-0 focus-visible:border-primary"
                  />
                )}
                {hasStyleRating && isSubmitted && styleNote && (
                  <span className="text-muted-foreground/70 italic truncate max-w-[120px]">
                    "{styleNote}"
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
