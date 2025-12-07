import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useUser } from "@clerk/clerk-react";
import Header from "@/components/layout/Header";
import { ActivityTimeline } from "@/components/features/ActivityTimeline";
import { ActivityFilters, ActivityFilters as ActivityFiltersType } from "@/components/features/ActivityFilters";
import { apiClient } from "@/api/client";
import { CloneAction, Conversation } from "@/types";
import { Loader2 } from "lucide-react";

const Activity = () => {
  const { user } = useUser();
  const [filters, setFilters] = useState<ActivityFiltersType>({});
  const [searchQuery, setSearchQuery] = useState("");

  const { data: actionsData, isLoading: actionsLoading, isError: actionsError } = useQuery<{
    items: CloneAction[];
    total: number;
    page: number;
  }>({
    queryKey: ["actions", filters],
    queryFn: () => apiClient.activity.actions(filters),
    retry: 1,
    refetchOnWindowFocus: false,
  });

  const { data: conversationsData, isLoading: conversationsLoading, isError: conversationsError } = useQuery<{
    items: Conversation[];
    total: number;
    page: number;
  }>({
    queryKey: ["conversations", filters],
    queryFn: () => apiClient.activity.conversations(filters),
    retry: 1,
    refetchOnWindowFocus: false,
  });

  const { data: searchResults, isLoading: searchLoading } = useQuery<{
    actions: CloneAction[];
    conversations: Conversation[];
  }>({
    queryKey: ["activitySearch", searchQuery],
    queryFn: () => apiClient.activity.search(searchQuery),
    enabled: !!searchQuery,
  });

  const handleFiltersChange = (newFilters: ActivityFiltersType) => {
    setFilters(newFilters);
    setSearchQuery(""); // Clear search when filters change
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setFilters({}); // Clear filters when searching
  };

  const actions = searchQuery
    ? searchResults?.actions || []
    : (actionsError ? [] : actionsData?.items || []);

  const conversations = searchQuery
    ? searchResults?.conversations || []
    : (conversationsError ? [] : conversationsData?.items || []);

  const isLoading = actionsLoading || conversationsLoading || (searchQuery && searchLoading);

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="container mx-auto px-6 py-24">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Header */}
          <div>
            <h1 className="text-4xl md:text-5xl font-bold mb-4">
              Activity & Interactions
            </h1>
            <p className="text-xl text-muted-foreground">
              View what your clone has done and conversations it has had
            </p>
            {(actionsError || conversationsError) && (
              <div className="mt-4 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                <p className="text-sm text-yellow-600 dark:text-yellow-400">
                  ⚠️ Unable to connect to the backend. Activity data cannot be loaded.
                </p>
              </div>
            )}
          </div>

          {/* Filters */}
          <ActivityFilters onFiltersChange={handleFiltersChange} onSearch={handleSearch} />

          {/* Activity Timeline */}
          <ActivityTimeline
            actions={actions}
            conversations={conversations}
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  );
};

export default Activity;

