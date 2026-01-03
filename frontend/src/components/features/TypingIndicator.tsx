/**
 * TypingIndicator Component
 *
 * Animated "typing" indicator shown while waiting for the clone's response.
 * Displays three bouncing dots in a message bubble to indicate activity.
 *
 * Features:
 * - Three animated dots with staggered timing
 * - Consistent styling with clone message bubbles
 * - Bot avatar for visual consistency
 *
 * @example
 * {isTyping && <TypingIndicator />}
 */

import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { User } from "lucide-react";

export const TypingIndicator = () => {
  return (
    <div className="flex gap-3 mb-4">
      <Avatar className="w-8 h-8">
        <AvatarFallback className="bg-secondary/20">
          <User className="w-4 h-4" />
        </AvatarFallback>
      </Avatar>

      <Card className="p-4 bg-card border-border/50">
        <div className="flex gap-1">
          <div
            className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
            style={{ animationDelay: "0ms" }}
          />
          <div
            className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
            style={{ animationDelay: "150ms" }}
          />
          <div
            className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
            style={{ animationDelay: "300ms" }}
          />
        </div>
      </Card>
    </div>
  );
};
