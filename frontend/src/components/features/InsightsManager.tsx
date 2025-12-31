import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Mic, Save, Edit, Trash2, Play, Search, Loader2, Lock, Sparkles } from "lucide-react";
import { apiClient } from "@/api/client";
import { Insight } from "@/types";
import { useToast } from "@/hooks/use-toast";
import { VoiceRecorder } from "./VoiceRecorder";
import { useUser } from "@clerk/clerk-react";

export const InsightsManager = () => {
  // TODO: Change ENABLE_SEARCH to true to make search active. Also needs to be fixed in backend:
  // - Fix filteredInsights logic to show empty array when searchQuery exists but searchMutation.data is undefined
  // - Add loading state during search
  // - Add error handling for search failures
  const ENABLE_SEARCH = false;
  
  const [textInput, setTextInput] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showUpgradeDialog, setShowUpgradeDialog] = useState(false);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { user } = useUser();

  // TODO: Replace with actual premium check from your backend API
  // This could be: user?.publicMetadata?.subscriptionTier === 'premium'
  // or fetched from your API endpoint (e.g., apiClient.user.subscription())
  // For now, checking Clerk's publicMetadata as a placeholder
  const isPremium = (user?.publicMetadata?.isPremium === true) || 
                    (user?.publicMetadata?.subscriptionTier === 'premium') ||
                    false; // Default to false for now

  const { data: insights = [], isLoading } = useQuery<Insight[]>({
    queryKey: ["insights"],
    queryFn: () => apiClient.insights.list(),
  });

  const createMutation = useMutation({
    mutationFn: (content: string) => apiClient.insights.create(content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["insights"] });
      setTextInput("");
      toast({
        title: "Insight Saved",
        description: "Your insight has been saved successfully",
      });
    },
    onError: () => {
      toast({
        title: "Save Failed",
        description: "Failed to save insight",
        variant: "destructive",
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, content }: { id: string; content: string }) =>
      apiClient.insights.update(id, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["insights"] });
      setEditingId(null);
      toast({
        title: "Insight Updated",
        description: "Your insight has been updated successfully",
      });
    },
    onError: () => {
      toast({
        title: "Update Failed",
        description: "Failed to update insight",
        variant: "destructive",
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.insights.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["insights"] });
      toast({
        title: "Insight Deleted",
        description: "Insight has been removed",
      });
    },
    onError: () => {
      toast({
        title: "Delete Failed",
        description: "Failed to delete insight",
        variant: "destructive",
      });
    },
  });

  const searchMutation = useMutation({
    mutationFn: (query: string) => apiClient.insights.search(query),
  });

  const handleSaveText = () => {
    if (textInput.trim()) {
      createMutation.mutate(textInput.trim());
    }
  };

  const handleSaveVoice = (transcription: string) => {
    if (transcription.trim()) {
      createMutation.mutate(transcription.trim());
    }
  };

  const handleEdit = (insight: Insight) => {
    setEditingId(insight.id);
    setTextInput(insight.content);
  };

  const handleUpdate = () => {
    if (editingId && textInput.trim()) {
      updateMutation.mutate({ id: editingId, content: textInput.trim() });
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setTextInput("");
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      searchMutation.mutate(searchQuery);
    }
  };

  const filteredInsights = searchQuery
    ? searchMutation.data || insights
    : insights;

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="space-y-6">
      {/* Voice Recording - Premium Feature */}
      <Card className="relative">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mic className="w-5 h-5" />
            Record Voice Insight
            {!isPremium && (
              <Badge variant="secondary" className="ml-auto">
                <Sparkles className="w-3 h-3 mr-1" />
                Premium
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="relative">
          {!isPremium ? (
            // Premium Locked State - Blurred Overlay
            <div className="relative">
              {/* Blurred background */}
              <div className="blur-sm pointer-events-none select-none opacity-50">
                <VoiceRecorder
                  onTranscriptionComplete={() => {}}
                  onSave={() => {}}
                />
              </div>
              
              {/* Overlay content */}
              <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm rounded-lg">
                <div className="text-center space-y-4 p-6 max-w-sm">
                  <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                    <Lock className="w-8 h-8 text-primary" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-lg font-semibold">Voice Insights are Premium</h3>
                    <p className="text-sm text-muted-foreground">
                      Upgrade to unlock voice recording and instant transcription for your insights.
                    </p>
                  </div>
                  <Dialog open={showUpgradeDialog} onOpenChange={setShowUpgradeDialog}>
                    <DialogTrigger asChild>
                      <Button className="bg-gradient-primary hover:shadow-glow">
                        <Sparkles className="w-4 h-4 mr-2" />
                        Upgrade to Premium
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Upgrade to Premium</DialogTitle>
                        <DialogDescription>
                          Unlock voice insights and other premium features.
                        </DialogDescription>
                      </DialogHeader>
                      <div className="space-y-4 py-4">
                        <div className="space-y-2">
                          <h4 className="font-semibold">Premium Features:</h4>
                          <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                            <li>Voice insight recording</li>
                            <li>Instant transcription</li>
                            <li>Advanced AI features</li>
                            <li>Priority support</li>
                          </ul>
                        </div>
                      </div>
                      <DialogFooter>
                        <Button variant="outline" onClick={() => setShowUpgradeDialog(false)}>
                          Maybe Later
                        </Button>
                        <Button 
                          onClick={() => {
                            // TODO: Navigate to your payment/subscription page
                            // navigate('/upgrade') or open Stripe checkout
                            toast({
                              title: "Redirecting to upgrade...",
                              description: "You'll be redirected to complete your upgrade.",
                            });
                            setShowUpgradeDialog(false);
                          }}
                        >
                          Upgrade Now
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </div>
              </div>
            </div>
          ) : (
            // Premium User - Full Access
            <VoiceRecorder
              onTranscriptionComplete={(transcription) => {
                setTextInput(transcription);
              }}
              onSave={handleSaveVoice}
            />
          )}
        </CardContent>
      </Card>

      {/* Text Input */}
      <Card>
        <CardHeader>
          <CardTitle>Add Text Insight</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            placeholder="Type your insight here..."
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            rows={4}
          />
          <div className="flex gap-2">
            {editingId ? (
              <>
                <Button onClick={handleUpdate} disabled={updateMutation.isPending}>
                  {updateMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Updating...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4 mr-2" />
                      Update
                    </>
                  )}
                </Button>
                <Button variant="outline" onClick={handleCancelEdit}>
                  Cancel
                </Button>
              </>
            ) : (
              <Button onClick={handleSaveText} disabled={createMutation.isPending || !textInput.trim()}>
                {createMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    Save Insight
                  </>
                )}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Search */}
      {ENABLE_SEARCH && (
        <Card>
          <CardContent className="pt-6">
            <form onSubmit={handleSearch} className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  type="text"
                  placeholder="Search insights..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Button type="submit" variant="outline">
                Search
              </Button>
              {searchQuery && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setSearchQuery("");
                    searchMutation.reset();
                  }}
                >
                  Clear
                </Button>
              )}
            </form>
          </CardContent>
        </Card>
      )}

      {/* Insights List */}
      <Card>
        <CardHeader>
          <CardTitle>Saved Insights</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : filteredInsights.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {searchQuery ? "No insights found" : "No insights recorded yet"}
            </div>
          ) : (
            <div className="space-y-4">
              {filteredInsights.map((insight) => (
                <div
                  key={insight.id}
                  className="p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2">
                        {insight.type === "voice" ? (
                          <Mic className="w-4 h-4 text-muted-foreground" />
                        ) : (
                          <span className="text-xs px-2 py-1 bg-muted rounded">Text</span>
                        )}
                        <span className="text-xs text-muted-foreground">
                          {formatDate(insight.createdAt)}
                        </span>
                      </div>
                      {editingId === insight.id ? (
                        <Textarea
                          value={textInput}
                          onChange={(e) => setTextInput(e.target.value)}
                          rows={3}
                        />
                      ) : (
                        <p className="text-sm">{insight.content}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {insight.type === "voice" && insight.audioUrl && (
                        <Button variant="ghost" size="icon">
                          <Play className="w-4 h-4" />
                        </Button>
                      )}
                      {editingId !== insight.id && (
                        <>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(insight)}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => deleteMutation.mutate(insight.id)}
                            disabled={deleteMutation.isPending}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

