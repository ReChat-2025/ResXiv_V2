"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Icon } from "@/components/ui/icon";
import { usePapersStore } from "@/lib/stores/papers-store";
import { getIconName } from "@/lib/icons";
import { papersConfig } from "@/lib/papers-config";
import { Paper } from "@/lib/papers-config";

interface PaperViewerProps {
  paper: Paper;
  onCitePaper?: (paper: Paper) => void;
  onPaperAction?: (action: string, paper: Paper) => void;
}

export function PaperViewer({ paper, onCitePaper, onPaperAction }: PaperViewerProps) {
  const {
    currentPage,
    totalPages,
    selectedLanguage,
    zoomLevel,
    setCurrentPage,
    setSelectedLanguage,
    setZoomLevel,
  } = usePapersStore();

  const config = papersConfig?.paperViewer;

  // Add error boundary
  if (!paper) {
    return <EmptyPaperViewer />;
  }

  if (!config) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="text-sm text-gray-500">Loading paper viewer...</p>
        </div>
      </div>
    );
  }

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  const handlePreviousPage = () => {
    handlePageChange(currentPage - 1);
  };

  const handleNextPage = () => {
    handlePageChange(currentPage + 1);
  };

  const handleCite = () => {
    onCitePaper?.(paper);
    onPaperAction?.('cite', paper);
  };

  const formatPagination = (current: number, total: number): string => {
    return config.controls.pagination.format
      .replace("{current}", current.toString())
      .replace("{total}", total.toString());
  };

  return (
    <div className="flex-1 flex flex-col">
      {/* Paper Controls */}
      <div className="p-4 border-b bg-card">
        <div className="flex items-center justify-between">
          {/* Language and Navigation Controls */}
          <div className="flex items-center gap-4">
            {/* Language Selector */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="gap-2">
                  {selectedLanguage}
                  <Icon name={getIconName('expand')} size={16} weight="regular" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                {config.controls.languages.map((lang) => (
                  <DropdownMenuItem
                    key={lang.id}
                    onClick={() => setSelectedLanguage(lang.label)}
                    className={selectedLanguage === lang.label ? "bg-accent" : ""}
                  >
                    {lang.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Page Navigation */}
            <div className="flex items-center gap-2">
              <Button 
                variant="outline" 
                size="icon" 
                className="h-8 w-8"
                onClick={handlePreviousPage}
                disabled={currentPage <= 1}
                aria-label="Previous page"
              >
                <Icon name={getIconName('previous')} size={16} weight="regular" />
              </Button>
              
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  min={1}
                  max={totalPages}
                  value={currentPage}
                  onChange={(e) => handlePageChange(Number(e.target.value))}
                  className="w-12 h-8 text-center text-sm"
                  aria-label="Current page"
                />
                <span className="text-sm text-muted-foreground whitespace-nowrap">
                  {formatPagination(currentPage, totalPages)}
                </span>
              </div>
              
              <Button 
                variant="outline" 
                size="icon" 
                className="h-8 w-8"
                onClick={handleNextPage}
                disabled={currentPage >= totalPages}
                aria-label="Next page"
              >
                <Icon name={getIconName('next')} size={16} weight="regular" />
              </Button>
            </div>
          </div>

          {/* Zoom and Actions */}
          <div className="flex items-center gap-4">
            {/* Cite Button */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleCite}
              className="gap-2"
            >
              <Icon name={getIconName('citation')} size={16} weight="regular" />
              Cite
            </Button>
            
            {/* Zoom Control */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="gap-2">
                  {zoomLevel}
                  <Icon name={getIconName('expand')} size={16} weight="regular" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                {config.controls.zoomLevels.map((zoom) => (
                  <DropdownMenuItem
                    key={zoom}
                    onClick={() => setZoomLevel(zoom)}
                    className={zoomLevel === zoom ? "bg-accent" : ""}
                  >
                    {zoom}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Additional Actions */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon" className="h-8 w-8">
                  <Icon name="DotsThreeVertical" size={16} weight="regular" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => onPaperAction?.('download', paper)}>
                  <Icon name={getIconName('download')} size={16} weight="regular" className="mr-2" />
                  Download PDF
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onPaperAction?.('share', paper)}>
                  <Icon name={getIconName('share')} size={16} weight="regular" className="mr-2" />
                  Share
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onPaperAction?.('bookmark', paper)}>
                  <Icon name={getIconName('bookmark')} size={16} weight="regular" className="mr-2" />
                  Bookmark
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onPaperAction?.('export', paper)}>
                  <Icon name="Export" size={16} weight="regular" className="mr-2" />
                  Export Citation
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      {/* Paper Content Area */}
      <div className="flex-1 p-6 overflow-y-auto bg-muted/20">
        {/* Academic Paper Display */}
        <div className="max-w-4xl mx-auto bg-white rounded-lg overflow-hidden">
          {/* Paper Content */}
          <div className="p-12 text-black">
            {/* Paper Header */}
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold mb-4 uppercase tracking-wide">
                {paper.title}
              </h1>
              <div className="text-lg font-medium mb-2 text-gray-600">
                — START OF EXAMPLE —
              </div>
              <div className="text-sm italic text-gray-500 mb-6">
                [Page 1 - text aligned in the center and middle of the page]
              </div>
              
              {/* Author Information */}
              <div className="mb-6">
                <div className="text-base font-medium mb-2">
                  "Behavioral Study of Obedience"
                </div>
                <div className="text-sm text-gray-600 mb-1">
                  by [{paper.authors[0]}], [University]
                </div>
                <div className="text-sm text-gray-600">
                  {paper.year}
                </div>
              </div>
            </div>

            {/* Page Break Indicator */}
            <div className="text-center text-sm italic text-gray-500 mb-6">
              [Page 2 - text starts at the top, left]
            </div>

            {/* Abstract Section */}
            <div className="mb-8">
              <h2 className="text-lg font-bold mb-4">Abstract</h2>
              <p className="text-sm leading-relaxed text-justify">
                {paper.abstract || "There are little facts about the role of obedience when doing evil actions up until now (1961). Most people suggest that only psychopath people do horrible actions if they are ordered to do so. Our experiment tested people's obedience to authority. The results showed that most obey all orders given by the authority-figure. The conclusion is that when it comes to people harming others, the situation a person's in is more important than previously thought. In contrary to earlier belief, individual characteristics are less important."}
              </p>
            </div>

            {/* Next Page Indicator */}
            <div className="text-center text-sm italic text-gray-500 mb-6">
              [Page 3-X - text starts in the top, left corner, no extra spacing to align text]
            </div>

            {/* Introduction Section */}
            <div className="mb-8">
              <h2 className="text-lg font-bold mb-4">Introduction</h2>
              <p className="text-sm leading-relaxed text-justify mb-4">
                Current theories focus on personal characteristics to explain wrong-doing and how someone can intentionally harm others. In a survey, professionals such as doctors, psychologist and laymen thought that very few out of a population (1-3%) would harm others if ordered to do so.
              </p>
              <p className="text-sm leading-relaxed text-justify mb-4">
                In the recent war trial with Adolph Eichmann, he claims to "only have been following orders". The author wanted to test whether this is true, or just a cheap explanation. Can people harm others because they obey the orders? Are good-hearted people able to do that? The experiment will test whether a person can keep giving electric shocks to another person just because they are told to do so. The expectation is that very few will keep giving shocks, and that most persons will disobey the order.
              </p>
            </div>

            {/* Methods Section */}
            <div className="mb-8">
              <h2 className="text-lg font-bold mb-4">Methods</h2>
              <p className="text-sm leading-relaxed text-justify">
                The experimental procedure involved recruiting participants through newspaper advertisements. Participants were told they were taking part in a study on memory and learning. Each session involved three people: the experimenter (authority figure), the teacher (actual participant), and the learner (confederate). The teacher was instructed to deliver electric shocks of increasing intensity each time the learner made an error in a word-pair memory task...
              </p>
            </div>

            {/* Paper metadata footer */}
            <div className="mt-12 pt-6 border-t border-gray-200">
              <div className="text-xs text-gray-500 space-y-1">
                <div><span className="font-medium">Authors:</span> {paper.authors.join(", ")}</div>
                {paper.venue && <div><span className="font-medium">Venue:</span> {paper.venue}</div>}
                {paper.tags.length > 0 && <div><span className="font-medium">Tags:</span> {paper.tags.join(", ")}</div>}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Empty state when no paper is selected
export function EmptyPaperViewer() {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center max-w-md">
        <Icon 
          name={getIconName('document')} 
          size={64} 
          weight="light" 
          className="mx-auto mb-4 text-muted-foreground/50" 
        />
        <h3 className="text-lg font-medium mb-2">Select a Paper</h3>
        <p className="text-muted-foreground">
          Choose a paper from the sidebar to start reading and analyzing
        </p>
      </div>
    </div>
  );
} 