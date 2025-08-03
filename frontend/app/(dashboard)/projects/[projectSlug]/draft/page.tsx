"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import dynamic from 'next/dynamic';
import { 
  draftApi, 
  type LaTeXFileStructure, 
  type BranchResponse, 
  type CompilationStatus,
  type LaTeXTemplate,
  type LaTeXFile,
  type FileTreeResponse,
  type ProjectFile
} from "@/lib/api/draft-api";
import { projectsApi } from "@/lib/api/projects-api";
import { agenticApi } from "@/lib/api/agentic-api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { 
  Search, 
  MessageCircle, 
  FileText,
  ChevronLeft,
  ChevronRight,
  Upload,
  Send,
  Download,
  RefreshCw,
  FolderOpen,
  Folder,
  Plus,
  MoreHorizontal,
  Code,
  Image,
  BookOpen,
  Palette,
  ChevronDown,
  ChevronUp,
  Type,
  Eye,
  EyeOff,
  FileIcon,
  File,
  Play,
  Settings
} from "lucide-react";

// Dynamically import Monaco Editor to avoid SSR issues
const Editor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => <div className="h-full bg-papers-secondary flex items-center justify-center">Loading editor...</div>
});

// Types
interface Project {
  id: string;
  name: string;
  description: string | null;
  slug: string | null;
}

interface FileNode {
  id: string;
  name: string;
  type: 'file' | 'folder';
  icon: string;
  path: string;
  isExpanded?: boolean;
  isSelected?: boolean;
  children?: FileNode[];
  size?: number;
  last_modified?: string;
}

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface LaTeXProject {
  id: string;
  name: string;
  template: string;
  created_at: string;
  created_by: string;
  files?: Array<{
    id: string;
    path: string;
    name: string;
    type: string;
    size: number;
    updated_at: string;
  }>;
}

// File Tree Component
const FileTreeItem: React.FC<{
  node: FileNode;
  level: number;
  onSelect: (node: FileNode) => void;
  onToggle: (node: FileNode) => void;
  onAdd: (node: FileNode) => void;
}> = ({ node, level, onSelect, onToggle, onAdd }) => {
  const getFileIcon = (fileName: string, type: string) => {
    if (type === 'folder') return <Folder size={16} className="text-papers-muted" />;
    
    const ext = fileName.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'tex':
        return <Code size={16} className="text-papers-muted" />;
      case 'pdf':
        return <FileText size={16} className="text-papers-muted" />;
      case 'bib':
        return <BookOpen size={16} className="text-papers-muted" />;
      case 'cls':
      case 'sty':
        return <Palette size={16} className="text-papers-muted" />;
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'svg':
        return <Image size={16} className="text-papers-muted" />;
      default:
        return <File size={16} className="text-papers-muted" />;
    }
  };

  return (
    <div>
      <div 
        className={`flex items-center gap-2 px-3 py-2 hover:bg-papers-selected cursor-pointer group ${
          node.isSelected ? 'bg-papers-selected text-papers-primary' : 'text-papers-primary'
        }`}
        style={{ paddingLeft: `${8 + level * 16}px` }}
        onClick={() => onSelect(node)}
      >
        {node.type === 'folder' && (
          <button 
            onClick={(e) => {
              e.stopPropagation();
              onToggle(node);
            }}
            className="p-1 hover:bg-papers-secondary rounded"
          >
            {node.isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
        )}
        {node.type === 'file' && <div className="w-4" />}
        
        {getFileIcon(node.name, node.type)}
        
        <span className="text-sm font-medium flex-1">{node.name}</span>
        
        {node.type === 'folder' && (
          <button 
            onClick={(e) => {
              e.stopPropagation();
              onAdd(node);
            }}
            className="opacity-0 group-hover:opacity-100 p-1 hover:bg-papers-secondary rounded"
          >
            <Plus size={12} />
          </button>
        )}
      </div>
      
      {node.type === 'folder' && node.isExpanded && node.children && (
        <div>
          {node.children.map((child) => (
            <FileTreeItem
              key={child.id}
              node={child}
              level={level + 1}
              onSelect={onSelect}
              onToggle={onToggle}
              onAdd={onAdd}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// Main Draft Page Component
export default function DraftPage() {
  const router = useRouter();
  const params = useParams();
  const projectSlug = params.projectSlug as string;
  
  // State
  const [project, setProject] = useState<Project | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fileStructure, setFileStructure] = useState<FileNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<FileNode | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [branches, setBranches] = useState<BranchResponse[]>([]);
  const [currentBranch, setCurrentBranch] = useState<BranchResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'latex' | 'canvas' | 'comments'>('latex');
  const [isCompiling, setIsCompiling] = useState(false);
  const [compilationStatus, setCompilationStatus] = useState<CompilationStatus | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [zoomLevel, setZoomLevel] = useState(100);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [latexProjects, setLatexProjects] = useState<LaTeXProject[]>([]);
  const [currentLatexProject, setCurrentLatexProject] = useState<LaTeXProject | null>(null);
  const [templates, setTemplates] = useState<LaTeXTemplate[]>([]);
  const [showNewProjectDialog, setShowNewProjectDialog] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<string>('article');
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [showBranchList, setShowBranchList] = useState(false);
  const [showAddFileDialog, setShowAddFileDialog] = useState(false);
  const [showBranchMenu, setShowBranchMenu] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [newFileType, setNewFileType] = useState<'file' | 'folder'>('file');
  const [addFileParent, setAddFileParent] = useState<FileNode | null>(null);
  
  // Fetch project ID from slug
  useEffect(() => {
    const fetchProjectId = async () => {
      if (projectSlug) {
        try {
          const projectsResponse = await projectsApi.getProjects();
          const foundProject = projectsResponse.projects.find((p: any) => 
            p.slug === projectSlug || p.id === projectSlug
          );
          
          if (foundProject) {
            setProject(foundProject);
            setProjectId(foundProject.id);
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

  // Load draft data when project ID is available
  useEffect(() => {
    const loadData = async () => {
      if (!projectId) return;
      
      try {
        setIsLoading(true);
        
        // Load LaTeX templates
        const templatesResponse = await draftApi.getLaTeXTemplates();
        setTemplates(templatesResponse.templates);
        
        // Load existing LaTeX projects
        try {
          console.log('Loading LaTeX projects for project:', projectId);
          const latexProjectsResponse = await draftApi.getLaTeXProjects(projectId);
          console.log('LaTeX projects response:', latexProjectsResponse);
          
          if (latexProjectsResponse.success) {
            setLatexProjects(latexProjectsResponse.latex_projects || []);
           
            if (latexProjectsResponse.latex_projects && latexProjectsResponse.latex_projects.length > 0) {
              console.log('Found existing LaTeX projects:', latexProjectsResponse.latex_projects.length);
              const firstProject = latexProjectsResponse.latex_projects[0];
            setCurrentLatexProject(firstProject);
              await loadLatexProjectData(firstProject.id, firstProject.files);
          } else {
            // No LaTeX projects exist, show create dialog
              console.log('No LaTeX projects found in successful response, showing create dialog');
            setShowNewProjectDialog(true);
            }
          } else {
            // API call succeeded but returned error
            console.error('LaTeX projects API returned error:', latexProjectsResponse);
            // If it's an authentication error, don't show error state, just show create dialog
            if (latexProjectsResponse.error && latexProjectsResponse.error.includes('authentication')) {
              console.log('Authentication issue detected, showing create dialog');
              setShowNewProjectDialog(true);
            } else {
              setError('Failed to load LaTeX projects');
            }
          }
        } catch (latexError) {
          console.error('LaTeX projects API call failed:', latexError);
          // Check if it's an authentication error
          if (latexError instanceof Error && latexError.message.includes('Authentication')) {
            console.log('Authentication error caught, showing create dialog');
          setShowNewProjectDialog(true);
          } else {
            setError('Failed to connect to API for LaTeX projects');
          }
        }
        
        // Load branches
        try {
          const branchesResponse = await draftApi.getBranches(projectId);
          setBranches(branchesResponse.branches);
          
          // Set current branch (find main or first available)
          const mainBranch = branchesResponse.branches.find(b => b.name.toLowerCase() === 'main') || branchesResponse.branches[0];
          if (mainBranch) {
            setCurrentBranch(mainBranch);
          }
        } catch (branchError) {
          console.log('Branches not available yet');
          // Create a default branch if none exist
          try {
            const newBranchResponse = await draftApi.createBranch(projectId, {
              name: 'main',
              description: 'Main branch for LaTeX editing'
            });
            setCurrentBranch(newBranchResponse.branch);
            setBranches([newBranchResponse.branch]);
          } catch (createBranchError) {
            console.error('Failed to create default branch:', createBranchError);
          }
        }
        
      } catch (error) {
        console.error('Error loading draft data:', error);
        setError('Failed to load draft data');
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [projectId]);

  // Load LaTeX project data
  const loadLatexProjectData = async (latexProjectId: string, initialFiles?: Array<any>) => {
    if (!projectId) return;
    
    try {
      // First, use files passed explicitly (preferred)
      if (initialFiles && initialFiles.length > 0) {
        console.log('Using files passed to loader:', initialFiles);
        const convertedStructure = convertFilesToFileNodes(initialFiles);
        console.log('Converted file structure (explicit):', convertedStructure);
        setFileStructure(convertedStructure);
        const firstFile = findFirstFile(convertedStructure);
        if (firstFile) await handleFileSelect(firstFile);
        return;
      }

      // Otherwise, try to find in already loaded LaTeX projects state
      const currentProject = latexProjects.find(p => p.id === latexProjectId);
      if (currentProject && currentProject.files) {
        console.log('Using files from already loaded LaTeX project:', currentProject.files);
        const convertedStructure = convertFilesToFileNodes(currentProject.files);
        console.log('Converted file structure from LaTeX project:', convertedStructure);
        setFileStructure(convertedStructure);
        
        // Select first file if available
        const firstFile = findFirstFile(convertedStructure);
        if (firstFile) {
          await handleFileSelect(firstFile);
        }
        return;
      }
      
      // Fallback: Load file structure via API
      const fileStructureResponse = await draftApi.getLaTeXFiles(projectId, latexProjectId);
      const convertedStructure = convertToFileNodes(fileStructureResponse.structure);
      setFileStructure(convertedStructure);
      
      // Select first file if available
      const firstFile = findFirstFile(convertedStructure);
      if (firstFile) {
        await handleFileSelect(firstFile);
      }
    } catch (error) {
      console.error('Error loading LaTeX project data:', error);
      // Fallback to general project file tree
      try {
        const fileTreeResponse = await draftApi.getProjectFileTree(projectId);
        const convertedTree = convertProjectFileTreeToNodes(fileTreeResponse.tree);
        setFileStructure([convertedTree]);
      } catch (treeError) {
        console.error('Error loading project file tree:', treeError);
      }
    }
  };

  // Utility to get LaTeX root folder name (e.g. "main")
  const getLatexRoot = () => currentLatexProject?.name || 'main';

  // Convert LaTeX project files to FileNode format (hide root folder)
  const convertFilesToFileNodes = (files: LaTeXProject['files']): FileNode[] => {
    if (!files || !Array.isArray(files)) return [];

    const fileMap = new Map<string, FileNode>();
    const rootNodes: FileNode[] = [];

    const latexRoot = getLatexRoot();

    // Sort for deterministic tree
    const sorted = files.sort((a, b) => a.path.localeCompare(b.path));

    sorted.forEach((file) => {
      // Strip the root folder (e.g. "main/")
      const relPath = file.path.startsWith(`${latexRoot}/`) ? file.path.slice(latexRoot.length + 1) : file.path;
      const parts = relPath.split('/').filter(Boolean);

      let currentPath = '';
      parts.forEach((part, idx) => {
        const parentPath = currentPath;
        currentPath = currentPath ? `${currentPath}/${part}` : part;

        if (!fileMap.has(currentPath)) {
          const isFile = idx === parts.length - 1;
          const node: FileNode = {
            id: file.path,          // keep full path for uniqueness
            name: part,
            type: isFile ? 'file' : 'folder',
            icon: isFile ? getFileIcon(part) : 'Folder',
            path: relPath,          // API calls use relative path (no root)
            isExpanded: false,
            children: isFile ? undefined : [],
            size: isFile ? file.size : undefined,
            last_modified: file.updated_at,
          };

          fileMap.set(currentPath, node);

          if (parentPath && fileMap.has(parentPath)) {
            const parent = fileMap.get(parentPath)!;
            parent.children!.push(node);
          } else if (!parentPath) {
            rootNodes.push(node);
          }
        }
      });
    });

    return rootNodes;
  };

  // Convert file tree structures to FileNode format
  const convertToFileNodes = (structure: any): FileNode[] => {
    if (!structure) return [];
    // If backend returns a single object instead of array, wrap it
    const items = Array.isArray(structure) ? structure : [structure];

    return items.map((item: any, index: number) => ({
      id: item.path || `${item.name}-${index}`,
      name: item.name,
      type: item.type,
      icon: item.type === 'directory' ? 'Folder' : getFileIcon(item.name),
      path: item.path,
      isExpanded: false,
      children: item.children ? convertToFileNodes(item.children) : undefined,
      size: item.metadata?.size,
      last_modified: item.metadata?.last_modified
    }));
  };

  const convertProjectFileTreeToNodes = (tree: any): FileNode => {
    if (!tree) {
      return {
        id: 'root',
        name: 'root',
        type: 'folder',
        icon: 'Folder',
        path: '',
        isExpanded: true,
        children: []
      } as FileNode;
    }

    return {
      id: tree.path || tree.name,
      name: tree.name,
      type: tree.type === 'folder' ? 'folder' : 'file',
      icon: tree.type === 'folder' ? 'Folder' : getFileIcon(tree.name),
      path: tree.path,
      isExpanded: tree.type === 'folder',
      children: tree.children ? tree.children.map(convertProjectFileTreeToNodes) : undefined,
      size: tree.size
    };
  };

  const getFileIcon = (fileName: string): string => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'tex': return 'Code';
      case 'pdf': return 'FileText';
      case 'bib': return 'BookOpen';
      case 'cls':
      case 'sty': return 'Palette';
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'svg': return 'Image';
      default: return 'FileText';
    }
  };

  const findFirstFile = (nodes: FileNode[]): FileNode | null => {
    for (const node of nodes) {
      if (node.type === 'file') return node;
      if (node.children) {
        const found = findFirstFile(node.children);
        if (found) return found;
      }
    }
    return null;
  };

  // File operations
  const handleFileSelect = async (node: FileNode) => {
    if (node.type === 'file' && projectId && currentLatexProject) {
      setFileStructure(prev => 
        updateNodeSelection(prev, node.id)
      );
      setSelectedFile(node);
      
      try {
        // Determine LaTeX root folder (e.g. "main")
        const latexRoot = getLatexRoot();

        // Strip the root prefix before calling the API – backend auto-prepends it
        let apiPath = node.path;
        if (apiPath.startsWith(`${latexRoot}/`)) {
          apiPath = apiPath.substring(latexRoot.length + 1);
        }

        const fileContentResponse = await draftApi.getLaTeXFileContent(
          projectId,
          currentLatexProject.id,
          apiPath
        );
        setFileContent(fileContentResponse.content);
      } catch (error) {
        console.error('Error loading file content:', error);
        // Fallback content
        if (node.path.endsWith('.tex')) {
          setFileContent('\\documentclass{article}\n\\begin{document}\n\n% Content for ' + node.name + '\n\n\\end{document}');
        } else {
          setFileContent('% ' + node.name + ' content');
        }
      }
    }
  };

  const updateNodeSelection = (nodes: FileNode[], selectedId: string): FileNode[] => {
    return nodes.map(node => ({
      ...node,
      isSelected: node.id === selectedId,
      children: node.children ? updateNodeSelection(node.children, selectedId) : undefined
    }));
  };

  const handleFileToggle = (node: FileNode) => {
    setFileStructure(prev => 
      updateNodeExpansion(prev, node.id)
    );
  };

  const updateNodeExpansion = (nodes: FileNode[], nodeId: string): FileNode[] => {
    return nodes.map(node => {
      if (node.id === nodeId) {
        return { ...node, isExpanded: !node.isExpanded };
      }
      return {
        ...node,
        children: node.children ? updateNodeExpansion(node.children, nodeId) : undefined
      };
    });
  };

  const handleFileAdd = (node: FileNode) => {
    setAddFileParent(node);
    setShowAddFileDialog(true);
  };

  const handleCreateFile = async () => {
    if (!newFileName.trim() || !addFileParent || !projectId || !currentBranch) return;
    
    try {
      const fileName = newFileName.trim();
      const latexRoot = getLatexRoot();
      const parentPath = addFileParent.path;
      const dirPath = parentPath || latexRoot; // if root, use latex root
      const newFilePath = parentPath ? `${parentPath}/${fileName}` : `${latexRoot}/${fileName}`;
      
      if (newFileType === 'file') {
        // Create a new file using branch API for proper Git integration
        const defaultContent = fileName.endsWith('.tex') 
          ? `% ${fileName}\n\\section{${fileName.replace('.tex', '')}}\n\n% Your content here\n`
          : `% ${fileName}\n\n% Your content here\n`;
        
        // Map file extensions to valid backend file types
        const getValidFileType = (filename: string): string => {
          const extension = filename.split('.').pop()?.toLowerCase() || '';
          const validTypes = ['tex', 'bib', 'sty', 'cls', 'pdf', 'png', 'jpg', 'txt', 'md'];
          
          // Map common extensions to valid types
          const extensionMap: Record<string, string> = {
            'latex': 'tex',
            'jpeg': 'jpg',
            'markdown': 'md',
            'text': 'txt',
            'gitkeep': 'txt',
            'gitignore': 'txt',
            'env': 'txt',
            'log': 'txt',
            'yml': 'txt',
            'yaml': 'txt',
            'json': 'txt',
            'xml': 'txt',
          };
          
          // Use mapped extension or check if it's already valid
          const mappedType = extensionMap[extension] || extension;
          return validTypes.includes(mappedType) ? mappedType : 'txt';
        };
        
        const fileType = getValidFileType(fileName);
        
        await draftApi.createBranchFile(projectId, currentBranch.id, {
          file_name: fileName,
          file_path: dirPath,
          file_type: fileType,
          content: defaultContent,
          encoding: 'utf-8'
        });
      } else {
        // Create a folder by creating a .gitkeep file in it
        const folderPath = parentPath ? `${parentPath}/${fileName}` : `${latexRoot}/${fileName}`;
        await draftApi.createBranchFile(projectId, currentBranch.id, {
            file_name: '.gitkeep',
            file_path: folderPath,
            file_type: 'txt',
            content: '',
            encoding: 'utf-8'
        });
      }
      
            // Refresh file structure by reloading LaTeX project data
      if (currentLatexProject) {
        console.log('Refreshing files by reloading LaTeX project data');
        await loadLatexProjectData(currentLatexProject.id);
      } else {
        console.warn('No current LaTeX project available for refresh');
      }
      
      // Reset dialog
      setShowAddFileDialog(false);
      setNewFileName('');
      setNewFileType('file');
      setAddFileParent(null);
    } catch (error) {
      console.error('Error creating file:', error);
      // Show user-friendly error message
      alert('Failed to create file. Please try again.');
    }
  };

  const handleAddRootFile = () => {
    // Create a fake root node for adding files at root level
    const rootNode: FileNode = {
      id: 'root',
      name: 'root',
      type: 'folder',
      icon: 'Folder',
      path: '',
      isExpanded: true
    };
    handleFileAdd(rootNode);
  };

  // Save file content
  const handleSaveFile = async () => {
    if (!projectId || !currentLatexProject || !selectedFile) return;
    
    try {
      await draftApi.updateLaTeXFile(
        projectId,
        currentLatexProject.id,
        selectedFile.path,
        { content: fileContent, message: 'Updated from editor' }
      );
      console.log('File saved successfully');
    } catch (error) {
      console.error('Error saving file:', error);
    }
  };

  // Create new LaTeX project
  const handleCreateLatexProject = async () => {
    if (!projectId || !newProjectName.trim()) return;
    
    try {
      setIsCreatingProject(true);
      const response = await draftApi.createLaTeXProject(projectId, {
        template: selectedTemplate as any,
        name: newProjectName
      });
      
      const newProject = response.latex_project;
      setLatexProjects(prev => [...prev, newProject]);
      setCurrentLatexProject(newProject);
      setShowNewProjectDialog(false);
      setNewProjectName('');
      
      // Load the new project data
      await loadLatexProjectData(newProject.id);
    } catch (error) {
      console.error('Error creating LaTeX project:', error);
    } finally {
      setIsCreatingProject(false);
    }
  };

  // Compilation
  const handleCompile = async () => {
    if (!projectId || !currentLatexProject) return;
    // Determine the file to compile – must be a .tex file
    const mainCompileFile = (selectedFile && selectedFile.path.endsWith('.tex'))
      ? selectedFile.path
      : 'main.tex';

    // If no .tex file is selected and main.tex doesn't exist in file list, abort early
    if (!mainCompileFile) return;
    
    try {
      setIsCompiling(true);
      
      const compilationResponse = await draftApi.compileLaTeX(
        projectId,
        currentLatexProject.id,
        { main_file: mainCompileFile }
      );
      
      // Poll for compilation status
      const checkStatus = async () => {
        try {
          const statusResponse = await draftApi.getCompilationStatus(
            projectId, 
            currentLatexProject.id, 
            compilationResponse.compilation_id
          );
          
          setCompilationStatus(statusResponse);
          
          if (statusResponse.compilation.status === 'completed') {
            // Download and set PDF URL
            try {
              const pdfBlob = await draftApi.downloadCompiledPDF(
                projectId,
                currentLatexProject.id,
                compilationResponse.compilation_id
              );
              const pdfUrl = URL.createObjectURL(pdfBlob);
              setPdfUrl(pdfUrl);
            } catch (downloadError) {
              console.error('Error downloading PDF:', downloadError);
            }
            setIsCompiling(false);
          } else if (statusResponse.compilation.status === 'failed') {
            setIsCompiling(false);
            console.error('Compilation failed:', statusResponse.compilation.errors);
          } else {
            // Continue polling
            setTimeout(checkStatus, 2000);
          }
        } catch (error) {
          console.error('Error checking compilation status:', error);
          setIsCompiling(false);
        }
      };
      
      checkStatus();
      
    } catch (error) {
      console.error('Compilation error:', error);
      if (error instanceof Error) {
        console.error('Error message:', error.message);
        // Try to extract more details from the error
        try {
          const errorData = JSON.parse(error.message);
          console.error('Backend error details:', errorData);
        } catch (parseError) {
          console.error('Could not parse error as JSON:', error.message);
        }
      }
      setIsCompiling(false);
    }
  };

  // Chat
  const handleSendMessage = async () => {
    if (!currentMessage.trim() || !projectId) return;
    
    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: currentMessage,
      timestamp: new Date().toISOString()
    };
    
    setChatMessages(prev => [...prev, newMessage]);
    setCurrentMessage('');
    
    try {
      // Use agentic API for AI response
      const response = await agenticApi.simpleChat(projectId, { message: currentMessage });
      
      const aiResponse: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString()
      };
      setChatMessages(prev => [...prev, aiResponse]);
    } catch (error) {
      console.error('Error sending message:', error);
      // Fallback response
      setTimeout(() => {
        const aiResponse: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: 'I can help you with LaTeX editing. What would you like to know?',
          timestamp: new Date().toISOString()
        };
        setChatMessages(prev => [...prev, aiResponse]);
      }, 1000);
    }
  };

  if (isLoading) {
    return (
      <div className="h-screen bg-papers-primary flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-papers-primary mx-auto mb-4"></div>
          <p className="text-papers-muted">Loading draft...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen bg-papers-primary flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-4">{error}</p>
          <Button onClick={() => router.push('/projects')}>
            Back to Projects
          </Button>
        </div>
      </div>
    );
  }

  // New project dialog
  if (showNewProjectDialog) {
    return (
      <div className="h-screen bg-papers-primary flex items-center justify-center">
        <Card className="w-96">
          <CardHeader>
            <CardTitle>Create LaTeX Project</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Project Name</label>
              <Input
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="Enter project name"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Template</label>
              <select
                value={selectedTemplate}
                onChange={(e) => setSelectedTemplate(e.target.value)}
                className="w-full p-2 border rounded"
              >
                <option value="article">Article</option>
                <option value="report">Report</option>
                <option value="book">Book</option>
                <option value="beamer">Beamer (Presentation)</option>
              </select>
            </div>
            <div className="flex gap-2">
              <Button 
                onClick={handleCreateLatexProject}
                disabled={!newProjectName.trim() || isCreatingProject}
                className="flex-1"
              >
                {isCreatingProject ? 'Creating...' : 'Create Project'}
              </Button>
              <Button 
                variant="outline"
                onClick={() => router.push('/projects')}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Add file dialog
  if (showAddFileDialog) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <Card className="w-96">
          <CardHeader>
            <CardTitle>Add {newFileType === 'file' ? 'File' : 'Folder'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Type</label>
              <div className="flex gap-2 mt-2">
                <button
                  onClick={() => setNewFileType('file')}
                  className={`px-3 py-2 rounded text-sm ${
                    newFileType === 'file' ? 'bg-papers-button-primary text-papers-button-primary' : 'bg-papers-secondary text-papers-muted'
                  }`}
                >
                  File
                </button>
                <button
                  onClick={() => setNewFileType('folder')}
                  className={`px-3 py-2 rounded text-sm ${
                    newFileType === 'folder' ? 'bg-papers-button-primary text-papers-button-primary' : 'bg-papers-secondary text-papers-muted'
                  }`}
                >
                  Folder
                </button>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">Name</label>
              <Input
                value={newFileName}
                onChange={(e) => setNewFileName(e.target.value)}
                placeholder={newFileType === 'file' ? 'example.tex' : 'folder-name'}
                onKeyPress={(e) => e.key === 'Enter' && handleCreateFile()}
              />
            </div>
            {addFileParent && (
              <div className="text-sm text-papers-muted">
                Will be created in: {addFileParent.path || 'root'}
              </div>
            )}
            <div className="flex gap-2">
              <Button 
                onClick={handleCreateFile}
                disabled={!newFileName.trim()}
                className="flex-1"
              >
                Create {newFileType === 'file' ? 'File' : 'Folder'}
              </Button>
              <Button 
                variant="outline"
                onClick={() => {
                  setShowAddFileDialog(false);
                  setNewFileName('');
                  setNewFileType('file');
                  setAddFileParent(null);
                }}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="h-screen bg-papers-primary flex flex-col">
      {/* Top Navigation */}
      <div className="bg-papers-sidebar border-b border-papers-medium px-4 py-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-semibold text-papers-primary">Draft</h1>
              <button
                onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
                className="p-1 hover:bg-papers-selected rounded"
              >
                {isSidebarCollapsed ? <Eye size={20} className="text-papers-muted" /> : <EyeOff size={20} className="text-papers-muted" />}
              </button>
            </div>
            
            <div className="flex items-center gap-2">
              <button 
                onClick={handleSaveFile}
                disabled={!selectedFile || !fileContent}
                className="p-3 bg-papers-secondary border border-papers-medium rounded-xl hover:bg-papers-selected disabled:opacity-50"
              >
                <Download size={20} className="text-papers-secondary" />
              </button>
              <button className="p-3 bg-papers-secondary border border-papers-medium rounded-xl hover:bg-papers-selected">
                <MessageCircle size={20} className="text-papers-secondary" />
              </button>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <ChevronUp size={20} className="text-papers-muted" />
              <div className="px-2 py-1 bg-papers-secondary border border-papers-dark rounded-xl">
                <span className="text-sm text-papers-secondary">{currentPage}</span>
              </div>
              <span className="text-sm text-papers-secondary">of {totalPages} pages</span>
              <ChevronDown size={20} className="text-papers-muted" />
            </div>
            
            <Button 
              onClick={handleCompile}
              disabled={isCompiling || !currentLatexProject || !(selectedFile && selectedFile.path.endsWith('.tex'))}
              className="bg-papers-button-primary text-papers-button-primary hover:bg-papers-button-primary/90 gap-2"
            >
              <RefreshCw size={16} className={isCompiling ? "animate-spin" : ""} />
              {isCompiling ? 'Compiling...' : 'Compile'}
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 min-h-0">
        <PanelGroup direction="horizontal" className="h-full">
          {/* Left Sidebar */}
          {!isSidebarCollapsed && (
            <Panel defaultSize={20} minSize={15} maxSize={30}>
              <div className="h-full bg-papers-sidebar border-r border-papers-medium flex flex-col">
            {/* Sidebar Header */}
            <div className="p-4 border-b border-papers-medium">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold text-papers-primary">Draft</h2>
                <button className="p-1 hover:bg-papers-selected rounded">
                  <EyeOff size={16} className="text-papers-muted" />
                </button>
              </div>
              
              <div className="mb-6">
                <div className="w-full h-px bg-papers-medium" />
              </div>
              
              {currentLatexProject && (
                <Badge variant="outline" className="text-xs bg-papers-selected text-papers-secondary border-papers-medium">
                  {currentLatexProject.name}
                </Badge>
              )}
            </div>

            {/* Files Section */}
            <div className="flex-1 p-4 overflow-y-auto">
              <div className="mb-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-bold text-papers-primary">Files</h3>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleAddRootFile}
                      className="p-2 bg-papers-secondary border border-papers-medium rounded-lg hover:bg-papers-selected"
                      title="Add file"
                    >
                      <Plus size={16} className="text-papers-muted" />
                    </button>
                  <div className="p-2 bg-papers-secondary border border-papers-medium rounded-lg hover:bg-papers-selected">
                    <Search size={16} className="text-papers-muted" />
                    </div>
                  </div>
                </div>
                
                <div className="space-y-1">
                  {fileStructure.length > 0 ? (
                    fileStructure.map((node) => (
                      <div key={node.id} className="group">
                        <FileTreeItem
                          node={node}
                          level={0}
                          onSelect={handleFileSelect}
                          onToggle={handleFileToggle}
                          onAdd={handleFileAdd}
                        />
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-papers-muted py-4">
                      {currentBranch ? (
                        <div>
                          <div>No files in branch: {currentBranch.name}</div>
                          <div className="text-xs mt-1">Branch ID: {currentBranch.id}</div>
                    </div>
                      ) : (
                        "Loading files..."
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Branch Info */}
            <div className="p-4 bg-papers-secondary border-t border-papers-medium relative">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-bold text-papers-primary">Current Branch</span>
                <div className="relative">
                    <button
                    onClick={() => setShowBranchMenu(!showBranchMenu)}
                    className="p-1 hover:bg-papers-selected rounded"
                  >
                    <MoreHorizontal size={16} className="text-papers-muted" />
                    </button>
                  {showBranchMenu && (
                    <div className="absolute right-0 mt-2 w-48 bg-papers-sidebar border border-papers-medium rounded-xl shadow-lg z-20">
                    <button
                        onClick={async () => {
                          setShowBranchMenu(false);
                          if (!projectId) return;
                          
                          const branchName = prompt('Enter new branch name:');
                          if (branchName?.trim()) {
                            try {
                              const response = await draftApi.createBranch(projectId, {
                                name: branchName.trim(),
                                description: `Branch created from ${currentBranch?.name || 'main'}`
                              });
                              setBranches(prev => [...prev, response.branch]);
                              setCurrentBranch(response.branch);
                            } catch (error) {
                              console.error('Error creating branch:', error);
                              alert('Failed to create branch');
                            }
                          }
                        }}
                        className="w-full px-4 py-2 text-left text-sm hover:bg-papers-selected"
                      >
                        Create New Branch
                      </button>
                      <div className="border-t border-papers-medium my-1"></div>
                      {branches.map((branch) => (
                        <button
                          key={branch.id}
                          onClick={() => {
                            setCurrentBranch(branch);
                            setShowBranchMenu(false);
                          }}
                          className={`w-full px-4 py-2 text-left text-sm hover:bg-papers-selected ${
                            currentBranch?.id === branch.id ? 'bg-papers-selected' : ''
                          }`}
                        >
                          {branch.name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              
              {currentBranch && (
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-papers-secondary">{currentBranch.name}</span>
                  </div>
                  <div className="text-xs text-papers-muted">
                    ID: {currentBranch.id.substring(0, 8)}...
                  </div>
                </div>
              )}
            </div>
          </div>
        </Panel>
          )}

          <PanelResizeHandle className="w-2 bg-papers-medium hover:bg-papers-dark transition-colors" />

          {/* Main Editor Panel */}
          <Panel defaultSize={50} minSize={30}>
            <div className="h-full bg-papers-primary flex flex-col">
              {/* Editor Header */}
              <div className="bg-papers-sidebar border-b border-papers-medium px-4 py-3 flex-shrink-0">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {selectedFile && (
                      <>
                        <div className="flex items-center gap-2">
                          <Code size={16} className="text-papers-muted" />
                          <span className="text-sm font-medium text-papers-primary">
                            {selectedFile.name}
                          </span>
                        </div>
                        <Badge variant="outline" className="text-xs">
                          {selectedFile.path}
                        </Badge>
                      </>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Button
                      onClick={handleSaveFile}
                      disabled={!selectedFile || !fileContent}
                      size="sm"
                      variant="outline"
                    >
                      Save
                    </Button>
                    <Button
                      onClick={handleCompile}
                      disabled={isCompiling || !currentLatexProject || !(selectedFile && selectedFile.path.endsWith('.tex'))}
                      size="sm"
                    >
                      <Play size={14} className="mr-1" />
                      Compile
                    </Button>
                  </div>
                </div>
              </div>

              {/* Editor Content */}
              <div className="flex-1 min-h-0">
                {selectedFile ? (
                  <Editor
                    height="100%"
                    defaultLanguage="latex"
                    value={fileContent}
                    onChange={(value) => setFileContent(value || '')}
                    theme="vs-dark"
                    options={{
                      minimap: { enabled: false },
                      fontSize: 14,
                      lineNumbers: 'on',
                      wordWrap: 'on',
                      scrollBeyondLastLine: false,
                      automaticLayout: true,
                    }}
                  />
                ) : (
                  <div className="h-full flex items-center justify-center text-papers-muted">
                    <div className="text-center">
                      <FileText size={48} className="mx-auto mb-4 opacity-50" />
                      <p>Select a file to start editing</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </Panel>

          <PanelResizeHandle className="w-2 bg-papers-medium hover:bg-papers-dark transition-colors" />

          {/* Right Panel - Tabs */}
          <Panel defaultSize={30} minSize={20}>
            <div className="h-full bg-papers-primary flex flex-col">
              {/* Tab Navigation */}
              <div className="bg-papers-sidebar border-b border-papers-medium px-4 py-3 flex-shrink-0">
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setActiveTab('latex')}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      activeTab === 'latex'
                        ? 'bg-papers-button-primary text-papers-button-primary'
                        : 'text-papers-muted hover:text-papers-primary hover:bg-papers-selected'
                    }`}
                  >
                    <Eye size={16} className="inline mr-2" />
                    Preview
                  </button>
                  <button
                    onClick={() => setActiveTab('comments')}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      activeTab === 'comments'
                        ? 'bg-papers-button-primary text-papers-button-primary'
                        : 'text-papers-muted hover:text-papers-primary hover:bg-papers-selected'
                    }`}
                  >
                    <MessageCircle size={16} className="inline mr-2" />
                    Chat
                  </button>
                </div>
              </div>

              {/* Tab Content */}
              <div className="flex-1 min-h-0">
                {activeTab === 'latex' && (
                  <div className="h-full bg-papers-secondary flex flex-col">
                    {/* PDF Controls */}
                    {pdfUrl && (
                      <div className="p-4 border-b border-papers-medium">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-papers-primary">PDF Preview</span>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                              disabled={currentPage <= 1}
                              className="p-1 hover:bg-papers-selected rounded disabled:opacity-50"
                            >
                              <ChevronLeft size={16} />
                            </button>
                            <span className="text-sm text-papers-secondary">
                              {currentPage} / {totalPages}
                            </span>
                            <button
                              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                              disabled={currentPage >= totalPages}
                              className="p-1 hover:bg-papers-selected rounded disabled:opacity-50"
                            >
                              <ChevronRight size={16} />
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* PDF Viewer */}
                    <div className="flex-1 p-4">
                      {isCompiling ? (
                        <div className="h-full flex items-center justify-center">
                          <div className="text-center">
                            <RefreshCw size={32} className="mx-auto mb-4 animate-spin text-papers-muted" />
                            <p className="text-papers-muted">Compiling LaTeX...</p>
                          </div>
                        </div>
                      ) : pdfUrl ? (
                        <iframe
                          src={pdfUrl}
                          className="w-full h-full border-0 rounded-lg"
                          title="PDF Preview"
                        />
                      ) : (
                        <div className="h-full flex items-center justify-center text-papers-muted">
                          <div className="text-center">
                            <FileText size={48} className="mx-auto mb-4 opacity-50" />
                            <p>Compile your LaTeX to see preview</p>
                            <Button
                              onClick={handleCompile}
                              disabled={!currentLatexProject || !(selectedFile && selectedFile.path.endsWith('.tex'))}
                              className="mt-4"
                              size="sm"
                            >
                              <Play size={14} className="mr-2" />
                              Compile Now
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Compilation Status */}
                    {compilationStatus && (
                      <div className="p-4 border-t border-papers-medium">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <div
                              className={`w-2 h-2 rounded-full ${
                                compilationStatus.compilation.status === 'completed'
                                  ? 'bg-green-500'
                                  : compilationStatus.compilation.status === 'failed'
                                  ? 'bg-red-500'
                                  : 'bg-yellow-500'
                              }`}
                            />
                            <span className="text-sm font-medium text-papers-primary">
                              {compilationStatus.compilation.status}
                            </span>
                          </div>
                          {compilationStatus.compilation.errors && compilationStatus.compilation.errors.length > 0 && (
                            <div className="text-sm text-red-400">
                              {compilationStatus.compilation.errors.slice(0, 3).map((error, idx) => (
                                <div key={idx} className="truncate">
                                  {error}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'comments' && (
                  <div className="h-full flex flex-col">
                    {/* Chat Messages */}
                    <div className="flex-1 p-4 overflow-y-auto space-y-4">
                      {chatMessages.length === 0 ? (
                        <div className="text-center text-papers-muted py-8">
                          <MessageCircle size={48} className="mx-auto mb-4 opacity-50" />
                          <p>Start a conversation about your LaTeX project</p>
                        </div>
                      ) : (
                        chatMessages.map((message) => (
                          <div
                            key={message.id}
                            className={`p-3 rounded-lg ${
                              message.type === 'user'
                                ? 'bg-papers-button-primary text-papers-button-primary ml-8'
                                : 'bg-papers-secondary text-papers-primary mr-8'
                            }`}
                          >
                            <div className="text-sm">{message.content}</div>
                            <div className="text-xs opacity-60 mt-1">
                              {new Date(message.timestamp).toLocaleTimeString()}
                            </div>
                          </div>
                        ))
                      )}
                    </div>

                    {/* Chat Input */}
                    <div className="p-4 border-t border-papers-medium">
                      <div className="flex gap-2">
                        <Input
                          value={currentMessage}
                          onChange={(e) => setCurrentMessage(e.target.value)}
                          placeholder="Ask about your LaTeX project..."
                          onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                          className="flex-1"
                        />
                        <Button
                          onClick={handleSendMessage}
                          disabled={!currentMessage.trim()}
                          size="sm"
                        >
                          <Send size={16} />
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </Panel>
        </PanelGroup>
      </div>
    </div>
  );
}