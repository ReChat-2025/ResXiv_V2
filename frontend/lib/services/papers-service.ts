import { usePapersStore } from '@/lib/stores/papers-store';
import { useAppStore } from '@/lib/stores/app-store';
import { papersApi } from '@/lib/api/papers-api';
import { Paper, PaperStatus, ChatActionButton } from '@/lib/papers-config';

// Papers service class for business logic
export class PapersService {
  private static instance: PapersService;

  private constructor() {}

  static getInstance(): PapersService {
    if (!PapersService.instance) {
      PapersService.instance = new PapersService();
    }
    return PapersService.instance;
  }

  // Initialize papers data
  async initializePapers(): Promise<void> {
    const store = usePapersStore.getState();
    
    try {
      store.setLoading(true);
      const response = await papersApi.getPapers({ project_id: "default", page: 1, size: 50 });
      
      store.setPapers(response.papers as any);
      
      // Auto-select first paper if available
      if (( response.papers as any).length > 0) {
        const selectedPaper = ( response.papers as any).find((p: any) => p.isSelected) || (response.papers as any)[0];
        store.setSelectedPaper(selectedPaper);
      }
    } catch (error) {
      console.error('Failed to load papers:', error);
      this.handleError('Failed to load papers', error);
    } finally {
      store.setLoading(false);
    }
  }

  // Search papers with debouncing
  async searchPapers(query: string, debounceMs: number = 300): Promise<void> {
    const store = usePapersStore.getState();
    
    // Debounce search requests
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }

    this.searchTimeout = setTimeout(async () => {
      try {
        if (!query.trim()) {
          // Reset to all papers if query is empty
          const response = await papersApi.getPapers({ project_id: "default", page: 1, size: 50 });
          store.setPapers(response.papers as any);
          return;
        }

        store.setLoading(true);
        const response = await papersApi.searchPapers({ query, project_id: "default" });
        store.setPapers(response.papers as any);
        
        // Clear selection if current paper is not in results
        const currentPaper = store.selectedPaper;
        if (currentPaper && !( response.papers as any).find((p: any) => p.id === currentPaper.id)) {
          store.setSelectedPaper(null);
        }
      } catch (error) {
        console.error('Search failed:', error);
        this.handleError('Search failed', error);
      } finally {
        store.setLoading(false);
      }
    }, debounceMs);
  }

  private searchTimeout: NodeJS.Timeout | null = null;

  // Add new paper
  async addPaper(paperData: Partial<Paper>): Promise<Paper | null> {
    const store = usePapersStore.getState();
    
    try {
      store.setLoading(true);
      
      const newPaper = await papersApi.uploadPaper({
        project_id: "default",
        file: new File([], "empty.pdf"),
        title: paperData.title || 'Untitled Paper',
        authors: paperData.authors || [],
        abstract: paperData.abstract,
        year: paperData.year,
        venue: paperData.venue,
        url: paperData.url,
        pdfUrl: paperData.pdfUrl,
        tags: paperData.tags || [],
      } as any);

      store.addPaper(newPaper as any);
      store.setSelectedPaper(newPaper as any);
      
      this.showNotification('Paper added successfully', 'success');
      return newPaper as any;
    } catch (error) {
      console.error('Failed to add paper:', error);
      this.handleError('Failed to add paper', error);
      return null;
    } finally {
      store.setLoading(false);
    }
  }

  // Update paper
  async updatePaper(id: string, updates: Partial<Paper>): Promise<boolean> {
    const store = usePapersStore.getState();
    
    try {
      store.setLoading(true);
      
      const updatedPaper = await papersApi.updatePaper({ project_id: "default", paper_id: id, ...updates } as any);
      store.updatePaper(id, updatedPaper as any);
      
      this.showNotification('Paper updated successfully', 'success');
      return true;
    } catch (error) {
      console.error('Failed to update paper:', error);
      this.handleError('Failed to update paper', error);
      return false;
    } finally {
      store.setLoading(false);
    }
  }

  // Delete paper
  async deletePaper(id: string): Promise<boolean> {
    const store = usePapersStore.getState();
    
    try {
      store.setLoading(true);
      
      await papersApi.deletePaper("default", id);
      store.removePaper(id);
      
      this.showNotification('Paper deleted successfully', 'success');
      return true;
    } catch (error) {
      console.error('Failed to delete paper:', error);
      this.handleError('Failed to delete paper', error);
      return false;
    } finally {
      store.setLoading(false);
    }
  }

  // Handle paper actions
  async handlePaperAction(action: string, paper: Paper): Promise<void> {
    switch (action) {
      case 'cite':
        await this.citePaper(paper);
        break;
      case 'download':
        await this.downloadPaper(paper);
        break;
      case 'share':
        await this.sharePaper(paper);
        break;
      case 'bookmark':
        await this.bookmarkPaper(paper);
        break;
      case 'export':
        await this.exportCitation(paper);
        break;
      default:
        console.warn(`Unknown paper action: ${action}`);
    }
  }

  // Handle chat actions
  async handleChatAction(action: ChatActionButton, paper: Paper): Promise<void> {
    switch (action.id) {
      case 'add-to-journal':
        await this.addToJournal(paper);
        break;
      case 'copy':
        await this.copyPaperInfo(paper);
        break;
      default:
        console.warn(`Unknown chat action: ${action.id}`);
    }
  }

  // Paper-specific actions
  private async citePaper(paper: Paper): Promise<void> {
    try {
      // Generate citation text
      const citation = this.generateCitation(paper);
      
      // Copy to clipboard
      await navigator.clipboard.writeText(citation);
      this.showNotification('Citation copied to clipboard', 'success');
    } catch (error) {
      console.error('Failed to cite paper:', error);
      this.handleError('Failed to generate citation', error);
    }
  }

  private async downloadPaper(paper: Paper): Promise<void> {
    try {
      if (!paper.pdfUrl) {
        this.showNotification('No PDF available for this paper', 'warning');
        return;
      }

      // Create download link
      const link = document.createElement('a');
      link.href = paper.pdfUrl;
      link.download = `${paper.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      this.showNotification('Download started', 'success');
    } catch (error) {
      console.error('Failed to download paper:', error);
      this.handleError('Failed to download paper', error);
    }
  }

  private async sharePaper(paper: Paper): Promise<void> {
    try {
      if (navigator.share) {
        await navigator.share({
          title: paper.title,
          text: `Check out this paper: ${paper.title}`,
          url: paper.url || window.location.href,
        });
      } else {
        // Fallback: copy link to clipboard
        const shareText = `${paper.title}\n${paper.url || window.location.href}`;
        await navigator.clipboard.writeText(shareText);
        this.showNotification('Paper link copied to clipboard', 'success');
      }
    } catch (error) {
      console.error('Failed to share paper:', error);
      this.handleError('Failed to share paper', error);
    }
  }

  private async bookmarkPaper(paper: Paper): Promise<void> {
    try {
      // Update paper status to bookmarked
      await this.updatePaper(paper.id, { 
        ...paper, 
        // Add bookmark status to paper (would need to extend Paper interface)
      });
      
      this.showNotification('Paper bookmarked', 'success');
    } catch (error) {
      console.error('Failed to bookmark paper:', error);
      this.handleError('Failed to bookmark paper', error);
    }
  }

  private async exportCitation(paper: Paper): Promise<void> {
    try {
      const citation = this.generateCitation(paper, 'bibtex');
      
      // Create download for citation file
      const blob = new Blob([citation], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${paper.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.bib`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      this.showNotification('Citation exported', 'success');
    } catch (error) {
      console.error('Failed to export citation:', error);
      this.handleError('Failed to export citation', error);
    }
  }

  private async addToJournal(paper: Paper): Promise<void> {
    try {
      // This would integrate with a journal/notes system
      console.log('Adding to journal:', paper.title);
      this.showNotification('Added to journal', 'success');
    } catch (error) {
      console.error('Failed to add to journal:', error);
      this.handleError('Failed to add to journal', error);
    }
  }

  private async copyPaperInfo(paper: Paper): Promise<void> {
    try {
      const info = `${paper.title}\n${paper.authors.join(', ')}\n${paper.year} • ${paper.venue}`;
      await navigator.clipboard.writeText(info);
      this.showNotification('Paper information copied', 'success');
    } catch (error) {
      console.error('Failed to copy paper info:', error);
      this.handleError('Failed to copy paper information', error);
    }
  }

  // Utility methods
  private generateCitation(paper: Paper, format: 'apa' | 'mla' | 'bibtex' = 'apa'): string {
    switch (format) {
      case 'apa':
        return `${paper.authors.join(', ')} (${paper.year}). ${paper.title}. ${paper.venue}.`;
      case 'mla':
        return `${paper.authors[0]}. "${paper.title}." ${paper.venue}, ${paper.year}.`;
      case 'bibtex':
        return `@article{${paper.id},
  title={${paper.title}},
  author={${paper.authors.join(' and ')}},
  journal={${paper.venue}},
  year={${paper.year}}
}`;
      default:
        return `${paper.authors.join(', ')} (${paper.year}). ${paper.title}. ${paper.venue}.`;
    }
  }

  private showNotification(message: string, type: 'success' | 'error' | 'warning' | 'info'): void {
    const appStore = useAppStore.getState();
    appStore.addNotification({
      title: type.charAt(0).toUpperCase() + type.slice(1),
      message,
      type,
      timestamp: new Date().toISOString(),
      read: false,
    });
  }

  private handleError(message: string, error: any): void {
    console.error(message, error);
    this.showNotification(message, 'error');
  }

  // Send chat message
  async sendChatMessage(message: string, paper: Paper): Promise<void> {
    try {
      // This would integrate with an AI chat service
      console.log('Sending chat message:', message, 'for paper:', paper.title);
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // For now, just show a success notification
      this.showNotification('Message sent', 'success');
    } catch (error) {
      console.error('Failed to send chat message:', error);
      this.handleError('Failed to send message', error);
    }
  }

  // Import paper from URL or DOI
  async importPaper(source: string): Promise<Paper | null> {
    const store = usePapersStore.getState();
    
    try {
      store.setLoading(true);
      
      const paper = await papersApi.importPaper(source);
      store.addPaper(paper);
      store.setSelectedPaper(paper);
      
      this.showNotification('Paper imported successfully', 'success');
      return paper;
    } catch (error) {
      console.error('Failed to import paper:', error);
      this.handleError('Failed to import paper', error);
      return null;
    } finally {
      store.setLoading(false);
    }
  }

  // Upload PDF for paper
  async uploadPaperPdf(paperId: string, file: File): Promise<boolean> {
    const store = usePapersStore.getState();
    
    try {
      store.setLoading(true);
      
      const result = await papersApi.uploadPaper({
        project_id: "default", // You may want to get this from context/store
        file: file,
        title: file.name,
        process_with_grobid: true,
        run_diagnostics: false,
        private_uploaded: false
      });
      
      // Update paper with PDF URL
      store.updatePaper(paperId, { pdfUrl: result.pdf_path || undefined });
      
      this.showNotification('PDF uploaded successfully', 'success');
      return true;
    } catch (error) {
      console.error('Failed to upload PDF:', error);
      this.handleError('Failed to upload PDF', error);
      return false;
    } finally {
      store.setLoading(false);
    }
  }

  // Update paper status
  async updatePaperStatus(paperId: string, status: PaperStatus): Promise<boolean> {
    return this.updatePaper(paperId, { status });
  }

  // Get paper recommendations
  async getPaperRecommendations(paperId: string): Promise<Paper[]> {
    try {
      // For now, return empty array since the API method doesn't exist yet
      // TODO: Implement getRecommendations in papersApi when backend is ready
      const recommendations: Paper[] = [];
      return recommendations;
    } catch (error) {
      console.error('Failed to get recommendations:', error);
      this.handleError('Failed to get recommendations', error);
      return [];
    }
  }
}

// Export singleton instance
export const papersService = PapersService.getInstance();

// React hooks for using the service
export const usePapersService = () => {
  return {
    initializePapers: () => papersService.initializePapers(),
    searchPapers: (query: string) => papersService.searchPapers(query),
    addPaper: (paperData: Partial<Paper>) => papersService.addPaper(paperData),
    updatePaper: (id: string, updates: Partial<Paper>) => papersService.updatePaper(id, updates),
    deletePaper: (id: string) => papersService.deletePaper(id),
    handlePaperAction: (action: string, paper: Paper) => papersService.handlePaperAction(action, paper),
    handleChatAction: (action: ChatActionButton, paper: Paper) => papersService.handleChatAction(action, paper),
    sendChatMessage: (message: string, paper: Paper) => papersService.sendChatMessage(message, paper),
    importPaper: (source: string) => papersService.importPaper(source),
    uploadPaperPdf: (paperId: string, file: File) => papersService.uploadPaperPdf(paperId, file),
    updatePaperStatus: (paperId: string, status: PaperStatus) => papersService.updatePaperStatus(paperId, status),
    getPaperRecommendations: (paperId: string) => papersService.getPaperRecommendations(paperId),
  };
}; 