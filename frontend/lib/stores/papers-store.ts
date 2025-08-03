import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { useMemo } from 'react';
import { Paper, PaperView } from '@/lib/papers-config';

interface PapersState {
  // Paper management
  papers: Paper[];
  selectedPaper: Paper | null;
  filteredPapers: Paper[];
  
  // UI state
  currentView: PaperView;
  sidebarCollapsed: boolean;
  chatSidebarCollapsed: boolean;
  
  // Search and filters
  searchQuery: string;
  
  // Pagination
  currentPage: number;
  totalPages: number;
  
  // Controls
  selectedLanguage: string;
  zoomLevel: string;
  
  // Chat
  chatInput: string;
  
  // Loading states
  isLoading: boolean;
  isSearching: boolean;
  
  // Actions
  setPapers: (papers: Paper[]) => void;
  setSelectedPaper: (paper: Paper | null) => void;
  setCurrentView: (view: PaperView) => void;
  toggleSidebar: () => void;
  toggleChatSidebar: () => void;
  setSearchQuery: (query: string) => void;
  setCurrentPage: (page: number) => void;
  setSelectedLanguage: (language: string) => void;
  setZoomLevel: (zoom: string) => void;
  setChatInput: (input: string) => void;
  setLoading: (loading: boolean) => void;
  clearSearch: () => void;
  selectPaperById: (id: string) => void;
  updatePaper: (id: string, updates: Partial<Paper>) => void;
  addPaper: (paper: Paper) => void;
  removePaper: (id: string) => void;
}

export const usePapersStore = create<PapersState>()(
  subscribeWithSelector((set, get) => ({
    // Initial state
    papers: [],
    selectedPaper: null,
    filteredPapers: [],
    currentView: 'chat',
    sidebarCollapsed: false,
    chatSidebarCollapsed: false,
    searchQuery: '',
    currentPage: 1,
    totalPages: 1,
    selectedLanguage: 'English',
    zoomLevel: '100%',
    chatInput: '',
    isLoading: false,
    isSearching: false,

    // Actions
    setPapers: (papers) => {
      set({ 
        papers, 
        filteredPapers: papers,
        totalPages: Math.ceil(papers.length / 10) // Assuming 10 papers per page
      });
    },

    setSelectedPaper: (paper) => {
      set({ selectedPaper: paper });
    },

    setCurrentView: (view) => {
      set({ currentView: view });
    },

    toggleSidebar: () => {
      set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }));
    },

    toggleChatSidebar: () => {
      set((state) => ({ chatSidebarCollapsed: !state.chatSidebarCollapsed }));
    },

    setSearchQuery: (query) => {
      set({ searchQuery: query, isSearching: true });
      
      // Filter papers based on search query
      const { papers } = get();
      if (!query.trim()) {
        set({ filteredPapers: papers, isSearching: false });
        return;
      }

      const lowercaseQuery = query.toLowerCase();
      const filtered = papers.filter(paper => 
        paper.title.toLowerCase().includes(lowercaseQuery) ||
        paper.authors.some(author => author.toLowerCase().includes(lowercaseQuery)) ||
        paper.tags.some(tag => tag.toLowerCase().includes(lowercaseQuery)) ||
        (paper.abstract && paper.abstract.toLowerCase().includes(lowercaseQuery))
      );
      
      set({ filteredPapers: filtered, isSearching: false });
    },

    setCurrentPage: (page) => {
      set({ currentPage: page });
    },

    setSelectedLanguage: (language) => {
      set({ selectedLanguage: language });
    },

    setZoomLevel: (zoom) => {
      set({ zoomLevel: zoom });
    },

    setChatInput: (input) => {
      set({ chatInput: input });
    },

    setLoading: (loading) => {
      set({ isLoading: loading });
    },

    clearSearch: () => {
      const { papers } = get();
      set({ 
        searchQuery: '', 
        filteredPapers: papers,
        isSearching: false 
      });
    },

    selectPaperById: (id) => {
      const { papers } = get();
      const paper = papers.find(p => p.id === id);
      set({ selectedPaper: paper || null });
    },

    updatePaper: (id, updates) => {
      set((state) => {
        const updatedPapers = state.papers.map(paper =>
          paper.id === id ? { ...paper, ...updates } : paper
        );
        const updatedFiltered = state.filteredPapers.map(paper =>
          paper.id === id ? { ...paper, ...updates } : paper
        );
        
        return {
          papers: updatedPapers,
          filteredPapers: updatedFiltered,
          selectedPaper: state.selectedPaper?.id === id 
            ? { ...state.selectedPaper, ...updates } 
            : state.selectedPaper
        };
      });
    },

    addPaper: (paper) => {
      set((state) => ({
        papers: [...state.papers, paper],
        filteredPapers: state.searchQuery 
          ? state.filteredPapers 
          : [...state.papers, paper]
      }));
    },

    removePaper: (id) => {
      set((state) => ({
        papers: state.papers.filter(p => p.id !== id),
        filteredPapers: state.filteredPapers.filter(p => p.id !== id),
        selectedPaper: state.selectedPaper?.id === id ? null : state.selectedPaper
      }));
    }
  }))
);

// Selector hooks for better performance
export const useSelectedPaper = () => usePapersStore(state => state.selectedPaper);
export const useFilteredPapers = () => usePapersStore(state => state.filteredPapers);
export const usePapersLoading = () => usePapersStore(state => state.isLoading);

// Individual search selectors
export const useSearchQuery = () => usePapersStore(state => state.searchQuery);
export const useIsSearching = () => usePapersStore(state => state.isSearching);
export const useSetSearchQuery = () => usePapersStore(state => state.setSearchQuery);
export const useClearSearch = () => usePapersStore(state => state.clearSearch);

export const usePapersSearch = () => {
  const searchQuery = useSearchQuery();
  const isSearching = useIsSearching();
  const setSearchQuery = useSetSearchQuery();
  const clearSearch = useClearSearch();
  
  return useMemo(() => ({
    searchQuery,
    isSearching,
    setSearchQuery,
    clearSearch
  }), [searchQuery, isSearching, setSearchQuery, clearSearch]);
};

// Individual sidebar selectors
export const useSidebarCollapsed = () => usePapersStore(state => state.sidebarCollapsed);
export const useToggleSidebar = () => usePapersStore(state => state.toggleSidebar);

export const usePapersSidebar = () => {
  const collapsed = useSidebarCollapsed();
  const toggle = useToggleSidebar();
  
  return useMemo(() => ({
    collapsed,
    toggle
  }), [collapsed, toggle]);
};

// Individual chat selectors
export const useChatInput = () => usePapersStore(state => state.chatInput);
export const useSetChatInput = () => usePapersStore(state => state.setChatInput);
export const useChatSidebarCollapsed = () => usePapersStore(state => state.chatSidebarCollapsed);
export const useToggleChatSidebar = () => usePapersStore(state => state.toggleChatSidebar);

export const usePapersChat = () => {
  const input = useChatInput();
  const setInput = useSetChatInput();
  const sidebarCollapsed = useChatSidebarCollapsed();
  const toggleSidebar = useToggleChatSidebar();
  
  return useMemo(() => ({
    input,
    setInput,
    sidebarCollapsed,
    toggleSidebar
  }), [input, setInput, sidebarCollapsed, toggleSidebar]);
}; 