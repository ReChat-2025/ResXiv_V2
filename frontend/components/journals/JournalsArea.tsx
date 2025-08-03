"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Icon } from "@/components/ui/icon";
import { appConfig } from "@/lib/config/app-config";
import { mockJournals, type Journal, formatTimestamp } from "@/lib/config/data-config";
import SearchInput from "@/components/ui/SearchInput";

interface JournalsAreaProps {
  journals?: Journal[];
  onCreateJournal?: () => void;
  onSearchChange?: (query: string) => void;
  onSortChange?: (sort: string) => void;
  onFilterChange?: (filter: string) => void;
  onJournalClick?: (journalId: string) => void;
  className?: string;
  title?: string;
  showCreateButton?: boolean;
}

interface SortOption {
  id: string;
  label: string;
}

interface FilterOption {
  id: string;
  label: string;
  value: string;
}

export function JournalsArea({
  journals,
  onCreateJournal,
  onSearchChange,
  onSortChange,
  onFilterChange,
  onJournalClick,
  className = "",
  title = "All Journals",
  showCreateButton = true
}: JournalsAreaProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSort, setSelectedSort] = useState("Recent");
  const [selectedFilter, setSelectedFilter] = useState("All");

  // Get configuration values
  const config = appConfig;
  const displayJournals = journals ?? mockJournals;

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    onSearchChange?.(value);
  };

  const handleSortChange = (sort: string) => {
    setSelectedSort(sort);
    onSortChange?.(sort);
  };

  const handleFilterChange = (filter: string) => {
    setSelectedFilter(filter);
    onFilterChange?.(filter);
  };

  const handleJournalClick = (journalId: string) => {
    onJournalClick?.(journalId);
  };

  const handleCreateJournal = () => {
    onCreateJournal?.();
  };

  // Configuration for sort and filter options
  const sortOptions: SortOption[] = [
    { id: "recent", label: "Recent" },
    { id: "oldest", label: "Oldest" },
    { id: "title_asc", label: "Title A-Z" },
    { id: "title_desc", label: "Title Z-A" },
    { id: "word_count", label: "Word Count" }
  ];

  const filterOptions: FilterOption[] = [
    { id: "all", label: "All", value: "all" },
    { id: "private", label: "Private", value: "private" },
    { id: "public", label: "Public", value: "public" },
    { id: "shared", label: "Shared", value: "shared" }
  ];

  const getPrivacyDotColor = (privacy: Journal['privacy']) => {
    const privacyColors = {
      private: "bg-beige-400",
      public: "bg-green-500",
      shared: "bg-blue-500"
    };
    return privacyColors[privacy] || privacyColors.private;
  };

  const getPrivacyLabel = (privacy: Journal['privacy']) => {
    const labels = {
      private: "Private",
      public: "Public", 
      shared: "Shared"
    };
    return labels[privacy] || labels.private;
  };

  return (
    <div className={`flex-1 flex flex-col bg-card ${className}`}>
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold text-gray-800">{title}</h1>
            <span className="text-gray-500">•</span>
            <span className="text-gray-500">
              {displayJournals.length} {displayJournals.length === 1 ? 'journal' : 'journals'}
            </span>
          </div>
          {showCreateButton && (
            <Button 
              onClick={handleCreateJournal}
              className="bg-primary hover:bg-primary/90 text-primary-foreground gap-2 rounded-lg"
            >
              <Icon name="Plus" size={16} weight="regular" />
              Create
            </Button>
          )}
        </div>

        {/* Search and Controls */}
        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="flex-1 max-w-md">
            <SearchInput
              placeholder="Search journals..."
              value={searchQuery}
              onChange={handleSearchChange}
              variant="default"
            />
          </div>

          {/* Sort and Filter */}
          <div className="flex items-center gap-2">
            {/* Sort Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="gap-2 h-10 border-border hover:bg-accent">
                  Sort
                  <Icon name="CaretDown" size={16} weight="regular" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="bg-card border-border">
                {sortOptions.map((option) => (
                  <DropdownMenuItem
                    key={option.id}
                    onClick={() => handleSortChange(option.label)}
                    className="text-gray-700 hover:bg-accent"
                  >
                    {option.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Filter Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="gap-2 h-10 border-border hover:bg-accent">
                  Filter
                  <Icon name="CaretDown" size={16} weight="regular" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="bg-card border-border">
                {filterOptions.map((option) => (
                  <DropdownMenuItem
                    key={option.id}
                    onClick={() => handleFilterChange(option.label)}
                    className="text-gray-700 hover:bg-accent"
                  >
                    {option.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      {/* Journal Entries */}
      <div className="flex-1 overflow-y-auto p-6">
        {displayJournals.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Icon name="Book" size={64} weight="light" className="mb-4 text-gray-400" />
            <h3 className="text-xl font-semibold text-gray-800 mb-2">No journals yet</h3>
            <p className="text-gray-600 mb-6">Start documenting your research and thoughts</p>
            {showCreateButton && (
              <Button onClick={handleCreateJournal} className="bg-primary hover:bg-primary/90 text-primary-foreground">
                Create your first journal
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-6 max-w-4xl">
            {displayJournals.map((journal) => (
              <article 
                key={journal.id} 
                className="group cursor-pointer bg-card hover:bg-accent/50 p-4 rounded-lg border border-border/50 hover:border-border transition-all duration-200"
                onClick={() => handleJournalClick(journal.id)}
              >
                <div className="flex items-start justify-between mb-3">
                  <h3 className="text-lg font-semibold text-gray-800 group-hover:text-primary transition-colors line-clamp-2">
                    {journal.title}
                  </h3>
                  <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                    <div className={`w-2 h-2 rounded-full ${getPrivacyDotColor(journal.privacy)}`}></div>
                    <span className="text-sm text-gray-600 capitalize">
                      {getPrivacyLabel(journal.privacy)}
                    </span>
                  </div>
                </div>
                
                <p className="text-gray-600 text-sm leading-relaxed mb-4 line-clamp-3">
                  {journal.content}
                </p>
                
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <div className="flex items-center gap-4">
                    <span>{journal.timestamp}</span>
                    <span>by {journal.author}</span>
                    {journal.wordCount && (
                      <span>{journal.wordCount} words</span>
                    )}
                  </div>
                  {journal.tags && journal.tags.length > 0 && (
                    <div className="flex items-center gap-1">
                      {journal.tags.slice(0, 2).map((tag) => (
                        <span 
                          key={tag}
                          className="px-2 py-1 bg-accent text-gray-600 rounded text-xs"
                        >
                          {tag}
                        </span>
                      ))}
                      {journal.tags.length > 2 && (
                        <span className="text-gray-500">
                          +{journal.tags.length - 2}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
} 