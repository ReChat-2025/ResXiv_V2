"use client";

import React, { useCallback, useEffect, useImperativeHandle, useLayoutEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Ensure worker version matches the API version used by react-pdf
if (typeof window !== 'undefined') {
  try {
    const v = (pdfjs as any).version;
    if (v) {
      (pdfjs as any).GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${v}/build/pdf.worker.min.mjs`;
    }
  } catch {}
}

export interface PdfViewerHandle {
  scrollToReference: (ref: { doi?: string; title?: string; year?: string; authors?: string[]; index?: number }) => void;
}

export interface PdfViewerProps {
  fileUrl: string;
  zoom: number; // 0.5 - 2.0
  currentPage: number;
  onTotalPages?: (pages: number) => void;
  onPageChange?: (page: number) => void;
  // When user selects text, we emit text and the screen coordinates where the hover should appear
  onTextSelection?: (data: { text: string; x: number; y: number }) => void;
}

export const PdfViewer = React.forwardRef<PdfViewerHandle, PdfViewerProps>(({
  fileUrl,
  zoom,
  currentPage,
  onTotalPages,
  onPageChange,
  onTextSelection,
}, ref) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState<number>(800);
  const [numPages, setNumPages] = useState<number>(0);
  const pageRefs = useRef<Array<HTMLDivElement | null>>([]);
  const pageOffsetsRef = useRef<number[]>([]);
  const lastNotifiedPageRef = useRef<number>(1);
  const pdfDocRef = useRef<any>(null);
  const annotationIdToDestRef = useRef<Map<string, any>>(new Map());
  const lastReportedChangeRef = useRef<{ page: number; ts: number } | null>(null);
  const programmaticNavigationRef = useRef<boolean>(false);
  const userScrollingRef = useRef<boolean>(false);
  const scrollEndTimerRef = useRef<number | null>(null);

  // Index of reference anchors: key -> {page,y}
  const refPositionIndex = useRef<Map<string, { page: number; y: number }>>(new Map<string, { page: number; y: number }>());
  type LineRec = { y: number; text: string };
  type SpanRec = { y: number; text: string };
  const pageLineIndexRef = useRef<Map<number, LineRec[]>>(new Map<number, LineRec[]>());
  const pageSpansIndexRef = useRef<Map<number, SpanRec[]>>(new Map<number, SpanRec[]>());

  // Normalize DOI to a comparable key
  const normalizeDoi = (doi?: string | null) => {
    if (!doi) return null;
    let d = doi.trim();
    d = d.replace(/^https?:\/\/(dx\.)?doi\.org\//i, "");
    d = d.replace(/^doi:\s*/i, "");
    return d.toLowerCase();
  };

  // Resize observer to recalc width for Page
  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const width = el.clientWidth;
      setContainerWidth(width);
      // offsets may change on resize due to reflow
      requestMeasureOffsets();
    });
    ro.observe(el);
    setContainerWidth(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  const handleLoadSuccess = useCallback((pdf: any) => {
    setNumPages(pdf.numPages || 0);
    pdfDocRef.current = pdf;
    if (onTotalPages) onTotalPages(pdf.numPages);
    // offsets will be measured after first render of pages
    setTimeout(() => requestMeasureOffsets(), 0);
  }, [onTotalPages]);

  // Measure page offsets relative to the scroll container
  const requestMeasureOffsets = () => {
    const container = containerRef.current;
    if (!container) return;
    const offsets: number[] = [];
    pageRefs.current.forEach((el) => {
      if (!el) {
        offsets.push(0);
        return;
      }
      const top = el.offsetTop; // since all are within the same offsetParent (container child), offsetTop works
      offsets.push(top);
    });
    pageOffsetsRef.current = offsets;
    try { console.debug('[PDF] measured page offsets', offsets); } catch {}
  };

  // Helper: scroll to a specific page and optional y offset within page
  const scrollToPagePosition = (pageNumber: number, yInPage: number | null) => {
    const container = containerRef.current;
    const offsets = pageOffsetsRef.current;
    if (!container || !offsets.length) return;
    const baseTop = offsets[pageNumber - 1] || 0;
    const y = Math.max(0, yInPage ?? 0);
    const top = baseTop + y;
    try { console.debug('[PDF] scrollToPagePosition', { pageNumber, yInPage: y, baseTop, top }); } catch {}
    programmaticNavigationRef.current = true;
    container.scrollTo({ top, behavior: 'smooth' });
  };

  // Resolve a PDF destination to scrollTop position
  const scrollToDestination = useCallback(async (dest: any) => {
    try {
      const pdf = pdfDocRef.current;
      if (!pdf) return;

      // Accept both named destinations (string) and explicit destination arrays (from onItemClick)
      let explicitDest: any = null;
      if (Array.isArray(dest)) {
        explicitDest = dest;
      } else {
        explicitDest = await pdf.getDestination(dest);
      }
      try { console.debug('[PDF] explicit destination', explicitDest); } catch {}
      if (!explicitDest || !Array.isArray(explicitDest)) {
        return;
      }
      const refObj = explicitDest[0];
      const pageIndex = await pdf.getPageIndex(refObj);
      const pageNumber = pageIndex + 1;

      const type = explicitDest[1];
      let yInPage: number | null = null;

      try {
        const page = await pdf.getPage(pageNumber);
        const viewportAt1 = page.getViewport({ scale: 1 });
        const scale = containerWidth / viewportAt1.width;
        const viewport = page.getViewport({ scale });

        if (type === 'XYZ') {
          const topVal = explicitDest[3];
          if (typeof topVal === 'number') {
            const pt = viewport.convertToViewportPoint(0, topVal);
            yInPage = pt[1];
          } else {
            yInPage = 0;
          }
        } else if (type === 'FitH' || type === 'FitBH') {
          const topVal = explicitDest[2];
          if (typeof topVal === 'number') {
            const pt = viewport.convertToViewportPoint(0, topVal);
            yInPage = pt[1];
          } else {
            yInPage = 0;
          }
        } else if (type === 'FitV' || type === 'FitBV') {
          yInPage = 0;
        } else {
          yInPage = 0;
        }
      } catch (err) {
        try { console.debug('[PDF] viewport conversion failed', err); } catch {}
        yInPage = 0;
      }

      scrollToPagePosition(pageNumber, yInPage);
      onPageChange && onPageChange(pageNumber);
    } catch (err) {
      try { console.debug('[PDF] scrollToDestination failed', err); } catch {}
    }
  }, [containerWidth, onPageChange]);

  // Sync current page from scroll
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const onScroll = () => {
      const offsets = pageOffsetsRef.current;
      if (!offsets.length) return;

      // mark as actively scrolling and debounce end
      userScrollingRef.current = true;
      if (scrollEndTimerRef.current) window.clearTimeout(scrollEndTimerRef.current);
      scrollEndTimerRef.current = window.setTimeout(() => {
        userScrollingRef.current = false;
      }, 250);

      // use viewport center to determine current page, reducing boundary jitter
      const yCenter = container.scrollTop + container.clientHeight / 2;
      let page = offsets.length;
      for (let i = 0; i < offsets.length - 1; i++) {
        if (yCenter >= offsets[i] && yCenter < offsets[i + 1]) {
          page = i + 1;
          break;
        }
      }

      if (page !== lastNotifiedPageRef.current) {
        lastNotifiedPageRef.current = page;
        lastReportedChangeRef.current = { page, ts: Date.now() };
        onPageChange && onPageChange(page);
      }
    };

    container.addEventListener('scroll', onScroll, { passive: true });
    return () => container.removeEventListener('scroll', onScroll);
  }, [onPageChange]);

  // Scroll to page when currentPage changes externally
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Skip if this change was just reported by our own scroll observer (prevents recoil)
    const recent = lastReportedChangeRef.current &&
      lastReportedChangeRef.current.page === currentPage &&
      Date.now() - lastReportedChangeRef.current.ts < 400;

    if ((recent || userScrollingRef.current) && !programmaticNavigationRef.current) {
      try { console.debug('[PDF] skip auto-scroll (user scroll in progress or recent)', currentPage); } catch {}
      return;
    }

    const offsets = pageOffsetsRef.current;
    if (!offsets.length || currentPage < 1 || currentPage > offsets.length) return;
    const top = offsets[currentPage - 1];
    try { console.debug('[PDF] auto-scroll to page from prop', currentPage, top, { programmatic: programmaticNavigationRef.current }); } catch {}
    container.scrollTo({ top, behavior: 'smooth' });
    programmaticNavigationRef.current = false;
  }, [currentPage, numPages]);

  // Selection detection inside the container
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const handler = () => {
      try {
        const sel = window.getSelection();
        if (!sel || !sel.toString().trim()) return;
        // Ensure selection is within our container
        const anchorNode = sel.anchorNode as Node | null;
        if (!anchorNode) return;
        if (!el.contains(anchorNode)) return;
        const range = sel.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return;
        const centerX = rect.right;
        const centerY = rect.top + rect.height / 2;
        if (onTextSelection) {
          onTextSelection({ text: sel.toString().trim(), x: centerX, y: centerY });
        }
      } catch {
        // no-op
      }
    };

    el.addEventListener('mouseup', handler, true);
    el.addEventListener('keyup', handler, true);
    document.addEventListener('selectionchange', handler, true);

    return () => {
      el.removeEventListener('mouseup', handler, true);
      el.removeEventListener('keyup', handler, true);
      document.removeEventListener('selectionchange', handler, true);
    };
  }, [onTextSelection]);

  // Handle internal anchors in text/annotation layers
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const onClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null;
      if (!target) return;
      // walk up to anchor
      let el: HTMLElement | null = target;
      while (el && el !== container) {
        if (el.tagName === 'A') break;
        el = el.parentElement;
      }
      if (el && el.tagName === 'A') {
        const href = (el as HTMLAnchorElement).getAttribute('href') || '';
        try { console.debug('[PDF] anchor click', { href, el }); } catch {}
        // Try mapping via annotation id when available
        let annId = el.getAttribute('data-annotation-id');
        // Fallback: pdf.js often uses element id like "pdfjs_internal_id_137R"
        if (!annId && el.id) {
          const m = el.id.match(/pdfjs_internal_id_(\w+)/i);
          if (m) annId = m[1];
        }
        if (annId) {
          const dest = annotationIdToDestRef.current.get(String(annId));
          try { console.debug('[PDF] annotation id', annId, '-> dest', dest); } catch {}
          if (dest) {
            e.preventDefault();
            e.stopPropagation();
            scrollToDestination(dest);
            return;
          }
        }
        // pdf.js uses #nameddest= or #page=<n> for internal links
        const matchPage = href.match(/#page=(\d+)/i);
        const matchDest = href.match(/#nameddest=([^&]+)/i);
        if (matchPage) {
          const p = parseInt(matchPage[1], 10);
          try { console.debug('[PDF] match #page', p); } catch {}
          if (p > 0) {
            e.preventDefault();
            e.stopPropagation();
            scrollToPagePosition(p, 0);
            onPageChange && onPageChange(p);
            return;
          }
        }
        if (matchDest) {
          try { console.debug('[PDF] match #nameddest', matchDest[1]); } catch {}
          e.preventDefault();
          e.stopPropagation();
          scrollToDestination(matchDest[1]);
          return;
        }
      }
    };

    container.addEventListener('click', onClick, true);
    return () => container.removeEventListener('click', onClick, true);
  }, [onPageChange, scrollToDestination]);

  // Expose handle to parent
  useImperativeHandle(ref, () => ({
    scrollToReference: (info) => {
      try { console.debug('[PDF] Jump request', info); } catch {}
      const doiKey = normalizeDoi(info.doi || null);
      try { if (doiKey) console.debug('[PDF] DOI key', doiKey); } catch {}
      if (doiKey) {
        const pos = refPositionIndex.current.get(`doi:${doiKey}`);
        try { console.debug('[PDF] DOI lookup result', pos); } catch {}
        if (pos && typeof pos.page === 'number') {
          scrollToPagePosition(pos.page, pos.y);
          onPageChange && onPageChange(pos.page);
          return;
        }
      }
      // If caller provided numeric index (e.g. [23]), try lines first
      const nIdx = (info as any)?.index;
      if (typeof nIdx === 'number' && nIdx > 0) {
        const patterns: RegExp[] = [
          new RegExp(`^\\s*\\[${nIdx}\\]`),
          new RegExp(`^\\s*${nIdx}\\.`),
          new RegExp(`^\\s*\\(${nIdx}\\)`),
          new RegExp(`^\\s*${nIdx}\\s*[-–—]`),
        ];
        try { console.debug('[PDF] Index search patterns', nIdx, patterns.map(p=>p.source)); } catch {}
        let idxHit: { page: number; y: number } | null = null;
        pageLineIndexRef.current.forEach((lines: LineRec[], pageNum: number) => {
          for (const { y, text } of lines) {
            if (patterns.some(p => p.test(text))) { idxHit = { page: pageNum, y }; break; }
          }
        });
        try { console.debug('[PDF] Index search hit', idxHit); } catch {}
        if (idxHit) {
          const ih: { page: number; y: number } = idxHit;
          scrollToPagePosition(ih.page, ih.y);
          onPageChange && onPageChange(ih.page);
          return;
        }
      }

      // fallback: try to search by words from the title in anchor texts index
      const title = (info.title || '').toLowerCase();
      if (title.length > 6) {
        const words = title.split(/\s+/).filter(Boolean);
        const probe = words.slice(0, 6).join(' ');
        try { console.debug('[PDF] Anchor-text probe', probe); } catch {}
        for (const [k, pos] of refPositionIndex.current.entries()) {
          if (k.startsWith('text:') && (k.includes(probe) || probe.includes(k.replace('text:','').slice(0, probe.length)))) {
            try { console.debug('[PDF] Anchor-text match', k, pos); } catch {}
            const target = pos as { page: number; y: number };
            scrollToPagePosition(target.page, target.y);
            onPageChange && onPageChange(target.page);
            return;
          }
        }
      }

      // Deep fallback: fuzzy match against text layer lines using title words and author last names
      const tokens: string[] = [];
      title.split(/\W+/).filter(w => w.length >= 4).slice(0, 8).forEach(w => tokens.push(w.toLowerCase()));
      if (Array.isArray(info.authors)) {
        info.authors.forEach((a: string) => {
          const parts = a.split(/\s+/).filter(Boolean);
          if (parts.length) tokens.push(parts[parts.length - 1].toLowerCase());
        });
      }
      if (info.year && /\d{4}/.test(info.year)) tokens.push(String(info.year));
      try { console.debug('[PDF] Fuzzy tokens', tokens); } catch {}

      let best: { page: number; y: number; score: number } | null = null;
      pageLineIndexRef.current.forEach((lines: LineRec[], pageNum: number) => {
        lines.forEach(({ y, text }) => {
          let score = 0;
          for (const tok of tokens) {
            if (text.includes(tok)) score += 1;
          }
          if (score > 2) {
            if (!best || score > best.score) best = { page: pageNum, y, score };
          }
        });
      });
      try { console.debug('[PDF] Fuzzy best', best); } catch {}
      if (best !== null) {
        const cand: { page: number; y: number; score: number } = best;
        scrollToPagePosition(cand.page, cand.y);
        onPageChange && onPageChange(cand.page);
        return;
      }

      // Targeted fallback: find the page/line that contains at least 2 of the first 3 authors' last names
      if (Array.isArray(info.authors) && info.authors.length > 0) {
        const firstThree = info.authors.slice(0, 3);
        const lastNames = firstThree.map((a: string) => {
          const parts = a.split(/\s+/).filter(Boolean);
          return parts.length ? parts[parts.length - 1].toLowerCase() : '';
        }).filter(Boolean);
        try { console.debug('[PDF] Author last-name probe', lastNames); } catch {}

        // Page-level match using spans: pick page with at least 2 last names present; scroll to earliest occurrence
        let bestPage: { page: number; hits: number; earliestY: number } | null = null;
        pageSpansIndexRef.current.forEach((spans: SpanRec[], pageNum: number) => {
          let hitsSet = new Set<string>();
          let earliestY = Infinity;
          for (const { y, text } of spans) {
            for (const ln of lastNames) {
              if (!hitsSet.has(ln) && text.includes(ln)) {
                hitsSet.add(ln);
                if (y < earliestY) earliestY = y;
              }
            }
            if (hitsSet.size >= 2) break;
          }
          if (hitsSet.size >= 2) {
            if (!bestPage || hitsSet.size > bestPage.hits) {
              bestPage = { page: pageNum, hits: hitsSet.size, earliestY: isFinite(earliestY) ? earliestY : 0 };
            }
          }
        });
        try { console.debug('[PDF] Author-match bestPage', bestPage); } catch {}
        if (bestPage) {
          const bp: { page: number; hits: number; earliestY: number } = bestPage;
          scrollToPagePosition(bp.page, Math.max(0, bp.earliestY - 10));
          onPageChange && onPageChange(bp.page);
          return;
        }

        // DOM-scan fallback: walk the current DOM text spans if indexes are incomplete
        const container = containerRef.current;
        if (container) {
          const allSpans = Array.from(container.querySelectorAll<HTMLSpanElement>('.react-pdf__Page__textContent span'));
          try { console.debug('[PDF] DOM scan spans', allSpans.length); } catch {}
          const pageToHits: Map<number, { hits: Set<string>; earliestY: number }> = new Map();
          allSpans.forEach((s) => {
            const pageEl = s.closest('div[data-page]') as HTMLDivElement | null;
            if (!pageEl) return;
            const pAttr = pageEl.getAttribute('data-page');
            const pNum = pAttr ? parseInt(pAttr, 10) : NaN;
            if (!pNum || isNaN(pNum)) return;
            const wrapper = pageRefs.current[pNum - 1];
            if (!wrapper) return;
            const text = (s.textContent || '').toLowerCase();
            if (!text) return;
            let hit = false;
            for (const ln of lastNames) {
              if (text.includes(ln)) { hit = true; break; }
            }
            if (!hit) return;
            const y = (s.getBoundingClientRect().top - wrapper.getBoundingClientRect().top) / (zoom || 1);
            const rec = pageToHits.get(pNum) || { hits: new Set<string>(), earliestY: Infinity };
            for (const ln of lastNames) {
              if (text.includes(ln)) rec.hits.add(ln);
            }
            if (y < rec.earliestY) rec.earliestY = y;
            pageToHits.set(pNum, rec);
          });
          let bestDom: { page: number; hits: number; earliestY: number } | null = null;
          pageToHits.forEach((v, k) => {
            const stats = { page: k, hits: v.hits.size, earliestY: v.earliestY };
            try { console.debug('[PDF] DOM page stats', stats); } catch {}
            if (v.hits.size >= 2) {
              if (!bestDom || v.hits.size > bestDom.hits) bestDom = stats;
            }
          });
          try { console.debug('[PDF] DOM best', bestDom); } catch {}
          if (bestDom) {
            const bd: { page: number; hits: number; earliestY: number } = bestDom;
            scrollToPagePosition(bd.page, Math.max(0, bd.earliestY - 10));
            onPageChange && onPageChange(bd.page);
            return;
          }
        }
      }

      // If still not found, try to locate a References/Bibliography heading
      let headingHitPage: number | null = null;
      let headingHitY: number | null = null;
      pageLineIndexRef.current.forEach((lines: LineRec[], pageNum: number) => {
        for (const { y, text } of lines) {
          if (text.includes('references') || text.includes('bibliography')) {
            headingHitPage = pageNum;
            headingHitY = y;
            break;
          }
        }
      });
      if (headingHitPage !== null && headingHitY !== null) {
        scrollToPagePosition(headingHitPage, headingHitY);
        onPageChange && onPageChange(headingHitPage);
        return;
      }

      console.debug('[PDF] scrollToReference: no match for', info);
    }
  }), [onPageChange, zoom]);

  return (
    <div ref={containerRef} className="w-full h-full overflow-auto">
      <div style={{ width: containerWidth, transform: `scale(${zoom})`, transformOrigin: 'top center' }}>
        <Document 
          file={fileUrl} 
          onLoadSuccess={handleLoadSuccess} 
          loading={null}
          onLoadError={(e)=>{ console.error('PDF load error', e); }}
          onItemClick={(item: any) => {
            try {
              try { console.debug('[PDF] onItemClick', item); } catch {}
              if (item?.dest) {
                scrollToDestination(item.dest);
                return;
              }
              const pageNumber = item?.pageNumber ?? (typeof item?.pageIndex === 'number' ? item.pageIndex + 1 : undefined);
              if (onPageChange && typeof pageNumber === 'number' && pageNumber > 0) {
                onPageChange(pageNumber);
              }
            } catch {}
          }}
        >
          {numPages > 0 ? (
            Array.from({ length: numPages }, (_, i) => i + 1).map((p) => (
              <div key={p} ref={(el) => { pageRefs.current[p - 1] = el; }} data-page={p} className="mb-4">
                <Page 
                  pageNumber={p}
                  width={containerWidth}
                  renderAnnotationLayer
                  renderTextLayer
                  loading={null}
                  onRenderSuccess={() => {
                    // measure after each page render
                    requestAnimationFrame(requestMeasureOffsets);
                    // index anchors in this page for DOI/text mapping
                    const wrapper = pageRefs.current[p - 1];
                    if (wrapper) {
                      const anchors = wrapper.querySelectorAll<HTMLAnchorElement>('a[href]');
                      anchors.forEach((a) => {
                        const href = a.getAttribute('href') || '';
                        // compute y offset relative to page wrapper
                        const y = (a.getBoundingClientRect().top - wrapper.getBoundingClientRect().top) / (zoom || 1);
                        // DOI mapping
                        const m = href.match(/doi\.org\/([^#?\s]+)/i);
                        if (m) {
                          const doiKey = normalizeDoi(m[1]);
                          if (doiKey) {
                            refPositionIndex.current.set(`doi:${doiKey}`, { page: p, y });
                          }
                        }
                        // text mapping (anchor text)
                        const text = (a.textContent || '').toLowerCase().trim();
                        if (text.length > 6) {
                          refPositionIndex.current.set(`text:${text.slice(0, 200)}`, { page: p, y });
                        }
                      });
                      try { console.debug('[PDF] Anchors indexed', p, anchors.length); } catch {}

                      // Build a lightweight line index from the text layer
                      const textLayer = wrapper.querySelector('.react-pdf__Page__textContent');
                      if (textLayer) {
                        const spans = Array.from(textLayer.querySelectorAll<HTMLSpanElement>('span'));
                        // group by approximate y to form lines
                        const groups: Map<number, Array<{ left: number; text: string }>> = new Map();
                        const top0 = wrapper.getBoundingClientRect().top;
                        const pageSpans: SpanRec[] = [];
                        spans.forEach((s) => {
                          const rect = s.getBoundingClientRect();
                          let top = (rect.top - top0) / (zoom || 1);
                          const key = Math.round(top / 2) * 2; // 2px bins to cluster
                          const left = rect.left;
                          const txt = (s.textContent || '').trim();
                          if (!txt) return;
                          pageSpans.push({ y: key, text: txt.toLowerCase() });
                          const arr = groups.get(key) || [];
                          arr.push({ left, text: txt });
                          groups.set(key, arr);
                        });
                        const lines: LineRec[] = [];
                        Array.from(groups.entries()).sort((a, b) => a[0] - b[0]).forEach(([y, arr]) => {
                          const line = arr.sort((a, b) => a.left - b.left).map(x => x.text).join(' ').replace(/\s+/g, ' ').toLowerCase();
                          if (line.length > 0) lines.push({ y, text: line });
                        });
                        pageLineIndexRef.current.set(p, lines);
                        pageSpansIndexRef.current.set(p, pageSpans);
                        try { console.debug('[PDF] Lines indexed', p, lines.length); } catch {}
                      }
                    }
                  }}
                  onGetAnnotationsSuccess={async (annots: any[]) => {
                    try {
                      try { console.debug('[PDF] annotations for page', p, annots); } catch {}
                      const pdf = pdfDocRef.current;
                      if (!pdf || !Array.isArray(annots)) return;
                      for (const a of annots) {
                        if (a?.subtype === 'Link' && a?.dest && a?.id) {
                          try {
                            const dest = await pdf.getDestination(a.dest);
                            if (Array.isArray(dest)) {
                              annotationIdToDestRef.current.set(String(a.id), dest);
                              try {
                                const ref = dest[0];
                                const pageIndex = await pdf.getPageIndex(ref);
                                console.debug('[PDF] mapped annotation', a.id, '-> page', pageIndex + 1);
                              } catch {}
                            } else {
                              try { console.debug('[PDF] map annotation: destination not array', a); } catch {}
                            }
                          } catch (err) {
                            try { console.debug('[PDF] map annotation failed', a, err); } catch {}
                          }
                        }
                      }
                    } catch {}
                  }}
                />
              </div>
            ))
          ) : (
            <div className="py-12 text-center text-sm text-muted-foreground">Loading PDF…</div>
          )}
        </Document>
      </div>
    </div>
  );
});

PdfViewer.displayName = 'PdfViewer';

export default PdfViewer; 