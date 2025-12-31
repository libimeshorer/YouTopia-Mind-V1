import { ChatMessage } from "@/types";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ThumbsUp, ThumbsDown, User, Bot, ChevronDown, ChevronUp } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useState } from "react";

interface ChatMessageBubbleProps {
  message: ChatMessage;
  isUser: boolean;
  cloneName?: string;
  onFeedback?: (rating: number) => void;
}

export const ChatMessageBubble = ({
  message,
  isUser,
  cloneName = "AI",
  onFeedback,
}: ChatMessageBubbleProps) => {
  const [feedbackGiven, setFeedbackGiven] = useState(
    message.feedbackRating !== undefined && message.feedbackRating !== null
  );
  const [showSources, setShowSources] = useState(false);

  const handleFeedback = (rating: number) => {
    if (onFeedback) {
      onFeedback(rating);
      setFeedbackGiven(true);
    }
  };

  const hasSources = !isUser && message.ragContext && message.ragContext.chunks.length > 0;

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"} mb-4`}>
      {/* Avatar */}
      <Avatar className="w-8 h-8">
        <AvatarFallback className={isUser ? "bg-primary/20" : "bg-secondary/20"}>
          {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
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
        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
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

          {/* Feedback buttons (Clone messages only) */}
          {!isUser && onFeedback && !feedbackGiven && (
            <div className="flex gap-1 ml-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 hover:bg-primary/10"
                onClick={() => handleFeedback(1)}
              >
                <ThumbsUp className="w-3 h-3" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 hover:bg-destructive/10"
                onClick={() => handleFeedback(-1)}
              >
                <ThumbsDown className="w-3 h-3" />
              </Button>
            </div>
          )}

          {/* Feedback indicator */}
          {feedbackGiven && message.feedbackRating !== null && (
            <span className="text-xs ml-2">
              {message.feedbackRating === 1 ? "👍" : "👎"}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
