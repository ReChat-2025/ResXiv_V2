"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import { papersApi, type PaperResponse } from "@/lib/api/papers-api";
import { projectsApi } from "@/lib/api/projects-api";
import { agenticApi } from "@/lib/api/agentic-api";
import { analyticsApi, type GraphVisualizationResponse, type GraphAnalyticsResponse } from "@/lib/api/analytics-api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { 
  Search, 
  MessageCircle, 
  BarChart3, 
  FileText,
  ChevronLeft,
  ChevronRight,
  Upload,
  Send,
  X
} from "lucide-react";
import { Minus, Plus } from "phosphor-react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import * as d3 from 'd3';

// Types
interface Paper {
  id: string;
  title: string;
  authors: string[];
  abstract?: string;
  keywords: string[];
  date_added: string;
  last_modified: string;
  pdf_path?: string | null;
}

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
  paper_context?: string;
}

// Graph Visualization Component
interface GraphVisualizationProps {
  data: GraphVisualizationResponse;
  selectedNodeId?: string | null;
  onNodeClick?: (nodeId: string) => void;
}

const GraphVisualization: React.FC<GraphVisualizationProps> = ({ data, selectedNodeId, onNodeClick }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!data || !svgRef.current || !containerRef.current) return;

    const svg = d3.select(svgRef.current);
    const container = containerRef.current;
    
    // Clear previous content
    svg.selectAll("*").remove();
    
    // Get container dimensions
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    svg.attr("width", width).attr("height", height);
    
    // Create main group for zoom/pan transformations
    const mainGroup = svg.append("g");
    
    // Create elegant defs for gradients and patterns
    const defs = svg.append("defs");
    
    // Define a modern color palette that matches the website theme
    const clusterColors = {
      1: '#3b82f6', // blue-500 - primary theme color
      2: '#10b981', // emerald-500 - accent green
      3: '#8b5cf6', // violet-500 - accent purple
      4: '#f59e0b', // amber-500 - accent orange
      5: '#ef4444', // red-500 - accent red
      6: '#06b6d4', // cyan-500 - accent cyan
      7: '#84cc16', // lime-500 - accent lime
      8: '#ec4899', // pink-500 - accent pink
      default: 'hsl(var(--primary))', // fallback to theme primary
      isolated: 'hsl(var(--muted-foreground))', // muted color for isolated nodes
    };
    
    // Determine cluster assignments and colors for each node
    const nodeColorMap = new Map();
    data.nodes.forEach((node: any) => {
      const clusterId = node.cluster || node.cluster_id;
      const isIsolated = !data.edges.some(edge => 
        (typeof edge.source === 'string' ? edge.source : (edge.source as any).id) === node.id ||
        (typeof edge.target === 'string' ? edge.target : (edge.target as any).id) === node.id
      );
      
      if (isIsolated) {
        nodeColorMap.set(node.id, clusterColors.isolated);
      } else if (clusterId && clusterColors[clusterId as keyof typeof clusterColors]) {
        nodeColorMap.set(node.id, clusterColors[clusterId as keyof typeof clusterColors]);
      } else {
        nodeColorMap.set(node.id, clusterColors.default);
      }
    });
    
    // Subtle dot pattern background
    const pattern = defs.append("pattern")
      .attr("id", "dots")
      .attr("width", 20)
      .attr("height", 20)
      .attr("patternUnits", "userSpaceOnUse");
    
    pattern.append("circle")
      .attr("cx", 10)
      .attr("cy", 10)
      .attr("r", 1)
      .attr("fill", "hsl(var(--border))")
      .attr("opacity", 0.3);

    // Add background to main group (so it zooms with content)
    mainGroup.append("rect")
      .attr("x", -width * 2)
      .attr("y", -height * 2)
      .attr("width", width * 4)
      .attr("height", height * 4)
      .attr("fill", "url(#dots)");
    
    // Modern force simulation with better spacing
    const simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(data.edges).id((d: any) => d.id).strength(0.3).distance(150))
      .force("charge", d3.forceManyBody().strength(-400))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(50))
      .force("x", d3.forceX(width / 2).strength((d: any) => {
        // Stronger centering force for isolated nodes
        const isIsolated = !data.edges.some(edge => 
          (typeof edge.source === 'string' ? edge.source : (edge.source as any).id) === d.id ||
          (typeof edge.target === 'string' ? edge.target : (edge.target as any).id) === d.id
        );
        return isIsolated ? 0.03 : 0.01;
      }))
      .force("y", d3.forceY(height / 2).strength((d: any) => {
        // Stronger centering force for isolated nodes
        const isIsolated = !data.edges.some(edge => 
          (typeof edge.source === 'string' ? edge.source : (edge.source as any).id) === d.id ||
          (typeof edge.target === 'string' ? edge.target : (edge.target as any).id) === d.id
        );
        return isIsolated ? 0.03 : 0.01;
      }))
      .force("bounds", () => {
        // Keep nodes within viewport bounds
        data.nodes.forEach((d: any) => {
          const margin = 100;
          d.x = Math.max(margin, Math.min(width - margin, d.x || width / 2));
          d.y = Math.max(margin, Math.min(height - margin, d.y || height / 2));
        });
      });

    // Get connected nodes for highlighting
    const getConnectedNodes = (nodeId: string) => {
      const connected = new Set([nodeId]);
      data.edges.forEach(edge => {
        const sourceId = typeof edge.source === 'string' ? edge.source : (edge.source as any).id;
        const targetId = typeof edge.target === 'string' ? edge.target : (edge.target as any).id;
        
        if (sourceId === nodeId) {
          connected.add(targetId);
        }
        if (targetId === nodeId) {
          connected.add(sourceId);
        }
      });
      return connected;
    };

    const connectedNodes = selectedNodeId ? getConnectedNodes(selectedNodeId) : new Set();

    // Create smooth curved connections
    const link = mainGroup.append("g")
      .selectAll("path")
      .data(data.edges)
      .join("path")
      .attr("fill", "none")
      .attr("stroke", (d: any) => {
        if (selectedNodeId) {
          const sourceId = typeof d.source === 'string' ? d.source : (d.source as any).id;
          const targetId = typeof d.target === 'string' ? d.target : (d.target as any).id;
          if (sourceId === selectedNodeId || targetId === selectedNodeId) {
            return '#f59e0b';
          }
          return 'hsl(var(--muted-foreground))';
        }
        return 'hsl(var(--border))';
      })
      .attr("stroke-width", (d: any) => {
        const baseWidth = Math.max(1.5, Math.sqrt(d.weight || 1) * 1.5);
        if (selectedNodeId) {
          const sourceId = typeof d.source === 'string' ? d.source : (d.source as any).id;
          const targetId = typeof d.target === 'string' ? d.target : (d.target as any).id;
          if (sourceId === selectedNodeId || targetId === selectedNodeId) {
            return baseWidth * 2;
          }
        }
        return baseWidth;
      })
      .attr("opacity", (d: any) => {
        if (selectedNodeId) {
          const sourceId = typeof d.source === 'string' ? d.source : (d.source as any).id;
          const targetId = typeof d.target === 'string' ? d.target : (d.target as any).id;
          if (sourceId === selectedNodeId || targetId === selectedNodeId) {
            return 0.9;
          }
          return 0.2;
        }
        return 0.5;
      })
      .style("filter", "drop-shadow(0 1px 3px rgba(0,0,0,0.1))");

    // Create card-like node containers
    const nodeContainer = mainGroup.append("g")
      .selectAll("g")
      .data(data.nodes)
      .join("g")
      .style("cursor", "pointer");

    // Main node circle with modern styling
    nodeContainer.append("circle")
      .attr("r", 24)
      .attr("fill", (d: any) => {
        if (selectedNodeId) {
          if (d.id === selectedNodeId) {
            return '#f59e0b'; // amber for selected node
          }
          if (connectedNodes.has(d.id)) {
            return nodeColorMap.get(d.id) || clusterColors.default; // maintain cluster color for connected
          }
          return 'hsl(var(--muted))'; // dim non-connected nodes
        }
        // Default: show cluster colors
        return nodeColorMap.get(d.id) || clusterColors.default;
      })
      .attr("stroke", "hsl(var(--background))")
      .attr("stroke-width", 3)
      .style("filter", (d: any) => {
        if (selectedNodeId === d.id) {
          return "drop-shadow(0 8px 25px rgba(245, 158, 11, 0.4)) drop-shadow(0 0 0 3px rgba(245, 158, 11, 0.2))";
        }
        return "drop-shadow(0 4px 15px rgba(0,0,0,0.1))";
      });

    // Inner highlight circle
    nodeContainer.append("circle")
      .attr("r", 18)
      .attr("fill", "rgba(255,255,255,0.3)")
      .attr("stroke", "none");

    // Paper icon (simple representation)
    nodeContainer.append("rect")
      .attr("x", -6)
      .attr("y", -8)
      .attr("width", 12)
      .attr("height", 16)
      .attr("rx", 2)
      .attr("fill", "hsl(var(--background))")
      .attr("opacity", 0.9);

    nodeContainer.append("line")
      .attr("x1", -4)
      .attr("y1", -4)
      .attr("x2", 4)
      .attr("y2", -4)
      .attr("stroke", "hsl(var(--foreground))")
      .attr("stroke-width", 0.5)
      .attr("opacity", 0.7);

    nodeContainer.append("line")
      .attr("x1", -4)
      .attr("y1", -1)
      .attr("x2", 4)
      .attr("y2", -1)
      .attr("stroke", "hsl(var(--foreground))")
      .attr("stroke-width", 0.5)
      .attr("opacity", 0.7);

    nodeContainer.append("line")
      .attr("x1", -4)
      .attr("y1", 2)
      .attr("x2", 2)
      .attr("y2", 2)
      .attr("stroke", "hsl(var(--foreground))")
      .attr("stroke-width", 0.5)
      .attr("opacity", 0.7);

    // Modern labels with background cards
    const labelGroup = nodeContainer.append("g")
      .attr("transform", "translate(0, 45)");

    // Label background
    labelGroup.append("rect")
      .attr("x", (d: any) => {
        const text = d.title.substring(0, 14) + (d.title.length > 14 ? "..." : "");
        return -(text.length * 3.8);
      })
      .attr("y", -8)
      .attr("width", (d: any) => {
        const text = d.title.substring(0, 14) + (d.title.length > 14 ? "..." : "");
        return text.length * 7.6;
      })
      .attr("height", 16)
      .attr("rx", 8)
      .attr("fill", "hsl(var(--background))")
      .attr("stroke", "hsl(var(--border))")
      .attr("stroke-width", 1)
      .attr("opacity", 0.95)
      .style("filter", "drop-shadow(0 2px 8px rgba(0,0,0,0.1))");

    // Label text
    labelGroup.append("text")
      .text((d: any) => d.title.substring(0, 14) + (d.title.length > 14 ? "..." : ""))
      .attr("text-anchor", "middle")
      .attr("dy", "0.35em")
      .attr("font-size", "11px")
      .attr("font-weight", "500")
      .attr("fill", (d: any) => {
        if (selectedNodeId) {
          if (d.id === selectedNodeId || connectedNodes.has(d.id)) {
            return "hsl(var(--foreground))";
          }
          return "hsl(var(--muted-foreground))";
        }
        return "hsl(var(--foreground))";
      })
      .style("font-family", "var(--font-sans)")
      .style("opacity", (d: any) => {
        if (selectedNodeId && !connectedNodes.has(d.id)) {
          return 0.5;
        }
        return 1;
      });

    // Enhanced interactions
    nodeContainer
      .on("mouseover", function(event, d) {
        if (selectedNodeId !== d.id) {
          d3.select(this).select("circle:first-child")
            .transition()
            .duration(200)
            .attr("r", 28)
            .style("filter", "drop-shadow(0 6px 20px rgba(0,0,0,0.2))");
        }
      })
      .on("mouseout", function(event, d) {
        if (selectedNodeId !== d.id) {
          d3.select(this).select("circle:first-child")
            .transition()
            .duration(200)
            .attr("r", 24)
            .style("filter", "drop-shadow(0 4px 15px rgba(0,0,0,0.1))");
        }
      })
      .on("click", (event, d: any) => {
        if (onNodeClick) {
          onNodeClick(d.id);
        }
      });

    // Drag behavior
    const drag = d3.drag()
      .on("start", (event: any, d: any) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event: any, d: any) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event: any, d: any) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    nodeContainer.call(drag as any);

    // Add zoom and pan behavior
    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        mainGroup.attr("transform", event.transform);
      });

    // Apply zoom to the entire SVG
    svg.call(zoom as any);

    // Add zoom controls UI
    const zoomControls = d3.select(container)
      .append("div")
      .attr("class", "absolute top-4 right-4 flex flex-col gap-2 bg-background/80 backdrop-blur-sm border border-border/50 rounded-lg p-2")
      .style("position", "absolute")
      .style("top", "16px")
      .style("right", "16px")
      .style("z-index", "10");

    // Zoom in button
    zoomControls.append("button")
      .attr("class", "w-8 h-8 flex items-center justify-center rounded border border-border/50 bg-background hover:bg-accent transition-colors")
      .html(`<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
      </svg>`)
      .on("click", () => {
        svg.transition().duration(300).call(
          zoom.scaleBy as any, 1.5
        );
      });

    // Zoom out button
    zoomControls.append("button")
      .attr("class", "w-8 h-8 flex items-center justify-center rounded border border-border/50 bg-background hover:bg-accent transition-colors")
      .html(`<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 12H6"/>
      </svg>`)
      .on("click", () => {
        svg.transition().duration(300).call(
          zoom.scaleBy as any, 0.67
        );
      });

    // Reset zoom button
    zoomControls.append("button")
      .attr("class", "w-8 h-8 flex items-center justify-center rounded border border-border/50 bg-background hover:bg-accent transition-colors")
      .html(`<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
      </svg>`)
      .on("click", () => {
        svg.transition().duration(500).call(
          zoom.transform as any,
          d3.zoomIdentity
        );
      });

    // Smooth curved path function
    const linkArc = (d: any) => {
      const dx = d.target.x - d.source.x;
      const dy = d.target.y - d.source.y;
      const dr = Math.sqrt(dx * dx + dy * dy) * 0.4;
      return `M${d.source.x},${d.source.y}A${dr},${dr} 0 0,1 ${d.target.x},${d.target.y}`;
    };

    // Update positions with smooth transitions
    simulation.on("tick", () => {
      link.attr("d", linkArc);
      nodeContainer.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    // Cleanup
    return () => {
      simulation.stop();
      // Remove zoom controls
      d3.select(container).selectAll("div").remove();
    };
  }, [data, selectedNodeId, onNodeClick]);

  // Render container with SVG for the graph
  return (
    <div
      ref={containerRef}
      className="w-full h-full relative bg-gradient-to-br from-background via-muted/5 to-muted/20 rounded-xl overflow-hidden border border-border/40 backdrop-blur-sm"
      style={{ minHeight: '500px' }}
    >
      <svg ref={svgRef} className="w-full h-full" />
    </div>
  );
};

export default function PapersPage() {
  const router = useRouter();
  const params = useParams();
  const projectSlug = params.projectSlug as string;
  
  // Core state
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // UI state
  const [leftSidebarCollapsed, setLeftSidebarCollapsed] = useState(false);
  const [rightSidebarCollapsed, setRightSidebarCollapsed] = useState(false);
  const [currentViewMode, setCurrentViewMode] = useState<'chat' | 'graph'>('chat');
  const [searchQuery, setSearchQuery] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  
  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isProcessingMessage, setIsProcessingMessage] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  // Right sidebar tab
  const [rightTab, setRightTab] = useState<'chat' | 'insights'>('chat');
  // --- PDF viewer state ---
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  // Reference to the PDF iframe to hook selection events inside it
  const pdfIframeRef = useRef<HTMLIFrameElement>(null);
  const [isLoadingPdf, setIsLoadingPdf] = useState(false);
  const [pdfZoom, setPdfZoom] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  // Text selection state
  const [selectedText, setSelectedText] = useState<{text: string, page: number} | null>(null);
  const [showSelectionDialog, setShowSelectionDialog] = useState(false);
  const [selectionComment, setSelectionComment] = useState("");
  const [showAddToChat, setShowAddToChat] = useState(false);
  const [selectionPosition, setSelectionPosition] = useState<{x: number, y: number} | null>(null);
  const [showSelectionHint, setShowSelectionHint] = useState(false);
  const [showTip, setShowTip] = useState(true);
  const [isSelecting, setIsSelecting] = useState(false);
  const [selectionStartPos, setSelectionStartPos] = useState<{x: number, y: number} | null>(null);
  const [selectionRect, setSelectionRect] = useState<{x: number, y: number, width: number, height: number} | null>(null);

  const handleZoomIn = () => setPdfZoom((z) => Math.min(z + 0.1, 2));
  const handleZoomOut = () => setPdfZoom((z) => Math.max(z - 0.1, 0.5));
  const handlePrevPage = () => setCurrentPage((p) => Math.max(p - 1, 1));
  const handleNextPage = () => setCurrentPage((p) => Math.min(p + 1, totalPages));
  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  // Text selection handlers
  const handleTextSelection = (event?: MouseEvent) => {
    if (typeof window !== 'undefined') {
      const selection = window.getSelection();
      if (selection && selection.toString().trim()) {
        const selectedTextContent = selection.toString().trim();
        setSelectedText({ text: selectedTextContent, page: currentPage });
        
        // Get selection position for floating button
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        setSelectionPosition({
          x: rect.right + 10,
          y: rect.top + (rect.height / 2)
        });
        setShowAddToChat(true);
      } else {
        // Clear selection UI if no text selected
        setShowAddToChat(false);
        setSelectedText(null);
        setSelectionPosition(null);
      }
    }
  };

  const handleAddToChatClick = () => {
    setShowAddToChat(false);
    setShowSelectionDialog(true);
    // Clear the visual selection from main document
    if (typeof window !== 'undefined') {
      const selection = window.getSelection();
      if (selection) {
        selection.removeAllRanges();
      }
    }
  };

  const handleSendSelectionToChat = async () => {
    if (!selectedText || !selectionComment.trim() || !projectId || !selectedPaper) return;

    const contextMessage = `[Selected text from page ${selectedText.page}]:\n"${selectedText.text}"\n\nQuestion: ${selectionComment.trim()}`;

    // Add user message to chat
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: contextMessage,
      timestamp: new Date().toISOString(),
      paper_context: selectedPaper.id,
    };

    setChatMessages(prev => [...prev, userMessage]);
    setChatInput("");
    setIsProcessingMessage(true);
    setShowSelectionDialog(false);
    setSelectedText(null);
    setSelectionComment("");
    setShowAddToChat(false);
    setSelectionPosition(null);
    setShowSelectionHint(false);

    try {
      const response = await agenticApi.paperChat(projectId, {
        paper_id: selectedPaper.id,
        message: contextMessage,
        conversation_id: currentConversationId || undefined,
      });

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString(),
      };

      setChatMessages(prev => [...prev, assistantMessage]);
      
      if (response.conversation_id) {
        setCurrentConversationId(response.conversation_id);
      }
    } catch (error: any) {
      console.error('Failed to process selection message:', error);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'Sorry, I encountered an error processing your selection. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setChatMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsProcessingMessage(false);
    }
  };
  
  // Analytics state
  const [analyticsData, setAnalyticsData] = useState<any>(null);
  const [isLoadingAnalytics, setIsLoadingAnalytics] = useState(false);

  // Diagnostics state
  const [diagnosticsData, setDiagnosticsData] = useState<any>(null);
  const [isLoadingDiagnostics, setIsLoadingDiagnostics] = useState(false);

  // Graph analytics state
  const [graphVisualizationData, setGraphVisualizationData] = useState<GraphVisualizationResponse | null>(null);
  const [graphAnalyticsData, setGraphAnalyticsData] = useState<GraphAnalyticsResponse | null>(null);
  const [isLoadingGraphAnalytics, setIsLoadingGraphAnalytics] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Fetch project ID from slug
  useEffect(() => {
    const fetchProjectId = async () => {
      if (projectSlug) {
        try {
          const projectsResponse = await projectsApi.getProjects();
          const project = projectsResponse.projects.find((p: any) => 
            p.slug === projectSlug || p.id === projectSlug
          );
          
          if (project) {
            setProjectId(project.id);
          } else {
            setError('Project not found');
            router.push('/projects');
          }
        } catch (error: any) {
          console.error('Failed to fetch project:', error);
          setError('Failed to load project');
        }
      }
    };

    fetchProjectId();
  }, [projectSlug, router]);

  // Fetch papers when project ID is available
  useEffect(() => {
    const fetchPapers = async () => {
      if (projectId) {
        try {
          setIsLoading(true);
          setError(null);
          
          const response = await papersApi.getPapers({
            project_id: projectId,
            page: 1,
            size: 50,
            search: searchQuery || undefined,
          });
          
          const convertedPapers: Paper[] = response.papers.map(paper => ({
            id: paper.id,
            title: paper.title,
            authors: paper.authors,
            abstract: paper.abstract || undefined,
            keywords: paper.keywords,
            date_added: paper.date_added,
            last_modified: paper.last_modified,
            pdf_path: paper.pdf_path,
          }));
          
          setPapers(convertedPapers);
          
          // Select first paper by default
          if (convertedPapers.length > 0 && !selectedPaper) {
            setSelectedPaper(convertedPapers[0]);
          }
        } catch (error: any) {
          console.error('Failed to fetch papers:', error);
          setError(error.message || 'Failed to load papers');
        } finally {
          setIsLoading(false);
        }
      }
    };

    fetchPapers();
  }, [projectId, searchQuery]);

  // Auto-hide tip after 8 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowTip(false);
    }, 8000);
    return () => clearTimeout(timer);
  }, [selectedPaper]);

  // Load PDF when selected paper changes
  useEffect(() => {
    let objectUrl: string | null = null;

    const fetchPdf = async () => {
      if (selectedPaper && selectedPaper.pdf_path && projectId) {
        setIsLoadingPdf(true);
        setPdfUrl(null);
        setCurrentPage(1);
        try {
          const blob = await papersApi.downloadPaper(projectId, selectedPaper.id);
          objectUrl = URL.createObjectURL(blob);
          setPdfUrl(objectUrl);
          
          // Try to extract page count from PDF content
          try {
            const arrayBuffer = await blob.arrayBuffer();
            const pdfText = new TextDecoder('latin1').decode(arrayBuffer);
            
            // Look for page count in PDF structure
            const pageCountMatch = pdfText.match(/\/Count\s+(\d+)/);
            if (pageCountMatch) {
              setTotalPages(parseInt(pageCountMatch[1], 10));
            } else {
              // Fallback: count page objects
              const pageMatches = pdfText.match(/\/Type\s*\/Page[^s]/g);
              setTotalPages(pageMatches ? pageMatches.length : 20);
            }
          } catch (parseError) {
            console.warn('Could not parse PDF page count:', parseError);
            setTotalPages(20); // Reasonable default for academic papers
          }
          // Get diagnostics for accurate page count
          try {
            const diag = await papersApi.getPaperDiagnostics(projectId, selectedPaper.id);
            if (diag && diag.page_count) {
              setTotalPages(diag.page_count);
            }
          } catch (dErr) {
            console.warn('Diagnostics not available', dErr);
          }
        } catch (err) {
          console.error("Failed to load PDF:", err);
          setTotalPages(1);
        } finally {
          setIsLoadingPdf(false);
        }
      } else {
        setPdfUrl(null);
        setCurrentPage(1);
        setTotalPages(1);
      }
    };

    fetchPdf();

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [selectedPaper, projectId]);

  // Fetch analytics data for graph view
  useEffect(() => {
    const fetchAnalytics = async () => {
      const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null;
      if (!token) {
        // Skip analytics call when not authenticated (e.g. public browsing)
        return;
      }

      if (projectId && currentViewMode === 'graph') {
        try {
          setIsLoadingAnalytics(true);
          setIsLoadingGraphAnalytics(true);
          
          // Fetch both traditional analytics and graph analytics
          const [analytics, graphAnalytics, graphVisualization] = await Promise.all([
            analyticsApi.getProjectAnalytics({ project_id: projectId }),
            analyticsApi.getGraphAnalytics(projectId),
            analyticsApi.getGraphVisualization(projectId, 'force_directed', false)
          ]);
          
          setAnalyticsData(analytics);
          setGraphAnalyticsData(graphAnalytics);
          setGraphVisualizationData(graphVisualization);
        } catch (error: any) {
          console.error('Failed to fetch analytics:', error);
          // Clear data on error
          setAnalyticsData(null);
          setGraphAnalyticsData(null);
          setGraphVisualizationData(null);
        } finally {
          setIsLoadingAnalytics(false);
          setIsLoadingGraphAnalytics(false);
        }
      }
    };

    fetchAnalytics();
  }, [projectId, currentViewMode]);

  // Clear diagnostics when paper changes
  useEffect(() => {
    setDiagnosticsData(null);
  }, [selectedPaper]);

  // Fetch diagnostics when insights tab is selected and a paper is selected
  useEffect(() => {
    const fetchDiagnostics = async () => {
      if (projectId && selectedPaper && rightTab === 'insights') {
        try {
          setIsLoadingDiagnostics(true);
          const diagnostics = await papersApi.getPaperDiagnostics(projectId, selectedPaper.id);
          setDiagnosticsData(diagnostics);
        } catch (error: any) {
          console.error('Failed to fetch diagnostics:', error);
          setDiagnosticsData(null);
        } finally {
          setIsLoadingDiagnostics(false);
        }
      }
    };

    fetchDiagnostics();
  }, [projectId, selectedPaper, rightTab]);

  // Utility to detect selected text in main document or any same-origin iframe.
  const getSelectionInfo = (): { text: string; x: number; y: number } | null => {
    // Check main document first
    const sel = window.getSelection();
    if (sel && sel.toString().trim()) {
      const range = sel.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      return { text: sel.toString().trim(), x: rect.right, y: rect.top + rect.height / 2 };
    }

    // Check all iframes for same-origin selections
    const iframes = Array.from(document.querySelectorAll<HTMLIFrameElement>('iframe'));
    for (const frame of iframes) {
      try {
        const frameSel = frame.contentWindow?.getSelection();
        if (frameSel && frameSel.toString().trim()) {
          const range = frameSel.getRangeAt(0);
          const rect = range.getBoundingClientRect();
          const frameRect = frame.getBoundingClientRect();
          return {
            text: frameSel.toString().trim(),
            x: frameRect.left + rect.right,
            y: frameRect.top + rect.top + rect.height / 2,
          };
        }
      } catch (_) {
        // Ignore cross-origin frames
      }
    }
    return null;
  };

  // Enhanced PDF text selection handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    setIsSelecting(true);
    setSelectionStartPos({ x, y });
    setSelectionRect(null);
    setShowAddToChat(false);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isSelecting || !selectionStartPos) return;
    
    const rect = e.currentTarget.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;
    
    const x = Math.min(selectionStartPos.x, currentX);
    const y = Math.min(selectionStartPos.y, currentY);
    const width = Math.abs(currentX - selectionStartPos.x);
    const height = Math.abs(currentY - selectionStartPos.y);
    
    // Only show selection rectangle if drag is meaningful
    if (width > 5 || height > 5) {
      setSelectionRect({ x, y, width, height });
    }
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isSelecting || !selectionStartPos) return;
    
    const rect = e.currentTarget.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;
    
    const width = Math.abs(currentX - selectionStartPos.x);
    const height = Math.abs(currentY - selectionStartPos.y);
    
    setIsSelecting(false);
    
    // Show selection button if user made a meaningful selection
    if (width > 10 && height > 10) {
      const centerX = Math.min(selectionStartPos.x, currentX) + width / 2;
      const centerY = Math.min(selectionStartPos.y, currentY) + height / 2;
      
      // Convert to screen coordinates
      const pdfContainer = e.currentTarget.getBoundingClientRect();
      setSelectionPosition({
        x: pdfContainer.left + centerX,
        y: pdfContainer.top + centerY
      });
      
      setSelectedText({ text: "", page: currentPage });
      setShowAddToChat(true);
      
      // Auto-hide after 8 seconds
      setTimeout(() => {
        setShowAddToChat(false);
        setSelectionRect(null);
      }, 8000);
    } else {
      setSelectionRect(null);
    }
    
    setSelectionStartPos(null);
  };

  // Also maintain fallback text selection detection
  useEffect(() => {
    const handleSelectionEvents = () => {
      setTimeout(() => {
        const info = getSelectionInfo();
        if (info && info.text.length > 3) {
          setSelectedText({ text: info.text, page: currentPage });
          setSelectionPosition({ x: info.x + 10, y: info.y });
          setShowAddToChat(true);
          
          setTimeout(() => {
            setShowAddToChat(false);
          }, 8000);
        }
      }, 100);
    };

    document.addEventListener('mouseup', handleSelectionEvents);
    document.addEventListener('selectionchange', handleSelectionEvents);

    return () => {
      document.removeEventListener('mouseup', handleSelectionEvents);
      document.removeEventListener('selectionchange', handleSelectionEvents);
    };
  }, [currentPage]);

  const showPDFSelectionPrompt = (x: number, y: number) => {
    setSelectionPosition({ x: x + 10, y: y });
    setShowAddToChat(true);
    // Set a placeholder for PDF text - user will input the actual text in dialog
    setSelectedText({ text: "", page: currentPage });
  };

  const handleAddPapers = async () => {
    if (!projectId) {
      return;
    }

    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf';
    input.multiple = true;
    
    input.onchange = async (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (!files || files.length === 0) return;
      
      setIsUploading(true);
      
      try {
        for (const file of Array.from(files)) {
          await papersApi.uploadPaper({
            project_id: projectId,
            file: file,
            process_with_grobid: true,
            run_diagnostics: true,
            private_uploaded: true,
          });
        }
        
        // Refresh papers list
        const response = await papersApi.getPapers({
          project_id: projectId,
          page: 1,
          size: 50,
        });
        
        const convertedPapers: Paper[] = response.papers.map(paper => ({
          id: paper.id,
          title: paper.title,
          authors: paper.authors,
          abstract: paper.abstract || undefined,
          keywords: paper.keywords,
          date_added: paper.date_added,
          last_modified: paper.last_modified,
          pdf_path: paper.pdf_path,
        }));
        
        setPapers(convertedPapers);
        
      } catch (error: any) {
        console.error('Failed to upload papers:', error);
      } finally {
        setIsUploading(false);
      }
    };
    
    input.click();
  };

  const handleSendMessage = async () => {
    if (!chatInput.trim() || !projectId || isProcessingMessage) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: chatInput.trim(),
      timestamp: new Date().toISOString(),
      paper_context: selectedPaper?.id,
    };

    setChatMessages(prev => [...prev, userMessage]);
    setChatInput("");
    setIsProcessingMessage(true);

    try {
      const response = await agenticApi.paperChat(projectId, {
        paper_id: selectedPaper!.id,
        message: userMessage.content,
        conversation_id: currentConversationId || undefined,
      });

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString(),
      };

      setChatMessages(prev => [...prev, assistantMessage]);
      
      if (response.conversation_id) {
        setCurrentConversationId(response.conversation_id);
      }
    } catch (error: any) {
      console.error('Failed to process message:', error);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'Sorry, I encountered an error processing your message. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setChatMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsProcessingMessage(false);
    }
  };

  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return `${Math.floor(diffInSeconds / 86400)}d ago`;
  };

  // Helper function to render diagnostic content (handles both strings and structured objects)
  const renderDiagnosticContent = (content: any) => {
    if (!content) return null;
    
    // If it's a string, render as markdown
    if (typeof content === 'string') {
      return (
        <div className="prose prose-sm prose-slate dark:prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {content}
          </ReactMarkdown>
        </div>
      );
    }
    
    // If it's an object, render structured content
    if (typeof content === 'object' && content !== null) {
      return (
        <div className="space-y-3">
          {Object.entries(content).map(([key, value]) => (
            <div key={key} className="border-l-2 border-muted pl-3">
              <h5 className="font-medium text-foreground text-xs mb-1 capitalize">
                {key.replace(/_/g, ' ')}
              </h5>
              <div className="prose prose-sm prose-slate dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {String(value)}
                </ReactMarkdown>
              </div>
            </div>
          ))}
        </div>
      );
    }
    
    // Fallback for other types
    return (
      <div className="prose prose-sm prose-slate dark:prose-invert max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {String(content)}
        </ReactMarkdown>
      </div>
    );
  };



  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <Card className="w-96">
          <CardContent className="p-6 text-center">
            <p className="text-destructive mb-4">{error}</p>
            <Button onClick={() => window.location.reload()}>Retry</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-background overflow-hidden">
      {/* Left Sidebar - Papers List */}
      <div className={`transition-all duration-300 border-r border-border bg-gradient-to-b from-card to-card/80 flex-shrink-0 ${
        leftSidebarCollapsed ? 'w-16' : 'w-80'
      }`}>
        <div className="flex flex-col h-full overflow-hidden">
          {/* Header */}
          <div className="p-6 pb-4 flex-shrink-0">
            <div className="flex items-center justify-between">
              {!leftSidebarCollapsed && (
                <h2 className="text-xl font-bold text-foreground tracking-tight">Papers</h2>
              )}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setLeftSidebarCollapsed(!leftSidebarCollapsed)}
                className="text-muted-foreground hover:text-foreground hover:bg-accent/50 rounded-lg transition-all duration-200"
              >
                {leftSidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
              </Button>
            </div>
          </div>

          {!leftSidebarCollapsed && (
            <>
              {/* View Mode Toggle */}
              <div className="px-6 pb-4 flex-shrink-0">
                <div className="flex bg-muted/40 rounded-xl p-1 space-x-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className={`flex-1 rounded-lg transition-all duration-200 ${
                      currentViewMode === 'chat' 
                        ? 'bg-background shadow-sm text-foreground font-medium' 
                        : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
                    }`}
                    onClick={() => setCurrentViewMode('chat')}
                  >
                    <FileText className="h-4 w-4 mr-2" />
                    PDF View
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className={`flex-1 rounded-lg transition-all duration-200 ${
                      currentViewMode === 'graph' 
                        ? 'bg-background shadow-sm text-foreground font-medium' 
                        : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
                    }`}
                    onClick={() => setCurrentViewMode('graph')}
                  >
                    <BarChart3 className="h-4 w-4 mr-2" />
                    Graph View
                  </Button>
                </div>
              </div>

              {/* Separator */}
              <div className="mx-6 mb-4">
                <div className="h-px bg-gradient-to-r from-transparent via-border to-transparent"></div>
              </div>

              {/* Search and Add */}
              <div className="px-6 pb-4 space-y-4 flex-shrink-0">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search papers..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10 h-10 bg-background/50 border-border/50 rounded-lg focus:bg-background focus:border-primary/50 transition-all duration-200"
                  />
                </div>
                <Button
                  onClick={handleAddPapers}
                  disabled={isUploading}
                  className="w-full h-10 bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg font-medium shadow-sm hover:shadow-md transition-all duration-200"
                >
                  {isUploading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></div>
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="h-4 w-4 mr-2" />
                      Add Papers
                    </>
                  )}
                </Button>
              </div>

              {/* Papers List */}
              <div className="flex-1 overflow-y-auto px-6 min-h-0">
                 <div className="space-y-3 pb-6">
                  {papers.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-muted/50 flex items-center justify-center">
                        <FileText className="h-7 w-7 opacity-50" />
                      </div>
                      <p className="text-sm font-medium mb-1">
                        {searchQuery ? 'No papers found' : 'No papers yet'}
                      </p>
                      <p className="text-xs text-muted-foreground/70">
                        {searchQuery ? 'Try adjusting your search' : 'Upload your first paper to get started'}
                      </p>
                    </div>
                  ) : (
                    papers.map((paper) => (
                      <div
                        key={paper.id}
                        className={`group cursor-pointer transition-all duration-200 rounded-xl border-2 ${
                          selectedPaper?.id === paper.id 
                            ? 'bg-primary/5 border-primary/20 shadow-md shadow-primary/5' 
                            : 'bg-card/50 border-transparent hover:bg-accent/50 hover:border-border/50 hover:shadow-sm'
                        }`}
                        onClick={() => setSelectedPaper(paper)}
                      >
                        <div className="p-4">
                          <div className="flex items-start gap-3">
                            <FileText
                              className={`w-4 h-4 mt-1 flex-shrink-0 transition-colors duration-200 ${
                                selectedPaper?.id === paper.id ? 'text-primary' : 'text-muted-foreground/40'
                              }`}
                            />
                            <h3 className="font-medium text-sm text-foreground line-clamp-2 leading-relaxed flex-1">
                              {paper.title}
                            </h3>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Center Area */}
      {currentViewMode === 'chat' ? (
        <div className="flex-1 bg-muted/30 flex flex-col min-h-0 overflow-hidden">
          {selectedPaper && selectedPaper.pdf_path ? (
            isLoadingPdf ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : pdfUrl ? (
              <div className="relative w-full h-full overflow-auto">
                {pdfUrl && (
                  <>
                    {/* Helper Message for Text Selection */}
                    {showTip && (
                      <div className="absolute top-4 left-4 z-20 bg-muted/90 text-muted-foreground px-3 py-2 rounded-lg text-xs border border-border/50 backdrop-blur-sm max-w-64 animate-in fade-in-0 slide-in-from-top-2 duration-300">
                        <div className="flex items-start gap-2">
                          <div className="flex-1">
                            🎯 <strong>NEW:</strong> Click and drag to select text areas, then ask questions instantly!
                          </div>
                          <button
                            onClick={() => setShowTip(false)}
                            className="text-muted-foreground hover:text-foreground opacity-60 hover:opacity-100 transition-opacity ml-1"
                            title="Dismiss tip"
                          >
                            ×
                          </button>
                        </div>
                      </div>
                    )}
                    
                    <iframe
                      ref={pdfIframeRef}
                      key={`${selectedPaper?.id}-${currentPage}`}
                      src={`${pdfUrl}#page=${currentPage}&toolbar=0&navpanes=0&scrollbar=0&statusbar=0&messages=0&view=FitH`}
                      title={selectedPaper.title}
                      className="w-full h-full" 
                      style={{transform:`scale(${pdfZoom})`, transformOrigin:'top center'}}
                    />
                    
                    {/* Text Selection Overlay */}
                    <div
                      className="absolute inset-0 z-10 cursor-text"
                      onMouseDown={handleMouseDown}
                      onMouseMove={handleMouseMove}
                      onMouseUp={handleMouseUp}
                      style={{
                        background: 'transparent',
                        pointerEvents: 'auto'
                      }}
                    >
                      {/* Selection Rectangle */}
                      {selectionRect && (
                        <div
                          className="absolute border-2 border-primary bg-primary/10 rounded-sm pointer-events-none"
                          style={{
                            left: `${selectionRect.x}px`,
                            top: `${selectionRect.y}px`,
                            width: `${selectionRect.width}px`,
                            height: `${selectionRect.height}px`,
                          }}
                        />
                      )}
                    </div>
                    
                    {/* Selection Hint Overlay */}
                    {showSelectionHint && (
                      <div className="absolute top-4 left-4 z-20 bg-primary/90 text-primary-foreground px-3 py-2 rounded-lg text-sm font-medium shadow-lg animate-in fade-in-0 slide-in-from-top-2 duration-300">
                        📝 Keep selecting text...
                      </div>
                    )}

                    {/* Floating Add to Chat Button */}
                    {showAddToChat && selectionPosition && (
                      <div
                        className="fixed z-30 transform -translate-y-1/2"
                        style={{
                          left: `${Math.min(selectionPosition.x, window.innerWidth - 200)}px`,
                          top: `${Math.max(50, Math.min(selectionPosition.y, window.innerHeight - 100))}px`,
                        }}
                      >
                        <Button
                          onClick={handleAddToChatClick}
                          data-selection-button
                          className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white shadow-xl border border-white/20 rounded-lg px-4 py-2 text-sm font-medium animate-in fade-in-0 zoom-in-95 duration-200 transform hover:scale-105 transition-transform"
                        >
                          ⚡ Ask about selected area
                        </Button>
                      </div>
                    )}

                    {/* Floating Pagination Controls - Bottom Center */}
                    <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-10">
                      <div className="flex items-center gap-3 bg-background/90 backdrop-blur-sm border border-border rounded-lg px-3 py-1.5 shadow-lg">
                        <Button variant="ghost" size="icon" onClick={handlePrevPage} disabled={currentPage <= 1}>
                          <ChevronLeft size={16} />
                        </Button>
                        <div className="flex items-center gap-2">
                          <Input
                            type="number"
                            min={1}
                            max={totalPages}
                            value={currentPage}
                            onChange={(e) => handlePageChange(Number(e.target.value))}
                            className="w-14 h-8 text-center text-sm"
                          />
                          <span className="text-sm text-muted-foreground">of {totalPages}</span>
                        </div>
                        <Button variant="ghost" size="icon" onClick={handleNextPage} disabled={currentPage >= totalPages}>
                          <ChevronRight size={16} />
                        </Button>
                      </div>
                    </div>
                    
                    {/* Floating Zoom Controls - Top Right */}
                    <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
                      <div className="flex items-center gap-2 bg-background/90 backdrop-blur-sm border border-border rounded-lg px-3 py-1.5 shadow-lg">
                        <Button variant="ghost" size="icon" onClick={handleZoomOut}>
                          <Minus size={16} />
                        </Button>
                        <span className="text-sm w-12 text-center select-none font-medium">{Math.round(pdfZoom*100)}%</span>
                        <Button variant="ghost" size="icon" onClick={handleZoomIn}>
                          <Plus size={16} />
                        </Button>
                      </div>
                      
                      {/* Ask About Text Button - Always Visible */}
                      <Button
                        onClick={() => {
                          setSelectedText({ text: "", page: currentPage });
                          setShowSelectionDialog(true);
                        }}
                        className="bg-gradient-to-r from-green-500 to-blue-500 hover:from-green-600 hover:to-blue-600 text-white shadow-lg border border-white/20 rounded-lg px-3 py-2 text-sm font-medium backdrop-blur-sm transform hover:scale-105 transition-all duration-200"
                        title="Quick way to ask questions about any text from this page"
                      >
                        🚀 Quick Ask
                      </Button>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center p-8">
                <p className="text-muted-foreground">Unable to display PDF.</p>
              </div>
            )
          ) : (
            <div className="flex-1 flex items-center justify-center p-8">
              <Card className="max-w-2xl w-full bg-card">
                <CardContent className="p-8 text-center">
                  <FileText className="h-16 w-16 mx-auto mb-4 text-muted-foreground" />
                  <h3 className="text-xl font-semibold text-foreground mb-2 font-sans">
                    {selectedPaper ? "No PDF available" : "Select a Paper"}
                  </h3>
                  <p className="text-muted-foreground font-sans">
                    {selectedPaper
                      ? "This paper does not have an associated PDF."
                      : "Choose a paper from the sidebar to view its content"}
                  </p>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      ) : (
        /* Graph View Center */
        <div className="flex-1 bg-muted/20 p-6 overflow-hidden min-h-0">
          {isLoadingAnalytics || isLoadingGraphAnalytics ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : graphVisualizationData && graphAnalyticsData ? (
            <div className="h-full flex flex-col overflow-hidden">
              {/* Graph Visualization - Full Height */}
              <Card className="h-full bg-card/50 backdrop-blur-sm border-border/50 overflow-hidden">
                <CardHeader className="pb-4 border-b border-border/50 flex-shrink-0">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg font-semibold text-foreground">
                        Paper Network
                      </CardTitle>
                      <p className="text-sm text-muted-foreground mt-1">
                        Explore relationships between {graphVisualizationData?.nodes?.length || 0} papers
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={async () => {
                        if (!projectId) return;
                        
                        setIsLoadingGraphAnalytics(true);
                        try {
                          // First regenerate the graph with new papers
                          await analyticsApi.regenerateGraph(projectId);
                          
                          // Then fetch the updated data
                          const [analytics, graphAnalytics, graphVisualization] = await Promise.all([
                            analyticsApi.getProjectAnalytics({ project_id: projectId }),
                            analyticsApi.getGraphAnalytics(projectId),
                            analyticsApi.getGraphVisualization(projectId, 'force_directed', false)
                          ]);
                          
                          setAnalyticsData(analytics);
                          setGraphAnalyticsData(graphAnalytics);
                          setGraphVisualizationData(graphVisualization);
                        } catch (error) {
                          console.error('Failed to regenerate graph:', error);
                          // Show error to user or handle gracefully
                        } finally {
                          setIsLoadingGraphAnalytics(false);
                        }
                      }}
                      disabled={isLoadingGraphAnalytics}
                      className="flex items-center gap-2"
                    >
                      <svg
                        className={`h-4 w-4 ${isLoadingGraphAnalytics ? 'animate-spin' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                        />
                      </svg>
                      Refresh
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="p-6 h-full overflow-hidden min-h-0">
                  <div className="h-full rounded-lg overflow-hidden">
                    <GraphVisualization 
                      data={graphVisualizationData}
                      selectedNodeId={selectedNodeId}
                      onNodeClick={(nodeId) => {
                        // Find the paper by ID and select it
                        const paper = papers.find(p => p.id === nodeId);
                        if (paper) {
                          setSelectedPaper(paper);
                          setSelectedNodeId(nodeId);
                        }
                      }}
                    />
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : analyticsData ? (
            <div className="flex items-center justify-center h-full">
              <Card className="w-96 bg-card/50 backdrop-blur-sm border-border/50">
                <CardContent className="p-8 text-center">
                  <BarChart3 className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    Graph View
                  </h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Network visualization will appear here when you have papers with connections
                  </p>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div className="text-center">
                      <div className="text-xl font-bold text-primary">{analyticsData.total_papers || 0}</div>
                      <div className="text-xs text-muted-foreground">Papers</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-primary">{analyticsData.total_collaborators || 0}</div>
                      <div className="text-xs text-muted-foreground">Collaborators</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <Card className="w-96 bg-card/50 backdrop-blur-sm border-border/50">
                <CardContent className="p-8 text-center">
                  <BarChart3 className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    No Network Data
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Upload papers to see their relationship network
                  </p>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}
 
      {/* Right Sidebar */}
      <div className={`transition-all duration-300 border-l border-border bg-card flex-shrink-0 ${rightSidebarCollapsed ? 'w-16' : 'w-96'} flex flex-col h-full min-h-0 overflow-hidden`}>
          {/* Header + Tab Toggle */}
          <div className="flex items-center p-2 gap-2 border-b border-border flex-shrink-0">
            {/* Tabs only when expanded */}
            {!rightSidebarCollapsed && (
              <>
                <Button
                  variant={rightTab === 'chat' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setRightTab('chat')}
                >
                  Chat
                </Button>
                <Button
                  variant={rightTab === 'insights' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setRightTab('insights')}
                >
                  Insights
                </Button>
              </>
            )}

            {/* Arrow aligned right */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setRightSidebarCollapsed(!rightSidebarCollapsed)}
              className="text-muted-foreground hover:text-foreground ml-auto"
            >
              {rightSidebarCollapsed ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </Button>
          </div>

          {!rightSidebarCollapsed && (
            <div className="flex flex-col h-full min-h-0 overflow-hidden">
              {/* Paper Context (only in chat tab) */}
              {rightTab === 'chat' && selectedPaper && (
                <div className="p-4 border-b border-border bg-muted/30 flex-shrink-0">
                  <h4 className="font-medium text-sm text-foreground mb-2">Discussing: {selectedPaper.title}</h4>
                  {selectedPaper.abstract && <p className="text-xs text-muted-foreground line-clamp-3">{selectedPaper.abstract}</p>}
                </div>
              )}

              {rightTab === 'chat' ? (
                <>
                {/* Chat Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
                  {chatMessages.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <MessageCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">Start a conversation about this paper</p>
                    </div>
                  ) : (
                    chatMessages.map((m) => (
                      <div key={m.id} className={`w-full ${m.type === 'user' ? 'text-right' : 'text-left'}`}>
                        <div className={`inline-block p-3 rounded-lg text-sm ${m.type === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground'} max-w-full`}>
                          {m.type === 'assistant' ? (
                            <div className="prose prose-sm prose-slate dark:prose-invert max-w-none">
                              <ReactMarkdown 
                                remarkPlugins={[remarkGfm]}
                                components={{
                                  h1: ({children}) => <h1 className="text-sm font-bold mb-2 mt-2 first:mt-0">{children}</h1>,
                                  h2: ({children}) => <h2 className="text-sm font-bold mb-2 mt-2 first:mt-0">{children}</h2>,
                                  h3: ({children}) => <h3 className="text-xs font-bold mb-1 mt-2 first:mt-0">{children}</h3>,
                                  p: ({children}) => <p className="mb-2 last:mb-0 text-sm leading-relaxed">{children}</p>,
                                  ul: ({children}) => <ul className="list-disc list-inside mb-2 space-y-1 text-sm">{children}</ul>,
                                  ol: ({children}) => <ol className="list-decimal list-inside mb-2 space-y-1 text-sm">{children}</ol>,
                                  li: ({children}) => <li className="leading-relaxed">{children}</li>,
                                  strong: ({children}) => <strong className="font-semibold">{children}</strong>,
                                  em: ({children}) => <em className="italic">{children}</em>,
                                  code: ({children}) => <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">{children}</code>,
                                  pre: ({children}) => <pre className="bg-muted p-2 rounded text-xs overflow-x-auto mb-2">{children}</pre>,
                                  blockquote: ({children}) => <blockquote className="border-l-4 border-muted-foreground pl-3 my-2 italic">{children}</blockquote>
                                }}
                              >
                                {m.content}
                              </ReactMarkdown>
                            </div>
                          ) : (
                            <span className="whitespace-pre-wrap break-words">{m.content}</span>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                  {isProcessingMessage && (
                    <div className="flex justify-start">
                      <div className="bg-muted text-foreground p-3 rounded-lg text-sm flex space-x-1">
                        <div className="animate-bounce w-2 h-2 bg-current rounded-full"></div>
                        <div className="animate-bounce w-2 h-2 bg-current rounded-full" style={{ animationDelay: '0.1s' }}></div>
                        <div className="animate-bounce w-2 h-2 bg-current rounded-full" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Chat Input */}
                <div className="p-4 border-t border-border flex-shrink-0">
                  <div className="flex space-x-2">
                    <Input
                      placeholder={selectedPaper ? 'Ask about this paper...' : 'Select a paper to start chatting...'}
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                      disabled={!selectedPaper || isProcessingMessage}
                      className="flex-1"
                    />
                    <Button onClick={handleSendMessage} disabled={!chatInput.trim() || !selectedPaper || isProcessingMessage} size="sm">
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                </>
              ) : (
                /* Insights Tab */
                <div className="flex-1 p-4 overflow-auto min-h-0">
                  {isLoadingDiagnostics ? (
                    <div className="flex items-center justify-center h-32">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                    </div>
                  ) : diagnosticsData ? (
                    <div className="space-y-6 text-sm max-w-full">
                      {/* Summary */}
                      {diagnosticsData.summary && (
                        <div className="w-full">
                          <h4 className="font-semibold text-foreground mb-2 flex items-center">
                            <span className="w-2 h-2 bg-primary rounded-full mr-2"></span>
                            Summary
                          </h4>
                          {renderDiagnosticContent(diagnosticsData.summary)}
                        </div>
                      )}

                      {/* Method */}
                      {diagnosticsData.method && (
                        <div className="w-full">
                          <h4 className="font-semibold text-foreground mb-2 flex items-center">
                            <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                            Methodology
                          </h4>
                          {renderDiagnosticContent(diagnosticsData.method)}
                        </div>
                      )}

                      {/* Dataset */}
                      {diagnosticsData.dataset && (
                        <div className="w-full">
                          <h4 className="font-semibold text-foreground mb-2 flex items-center">
                            <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                            Dataset
                          </h4>
                          {renderDiagnosticContent(diagnosticsData.dataset)}
                        </div>
                      )}

                      {/* Key Highlights */}
                      {diagnosticsData.highlights && (
                        <div className="w-full">
                          <h4 className="font-semibold text-foreground mb-2 flex items-center">
                            <span className="w-2 h-2 bg-yellow-500 rounded-full mr-2"></span>
                            Key Highlights
                          </h4>
                          {renderDiagnosticContent(diagnosticsData.highlights)}
                        </div>
                      )}

                      {/* Contributions */}
                      {diagnosticsData.contributions && (
                        <div className="w-full">
                          <h4 className="font-semibold text-foreground mb-2 flex items-center">
                            <span className="w-2 h-2 bg-purple-500 rounded-full mr-2"></span>
                            Contributions
                          </h4>
                          {renderDiagnosticContent(diagnosticsData.contributions)}
                        </div>
                      )}

                      {/* Strengths */}
                      {diagnosticsData.strengths && (
                        <div className="w-full">
                          <h4 className="font-semibold text-foreground mb-2 flex items-center">
                            <span className="w-2 h-2 bg-emerald-500 rounded-full mr-2"></span>
                            Strengths
                          </h4>
                          {renderDiagnosticContent(diagnosticsData.strengths)}
                        </div>
                      )}

                      {/* Limitations/Weaknesses */}
                      {(diagnosticsData.limitations || diagnosticsData.weakness) && (
                        <div className="w-full">
                          <h4 className="font-semibold text-foreground mb-2 flex items-center">
                            <span className="w-2 h-2 bg-orange-500 rounded-full mr-2"></span>
                            Limitations
                          </h4>
                          {renderDiagnosticContent(diagnosticsData.limitations || diagnosticsData.weakness)}
                        </div>
                      )}

                      {/* Future Scope */}
                      {diagnosticsData.future_scope && (
                        <div className="w-full">
                          <h4 className="font-semibold text-foreground mb-2 flex items-center">
                            <span className="w-2 h-2 bg-indigo-500 rounded-full mr-2"></span>
                            Future Research
                          </h4>
                          {renderDiagnosticContent(diagnosticsData.future_scope)}
                        </div>
                      )}
                    </div>
                  ) : selectedPaper ? (
                    <div className="flex flex-col items-center justify-center h-32 text-center">
                      <FileText className="h-8 w-8 mb-2 text-muted-foreground opacity-50" />
                      <p className="text-sm text-muted-foreground">
                        No diagnostics available for this paper.
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Diagnostics will be generated automatically when available.
                      </p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-32 text-center">
                      <FileText className="h-8 w-8 mb-2 text-muted-foreground opacity-50" />
                      <p className="text-sm text-muted-foreground">
                        Select a paper to view insights.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* Selection Dialog */}
        <Dialog open={showSelectionDialog} onOpenChange={setShowSelectionDialog}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>Ask about selected text (Page {selectedText?.page})</DialogTitle>
              <DialogDescription>
                <div className="mt-2 p-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg text-sm">
                  <span className="font-medium text-green-800 dark:text-green-200">⚡ Quick workflow:</span>
                  <ol className="text-xs text-green-600 dark:text-green-300 mt-1 list-decimal list-inside space-y-1">
                    <li>Copy the text you want to ask about from the PDF</li>
                    <li>Paste it below and type your question</li>
                    <li>Get instant AI insights!</li>
                  </ol>
                </div>
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <label htmlFor="selectedText" className="text-sm font-medium mb-2 block text-foreground flex items-center gap-2">
                    📄 Selected text
                    <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded">Paste here</span>
                  </label>
                  <Textarea
                    id="selectedText"
                    placeholder="Ctrl+C from PDF, then Ctrl+V here..."
                    value={selectedText?.text || ""}
                    onChange={(e) => setSelectedText(prev => prev ? {...prev, text: e.target.value} : {text: e.target.value, page: currentPage})}
                    className="min-h-[80px] resize-none font-mono text-sm bg-background border-2 border-dashed border-primary/30 focus:border-primary"
                    autoFocus
                  />
                </div>
                
                <div>
                  <label htmlFor="question" className="text-sm font-medium mb-2 block text-foreground flex items-center gap-2">
                    ❓ Your question
                    <span className="text-xs bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 px-2 py-0.5 rounded">Fast & smart</span>
                  </label>
                  <Textarea
                    id="question"
                    placeholder="Ask anything: 'Explain this', 'Summarize', 'What's the main point?', 'How does this work?'"
                    value={selectionComment}
                    onChange={(e) => setSelectionComment(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                        e.preventDefault();
                        if (selectionComment.trim() && selectedText?.text?.trim() && !isProcessingMessage) {
                          handleSendSelectionToChat();
                        }
                      }
                    }}
                    className="min-h-[80px] resize-none focus:border-primary"
                  />
                </div>
              </div>
            </div>
            <DialogFooter className="gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setShowSelectionDialog(false);
                  setSelectedText(null);
                  setSelectionComment("");
                  setShowAddToChat(false);
                  setSelectionPosition(null);
                  setShowSelectionHint(false);
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSendSelectionToChat}
                disabled={!selectionComment.trim() || !selectedText?.text?.trim() || isProcessingMessage}
                className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white"
              >
                {isProcessingMessage ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></div>
                    Analyzing...
                  </>
                ) : (
                  <>
                    ⚡ Ask AI
                    <span className="ml-2 text-xs opacity-75">(Ctrl+Enter)</span>
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
    </div>
  );
} 