"use client";

import React, { useState } from "react";
import { papersPageConfig, PaperItem } from "@/lib/config/papers-config";

interface PDFViewerProps {
  paper?: PaperItem | null;
  onCitePaper?: (paper: PaperItem) => void;
  className?: string;
}

export function PDFViewer({ 
  paper,
  onCitePaper,
  className = ""
}: PDFViewerProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages] = useState(15);
  const [zoom, setZoom] = useState(100);
  const [language, setLanguage] = useState("English");
  const [showLanguageDropdown, setShowLanguageDropdown] = useState(false);
  const [showZoomDropdown, setShowZoomDropdown] = useState(false);

  const config = papersPageConfig;

  const handlePreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  const handlePageInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const page = parseInt(e.target.value);
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  const handleZoomChange = (newZoom: number) => {
    setZoom(newZoom);
    setShowZoomDropdown(false);
  };

  const handleLanguageChange = (newLanguage: string) => {
    setLanguage(newLanguage);
    setShowLanguageDropdown(false);
  };

  const handleCiteClick = () => {
    if (paper && onCitePaper) {
      onCitePaper(paper);
    }
  };

  if (!paper) {
    return (
      <div 
        className={`flex-1 flex items-center justify-center ${className}`}
        style={{
          backgroundColor: config.styling.colors.contentBackground,
          minHeight: "100vh"
        }}
      >
        <div style={{
          textAlign: "center",
          color: config.styling.colors.textDisabled
        }}>
          <p style={{
            fontFamily: config.styling.typography.fontFamily,
            fontSize: config.styling.typography.sizes.large,
            fontWeight: config.styling.typography.weights.medium,
            margin: 0
          }}>
            Select a paper to view
          </p>
        </div>
      </div>
    );
  }

  return (
    <div 
      className={`flex-1 flex flex-col ${className}`}
      style={{
        backgroundColor: config.styling.colors.background,
        minHeight: "100vh"
      }}
    >
      {/* Top Controls */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: config.styling.padding.input,
        gap: config.styling.gap.large
      }}>
        {/* Language Selector */}
        <div style={{ position: "relative" }}>
          <button
            onClick={() => setShowLanguageDropdown(!showLanguageDropdown)}
            className="transition-colors"
            style={{
              display: "flex",
              alignItems: "center",
              gap: config.styling.gap.medium,
              padding: config.styling.padding.medium,
              backgroundColor: config.styling.colors.sidebarBackground,
              border: "none",
              borderRadius: config.styling.borderRadius.input,
              cursor: "pointer",
              height: "auto"
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = config.styling.colors.borderLight;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = config.styling.colors.sidebarBackground;
            }}
          >
            <span style={{
              color: config.styling.colors.textPrimary,
              fontFamily: config.styling.typography.fontFamily,
              fontSize: config.styling.typography.sizes.medium,
              fontWeight: config.styling.typography.weights.normal
            }}>
              {language}
            </span>
            <config.icons.caretDown 
              size={config.icons.size} 
              weight={config.icons.weight}
              style={{ color: config.styling.colors.textPrimary }}
            />
          </button>

          {showLanguageDropdown && (
            <div style={{
              position: "absolute",
              top: "100%",
              left: 0,
              marginTop: "4px",
              backgroundColor: config.styling.colors.contentBackground,
              border: `1px solid ${config.styling.colors.borderMedium}`,
              borderRadius: config.styling.borderRadius.input,
              boxShadow: `0 4px 6px ${config.styling.colors.shadowLight}`,
              zIndex: 10,
              minWidth: "120px"
            }}>
              {["English", "Spanish", "French", "German"].map((lang) => (
                <button
                  key={lang}
                  onClick={() => handleLanguageChange(lang)}
                  className="transition-colors"
                  style={{
                    display: "block",
                    width: "100%",
                    padding: config.styling.padding.input,
                    textAlign: "left",
                    backgroundColor: "transparent",
                    border: "none",
                    cursor: "pointer",
                    color: config.styling.colors.textPrimary,
                    fontFamily: config.styling.typography.fontFamily,
                    fontSize: config.styling.typography.sizes.medium
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = config.styling.colors.borderLight;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = "transparent";
                  }}
                >
                  {lang}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Page Navigation */}
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: config.styling.gap.small
        }}>
          <button
            onClick={handlePreviousPage}
            disabled={currentPage === 1}
            className="transition-colors"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "24px",
              height: "24px",
              backgroundColor: "transparent",
              border: "none",
              cursor: currentPage === 1 ? "not-allowed" : "pointer",
              opacity: currentPage === 1 ? 0.5 : 1
            }}
          >
            <config.icons.caretUp 
              size={config.icons.size} 
              weight={config.icons.weight}
              style={{ 
                color: config.styling.colors.textMuted,
                transform: "rotate(-90deg)"
              }}
            />
          </button>

          <div style={{
            display: "flex",
            alignItems: "center",
            gap: config.styling.gap.small,
            padding: "2px 8px",
            backgroundColor: config.styling.colors.contentBackground,
            border: `1px solid ${config.styling.colors.borderDark}`,
            borderRadius: config.styling.borderRadius.input
          }}>
            <input
              type="number"
              value={currentPage}
              onChange={handlePageInputChange}
              min={1}
              max={totalPages}
              style={{
                width: "45px",
                textAlign: "center",
                backgroundColor: "transparent",
                border: "none",
                outline: "none",
                color: config.styling.colors.textSecondary,
                fontFamily: config.styling.typography.fontFamily,
                fontSize: config.styling.typography.sizes.medium,
                fontWeight: config.styling.typography.weights.normal
              }}
            />
          </div>

          <span style={{
            color: config.styling.colors.textSecondary,
            fontFamily: config.styling.typography.fontFamily,
            fontSize: config.styling.typography.sizes.medium,
            fontWeight: config.styling.typography.weights.normal
          }}>
            of {totalPages} pages
          </span>

          <button
            onClick={handleNextPage}
            disabled={currentPage === totalPages}
            className="transition-colors"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "24px",
              height: "24px",
              backgroundColor: "transparent",
              border: "none",
              cursor: currentPage === totalPages ? "not-allowed" : "pointer",
              opacity: currentPage === totalPages ? 0.5 : 1
            }}
          >
            <config.icons.caretUp 
              size={config.icons.size} 
              weight={config.icons.weight}
              style={{ 
                color: config.styling.colors.textMuted,
                transform: "rotate(90deg)"
              }}
            />
          </button>
        </div>

        {/* Cite Button */}
        <button
          onClick={handleCiteClick}
          className="transition-colors"
          style={{
            display: "flex",
            alignItems: "center",
            gap: config.styling.gap.medium,
            padding: config.styling.padding.medium,
            backgroundColor: config.styling.colors.sidebarBackground,
            border: "none",
            borderRadius: config.styling.borderRadius.input,
            cursor: "pointer"
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = config.styling.colors.borderLight;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = config.styling.colors.sidebarBackground;
          }}
        >
          <config.icons.cite 
            size={config.icons.size} 
            weight={config.icons.weight}
            style={{ color: config.styling.colors.textPrimary }}
          />
          <span style={{
            color: config.styling.colors.textPrimary,
            fontFamily: config.styling.typography.fontFamily,
            fontSize: config.styling.typography.sizes.medium,
            fontWeight: config.styling.typography.weights.normal
          }}>
            Cite
          </span>
        </button>
      </div>

      {/* PDF Content Area */}
      <div style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        gap: "2px",
        padding: `0 ${config.styling.gap.large}`,
        marginBottom: config.styling.gap.large
      }}>
        {/* PDF Document Display */}
        <div style={{
          flex: 1,
          backgroundColor: config.styling.colors.contentBackground,
          border: `1px solid ${config.styling.colors.borderDark}`,
          borderRadius: config.styling.borderRadius.input,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "600px",
          boxShadow: `0 14px 25px ${config.styling.colors.shadowLight}`
        }}>
          {/* Placeholder for PDF content */}
          <div style={{
            width: "100%",
            height: "100%",
            backgroundColor: "#fff",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: config.styling.colors.textDisabled,
            fontFamily: config.styling.typography.fontFamily,
            fontSize: config.styling.typography.sizes.large
          }}>
            <div style={{ textAlign: "center" }}>
              <h3 style={{ margin: "0 0 8px 0", color: config.styling.colors.textPrimary }}>
                {paper.title}
              </h3>
              <p style={{ margin: 0 }}>
                PDF content would be displayed here
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Zoom Control */}
      <div style={{
        position: "absolute",
        bottom: config.styling.gap.section,
        right: config.styling.gap.section
      }}>
        <div style={{ position: "relative" }}>
          <button
            onClick={() => setShowZoomDropdown(!showZoomDropdown)}
            className="transition-colors"
            style={{
              display: "flex",
              alignItems: "center",
              gap: config.styling.gap.medium,
              padding: config.styling.padding.input,
              backgroundColor: config.styling.colors.contentBackground,
              border: `1px solid ${config.styling.colors.borderDark}`,
              borderRadius: config.styling.borderRadius.input,
              cursor: "pointer",
              width: "108px",
              height: "36px"
            }}
          >
            <span style={{
              flex: 1,
              color: config.styling.colors.textSecondary,
              fontFamily: config.styling.typography.fontFamily,
              fontSize: config.styling.typography.sizes.medium,
              fontWeight: config.styling.typography.weights.normal
            }}>
              {zoom}%
            </span>
            <config.icons.caretDown 
              size={config.icons.size} 
              weight={config.icons.weight}
              style={{ color: config.styling.colors.textMuted }}
            />
          </button>

          {showZoomDropdown && (
            <div style={{
              position: "absolute",
              bottom: "100%",
              right: 0,
              marginBottom: "4px",
              backgroundColor: config.styling.colors.contentBackground,
              border: `1px solid ${config.styling.colors.borderMedium}`,
              borderRadius: config.styling.borderRadius.input,
              boxShadow: `0 4px 6px ${config.styling.colors.shadowLight}`,
              zIndex: 10,
              minWidth: "100px"
            }}>
              {[50, 75, 100, 125, 150, 200].map((zoomLevel) => (
                <button
                  key={zoomLevel}
                  onClick={() => handleZoomChange(zoomLevel)}
                  className="transition-colors"
                  style={{
                    display: "block",
                    width: "100%",
                    padding: config.styling.padding.input,
                    textAlign: "left",
                    backgroundColor: "transparent",
                    border: "none",
                    cursor: "pointer",
                    color: config.styling.colors.textPrimary,
                    fontFamily: config.styling.typography.fontFamily,
                    fontSize: config.styling.typography.sizes.medium
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = config.styling.colors.borderLight;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = "transparent";
                  }}
                >
                  {zoomLevel}%
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PDFViewer; 