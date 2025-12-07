import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search, X } from "lucide-react";

interface ActivityFiltersProps {
  onFiltersChange: (filters: ActivityFilters) => void;
  onSearch: (query: string) => void;
}

export interface ActivityFilters {
  actionType?: string;
  platform?: string;
  participant?: string;
  startDate?: string;
  endDate?: string;
}

export const ActivityFilters = ({ onFiltersChange, onSearch }: ActivityFiltersProps) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState<ActivityFilters>({});

  const handleFilterChange = (key: keyof ActivityFilters, value: string) => {
    const newFilters = { ...filters, [key]: value || undefined };
    setFilters(newFilters);
    onFiltersChange(newFilters);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(searchQuery);
  };

  const clearFilters = () => {
    setFilters({});
    setSearchQuery("");
    onFiltersChange({});
    onSearch("");
  };

  const hasActiveFilters = Object.values(filters).some((v) => v) || searchQuery;

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          {/* Search */}
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search actions and conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Button type="submit" variant="outline">
              Search
            </Button>
            {hasActiveFilters && (
              <Button type="button" variant="ghost" onClick={clearFilters}>
                <X className="w-4 h-4 mr-2" />
                Clear
              </Button>
            )}
          </form>

          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Select
              value={filters.actionType || ""}
              onValueChange={(value) => handleFilterChange("actionType", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Action Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Types</SelectItem>
                <SelectItem value="task">Task</SelectItem>
                <SelectItem value="decision">Decision</SelectItem>
                <SelectItem value="recommendation">Recommendation</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={filters.platform || ""}
              onValueChange={(value) => handleFilterChange("platform", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Platform" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Platforms</SelectItem>
                <SelectItem value="slack">Slack</SelectItem>
                <SelectItem value="email">Email</SelectItem>
                <SelectItem value="linkedin">LinkedIn</SelectItem>
                <SelectItem value="x">X (Twitter)</SelectItem>
                <SelectItem value="granola">Granola</SelectItem>
                <SelectItem value="fathom">Fathom</SelectItem>
              </SelectContent>
            </Select>

            <Input
              type="date"
              placeholder="Start Date"
              value={filters.startDate || ""}
              onChange={(e) => handleFilterChange("startDate", e.target.value)}
            />

            <Input
              type="date"
              placeholder="End Date"
              value={filters.endDate || ""}
              onChange={(e) => handleFilterChange("endDate", e.target.value)}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

