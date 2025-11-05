"""
Scholar Inbox scraper with improved caption extraction and relevance scores.
"""

import logging
import subprocess
import sys
import requests
import urllib3
from pathlib import Path
from typing import List, Optional
from playwright.sync_api import Error as PlaywrightError, Page, sync_playwright

from .models import Paper, TeaserFigure, PaperRelevance
from .arxiv_client import ArxivClient

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ScholarInboxScraper:
    """Scraper for Scholar Inbox recommendation papers."""
    
    def __init__(self, cache_dir: Path):
        """Initialize scraper with cache directory."""
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.arxiv_client = ArxivClient(cache_dir=str(cache_dir))
        self._arxiv_metadata_cache: dict[str, dict] = {}
    
    def scrape_papers(self, url: str, max_papers: Optional[int] = None) -> List[Paper]:
        """Scrape papers from Scholar Inbox URL."""
        
        with sync_playwright() as p:
            browser = None
            context = None

            try:
                browser = self._launch_browser(p)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                # Capture console logs from the browser
                page.on("console", lambda msg: logger.info(f"[Browser Console] {msg.type}: {msg.text}"))
                
                # Navigate with extended timeout
                logger.info(f"Navigating to {url}")
                page.goto(url, wait_until='networkidle', timeout=90000)
                
                # Wait for page to load - try multiple selectors
                logger.info("Waiting for page to load...")
                try:
                    # Try to find abstract buttons (may not exist on all pages)
                    page.wait_for_selector('button[aria-label="show abstract"]', timeout=10000)
                except:
                    logger.info("Abstract buttons not found, trying alternative selectors...")
                    try:
                        # Try to find paper links
                        page.wait_for_selector('a[href*="arxiv.org"]', timeout=10000)
                    except:
                        logger.warning("No arxiv links found, continuing anyway...")
                
                # Wait for React to render
                page.wait_for_timeout(8000)
                
                # Scroll to load all content
                for i in range(5):
                    page.evaluate('window.scrollBy(0, window.innerHeight)')
                    page.wait_for_timeout(2000)
                
                # Extract papers
                papers = self._extract_all_papers(page)
                
                if max_papers:
                    papers = papers[:max_papers]
                
                logger.info(f"Found {len(papers)} papers")
                
                # Extract full info for each paper
                result_papers = []
                for idx, paper_data in enumerate(papers, 1):
                    logger.info(f"Processing paper {idx}/{len(papers)}: {paper_data.get('titleLink', 'Unknown')}")
                    paper = self._extract_paper_full_info(page, paper_data, idx)
                    if paper:
                        result_papers.append(paper)
                
                return result_papers

            finally:
                if context:
                    context.close()
                if browser:
                    browser.close()

    def _launch_browser(self, playwright):
        """Launch Chromium, installing browsers on-demand when necessary."""

        install_attempted = False

        while True:
            try:
                return playwright.chromium.launch(headless=True)
            except PlaywrightError as err:
                should_retry = (
                    not install_attempted and
                    any(keyword in str(err).lower() for keyword in ["executable doesn't exist", "playwright install"])
                )

                if not should_retry:
                    raise

                install_attempted = True
                logger.info("Playwright が未セットアップのため 'playwright install chromium' を実行します...")
                self._install_playwright_browsers()

    def _install_playwright_browsers(self):
        """Install Playwright Chromium runtime via subprocess."""

        try:
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=True,
            )
        except subprocess.CalledProcessError as err:
            logger.error("Playwright ブラウザのインストールに失敗しました。", exc_info=True)
            raise RuntimeError("Failed to install Playwright browsers") from err
    
    def _extract_all_papers(self, page: Page) -> List[dict]:
        """Extract all recommendation papers from the page using Bibtex."""
        
        papers_data = page.evaluate("""
        async () => {
            console.log('=== Starting paper extraction ===');
            
            // Find all Share buttons
            const allShareButtons = Array.from(document.querySelectorAll('button[aria-label="Share this paper"]'));
            console.log(`Found ${allShareButtons.length} share buttons`);
            
            // Filter out duplicate share buttons (each paper has 2 buttons)
            // Keep only one button per paper by checking y-coordinate proximity
            const shareButtons = [];
            const seenYPositions = new Set();
            
            for (const btn of allShareButtons) {
                const rect = btn.getBoundingClientRect();
                const y = Math.round(rect.y / 100) * 100; // Round to nearest 100px
                
                if (!seenYPositions.has(y)) {
                    seenYPositions.add(y);
                    shareButtons.push(btn);
                }
            }
            
            console.log(`Filtered to ${shareButtons.length} unique papers`);
            
            const allPapers = [];
            
            for (let i = 0; i < shareButtons.length; i++) {
                const shareBtn = shareButtons[i];
                console.log(`\n--- Processing paper ${i + 1}/${shareButtons.length} ---`);
                
                try {
                    // Click share button
                    shareBtn.click();
                    await new Promise(r => setTimeout(r, 800));
                    
                    // Click bibtex button
                    const bibtexBtn = document.querySelector('button[aria-label="Copy bibtex or add this paper to Zotero/Mendeley"]');
                    if (!bibtexBtn) {
                        console.log('  ✗ Bibtex button not found');
                        // Close Share dialog with backdrop click
                        const backdrop = document.querySelector('[class*="MuiBackdrop-root"]');
                        if (backdrop) {
                            backdrop.click();
                            await new Promise(r => setTimeout(r, 300));
                        }
                        continue;
                    }
                    
                    bibtexBtn.click();
                    await new Promise(r => setTimeout(r, 500));
                    
                    // Get bibtex from textarea
                    const textareas = document.querySelectorAll('textarea');
                    let bibtex = '';
                    for (const ta of textareas) {
                        if (ta.value && (ta.value.includes('@inproceedings') || ta.value.includes('@article'))) {
                            bibtex = ta.value;
                            break;
                        }
                    }
                    
                    if (!bibtex) {
                        console.log('  ✗ Bibtex not found in textarea');
                        // Close both dialogs with backdrop clicks
                        for (let i = 0; i < 2; i++) {
                            const backdrop = document.querySelector('[class*="MuiBackdrop-root"]');
                            if (backdrop) {
                                backdrop.click();
                                await new Promise(r => setTimeout(r, 300));
                            }
                        }
                        continue;
                    }
                    
                    console.log(`  ✓ Got bibtex: ${bibtex.substring(0, 100)}...`);
                    
                    // Parse bibtex
                    const parsed = {};
                    
                    // Extract author
                    const authorMatch = bibtex.match(/author=\{([^}]+)\}/);
                    if (authorMatch) parsed.authors = authorMatch[1];
                    
                    // Extract title
                    const titleMatch = bibtex.match(/title=\{([^}]+)\}/);
                    if (titleMatch) parsed.title = titleMatch[1];
                    
                    // Extract journal
                    const journalMatch = bibtex.match(/journal=\{([^}]+)\}/);
                    if (journalMatch) parsed.journal = journalMatch[1];
                    
                    // Extract booktitle
                    const booktitleMatch = bibtex.match(/booktitle=\{([^}]+)\}/);
                    if (booktitleMatch) parsed.booktitle = booktitleMatch[1];
                    
                    // Extract volume (arXiv ID for arXiv papers)
                    const volumeMatch = bibtex.match(/volume=\{([^}]+)\}/);
                    if (volumeMatch) parsed.volume = volumeMatch[1];
                    
                    // Extract year
                    const yearMatch = bibtex.match(/year=\{([^}]+)\}/);
                    if (yearMatch) parsed.year = yearMatch[1];
                    
                    console.log('  Parsed:', parsed);
                    
                    // Determine paper type and get URL
                    let paperUrl = null;
                    let arxivId = null;
                    let isArxiv = false;
                    
                    if (parsed.journal === 'arXiv' && parsed.volume) {
                        // arXiv paper
                        arxivId = parsed.volume;
                        paperUrl = `https://arxiv.org/abs/${arxivId}`;
                        isArxiv = true;
                        console.log(`  ✓ arXiv paper: ${arxivId}`);
                    } else {
                        // Non-arXiv paper - find title link
                        // Go back to find the title link for this paper
                        // We need to find the paper container that contains this share button
                        let container = shareBtn;
                        for (let level = 0; level < 10; level++) {
                            container = container.parentElement;
                            if (!container) break;
                            
                            // Look for a link with the title
                            const titleLinks = Array.from(container.querySelectorAll('a'));
                            for (const link of titleLinks) {
                                const linkText = (link.textContent || '').trim();
                                // Match title (allow some variation due to special chars)
                                if (linkText.length > 30 && parsed.title && 
                                    (linkText.includes(parsed.title.substring(0, 30)) || 
                                     parsed.title.includes(linkText.substring(0, 30)))) {
                                    paperUrl = link.href;
                                    console.log(`  ✓ Found title link: ${paperUrl}`);
                                    break;
                                }
                            }
                            if (paperUrl) break;
                        }
                        
                        if (!paperUrl) {
                            console.log('  ✗ Could not find paper URL');
                        }
                    }
                    
                    // Close all dialogs by clicking backdrop twice
                    // First click closes Bibtex dialog, second click closes Share dialog
                    for (let i = 0; i < 2; i++) {
                        const backdrop = document.querySelector('[class*="MuiBackdrop-root"]');
                        if (backdrop) {
                            backdrop.click();
                            await new Promise(r => setTimeout(r, 300));
                        }
                    }
                    await new Promise(r => setTimeout(r, 200));
                    
                    if (!parsed.title || !parsed.authors) {
                        console.log('  ✗ Missing title or authors');
                        continue;
                    }
                    
                    allPapers.push({
                        title: parsed.title,
                        authors: parsed.authors,
                        arxivId: arxivId,
                        paperUrl: paperUrl,
                        isArxiv: isArxiv,
                        journal: parsed.journal,
                        booktitle: parsed.booktitle,
                        year: parsed.year,
                        bibtex: bibtex,
                        metadata: {}
                    });
                    
                    console.log(`  ✓ Added paper: ${parsed.title.substring(0, 50)}`);
                    
                } catch (err) {
                    console.log(`  ✗ Error processing paper: ${err.message}`);
                    // Try to close any open dialogs with backdrop clicks
                    try {
                        for (let i = 0; i < 2; i++) {
                            const backdrop = document.querySelector('[class*="MuiBackdrop-root"]');
                            if (backdrop) {
                                backdrop.click();
                                await new Promise(r => setTimeout(r, 300));
                            }
                        }
                    } catch (e) {}
                }
            }
            
            console.log(`\n=== Extracted ${allPapers.length} papers ===`);
            
            // Now extract relevance scores for each paper
            const validPapers = allPapers;
            
            // Extract metadata and relevance scores for each paper
            validPapers.forEach((paper, paperIndex) => {
                console.log(`\n=== DEBUG: Extracting relevance for paper ${paperIndex + 1}: ${paper.title.substring(0, 50)} ===`);
                
                // Find the container for this paper by looking for Share button
                const shareButtons = Array.from(document.querySelectorAll('button[aria-label="Share this paper"]'));
                if (paperIndex >= shareButtons.length) {
                    console.log('  ✗ Share button not found for this paper index');
                    return;
                }
                
                let container = shareButtons[paperIndex];
                for (let i = 0; i < 15; i++) {
                    container = container.parentElement;
                    if (!container) break;
                    
                    console.log(`  Level ${i}: ${container.tagName}.${container.className}`);
                    
                    // DEBUG: Log all text content in this container
                    const containerText = (container.textContent || '').trim();
                    if (containerText.length < 500) {
                        console.log(`  Container text: ${containerText.substring(0, 200)}`);
                    }
                    
                    // Find all elements that might contain numbers
                    const allElements = Array.from(container.querySelectorAll('span, div'));
                    const numbersFound = [];
                    
                    for (const el of allElements) {
                        const text = (el.textContent || '').trim();
                        const num = parseInt(text);
                        
                        // Collect ALL numbers for debugging
                        if (!isNaN(num) && text === num.toString() && num >= 0 && num < 10000) {
                            // Skip years
                            if (num >= 2000 && num <= 2100) continue;
                            
                            const rect = el.getBoundingClientRect();
                            numbersFound.push({
                                num: num,
                                tag: el.tagName,
                                class: el.className,
                                width: Math.round(rect.width),
                                height: Math.round(rect.height),
                                x: Math.round(rect.x),
                                y: Math.round(rect.y)
                            });
                        }
                    }
                    
                    console.log(`  Found ${numbersFound.length} numbers:`, numbersFound.slice(0, 10));
                    
                    // Try to find 3 numbers in expected ranges
                    // relevance: 0-100, thumbs_up: 0-50, read_by: 0-1000
                    const validNumbers = numbersFound.filter(n => n.num >= 0 && n.num < 1000).map(n => n.num);
                    
                    if (validNumbers.length >= 3) {
                        // Try different combinations
                        for (let j = 0; j <= validNumbers.length - 3; j++) {
                            const r = validNumbers[j];
                            const t = validNumbers[j + 1];
                            const v = validNumbers[j + 2];
                            
                            console.log(`  Trying combination: r=${r}, t=${t}, v=${v}`);
                            
                            // Check if numbers fit expected pattern
                            if (r >= 0 && r <= 100 && t >= 0 && t <= 50 && v >= 0 && v <= 1000) {
                                paper.metadata.relevance = {
                                    relevance_score: r,
                                    thumbs_up: t,
                                    read_by: v
                                };
                                console.log(`  ✓ Found relevance pattern: ${r}, ${t}, ${v}`);
                                break;
                            }
                        }
                        
                        if (paper.metadata.relevance) break;
                    }
                }
                
                if (!paper.metadata.relevance) {
                    console.log(`  ✗ No relevance pattern found for this paper`);
                }
            });
            
            return validPapers;
        }
        """)
        
        return papers_data
    
    def _extract_paper_full_info(self, page: Page, paper_data: dict, index: int) -> Optional[Paper]:
        """Extract full information for a paper (supports both arXiv and non-arXiv)."""
        
        try:
            # New Bibtex-based format
            title = paper_data.get('title')
            authors_text = paper_data.get('authors', '')
            arxiv_id = paper_data.get('arxivId')
            is_arxiv = paper_data.get('isArxiv', False)
            paper_url = paper_data.get('paperUrl')
            
            # Parse authors
            authors = self._parse_authors(authors_text)
            
            # Get metadata
            metadata = paper_data.get('metadata') or {}
            
            # For arXiv papers, fetch official metadata
            arxiv_metadata = None
            arxiv_html_url = None
            arxiv_url = None
            
            if is_arxiv and arxiv_id:
                arxiv_html_url = f"https://arxiv.org/html/{arxiv_id}"
                arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
                
                arxiv_metadata = self._get_arxiv_metadata(arxiv_id)
                if arxiv_metadata:
                    title = arxiv_metadata.get('title') or title
                    authors = arxiv_metadata.get('authors') or authors
                    metadata['categories'] = arxiv_metadata.get('categories') or metadata.get('categories', [])
                    metadata['submitted_date'] = arxiv_metadata.get('published') or metadata.get('submitted_date')
                    metadata['updated_date'] = arxiv_metadata.get('updated') or metadata.get('updated_date')
                    metadata['pdf_url'] = arxiv_metadata.get('pdf_url') or metadata.get('pdf_url')
                    metadata['abs_url'] = arxiv_metadata.get('abs_url') or metadata.get('abs_url')
                    metadata['doi'] = arxiv_metadata.get('doi') or metadata.get('doi')
            
            # For non-arXiv papers, use the paper URL from bibtex
            if not is_arxiv:
                arxiv_url = paper_url  # Use the conference/journal URL
                # Set conference from booktitle or journal
                if paper_data.get('booktitle'):
                    metadata['conference'] = paper_data.get('booktitle')
                elif paper_data.get('journal'):
                    metadata['conference'] = paper_data.get('journal')
            
            # Extract relevance scores
            relevance_data = metadata.get('relevance')
            paper_relevance = None
            if relevance_data:
                paper_relevance = PaperRelevance(
                    relevance_score=relevance_data.get('relevance_score', 0),
                    thumbs_up=relevance_data.get('thumbs_up', 0),
                    read_by=relevance_data.get('read_by', 0)
                )
            
            # Extract abstract
            abstract = ""
            if is_arxiv and arxiv_id:
                abstract = self._extract_abstract_for_arxiv(page, arxiv_id)
            if arxiv_metadata and arxiv_metadata.get('abstract'):
                abstract = arxiv_metadata['abstract']
            # For non-arXiv papers, try to extract abstract from the page
            elif not is_arxiv:
                abstract = self._extract_abstract_generic(page, title)
            
            # Create paper object
            paper = Paper(
                title=title or "",
                authors=authors,
                abstract=abstract,
                arxiv_id=arxiv_id,
                arxiv_url=(metadata.get('abs_url') or arxiv_url),
                arxiv_html_url=arxiv_html_url,
                github_url=metadata.get('github_url'),
                conference=metadata.get('conference'),
                submitted_date=metadata.get('submitted_date'),
                categories=metadata.get('categories', []),
                paper_relevance=paper_relevance
            )
            
            # Extract teaser figures with captions
            if is_arxiv and arxiv_id:
                paper.teaser_figures = self._extract_teaser_figures_for_arxiv(page, arxiv_id, paper)
            else:
                # For non-arXiv papers, extract figures by title
                paper.teaser_figures = self._extract_teaser_figures_generic(page, title, paper)
            
            return paper
        
        except Exception as e:
            logger.error(f"Error extracting paper full info: {e}")
            return None

    def _get_arxiv_metadata(self, arxiv_id: str) -> Optional[dict]:
        """Retrieve and cache arXiv metadata for a given ID."""
        if arxiv_id in self._arxiv_metadata_cache:
            return self._arxiv_metadata_cache[arxiv_id]

        metadata = self.arxiv_client.fetch_paper_metadata_sync(arxiv_id)
        if metadata:
            self._arxiv_metadata_cache[arxiv_id] = metadata
        return metadata
    
    def _extract_abstract_generic(self, page: Page, title: str) -> str:
        """Extract abstract for non-arXiv papers by finding the abstract button near the title."""
        try:
            # Try to find abstract by looking for the paper with this title
            abstract = page.evaluate(f"""
            async (paperTitle) => {{
                // Find all links that might contain the title
                const allLinks = Array.from(document.querySelectorAll('a'));
                let titleLink = null;
                
                for (const link of allLinks) {{
                    const linkText = (link.textContent || '').trim();
                    // Match title (allow some variation)
                    if (linkText.length > 30 && paperTitle && 
                        (linkText.includes(paperTitle.substring(0, 30)) || 
                         paperTitle.includes(linkText.substring(0, 30)))) {{
                        titleLink = link;
                        break;
                    }}
                }}
                
                if (!titleLink) return '';
                
                // Find the container
                let container = titleLink.parentElement;
                for (let i = 0; i < 10; i++) {{
                    if (!container) break;
                    
                    // Find abstract button
                    const abstractBtn = container.querySelector('button[aria-label="show abstract"]');
                    if (abstractBtn) {{
                        abstractBtn.click();
                        
                        // Wait for abstract to appear
                        await new Promise(resolve => setTimeout(resolve, 2000));
                        
                        // Find abstract text (in <p> tags)
                        const paragraphs = container.querySelectorAll('p');
                        for (const p of paragraphs) {{
                            const text = p.textContent || '';
                            if (text.length > 100) {{
                                return text.trim();
                            }}
                        }}
                    }}
                    
                    container = container.parentElement;
                }}
                
                return '';
            }}
            """, title)
            
            return abstract if isinstance(abstract, str) else ""
        
        except Exception as e:
            logger.debug(f"Could not extract abstract for non-arXiv paper: {e}")
            return ""
    
    def _extract_abstract_for_arxiv(self, page: Page, arxiv_id: str) -> str:
        """Extract abstract by clicking abstract button for specific arXiv ID."""
        try:
            abstract = page.evaluate(f"""
            async (arxivId) => {{
                // Find all links with this arXiv ID
                const links = Array.from(document.querySelectorAll(`a[href*="${{arxivId}}"]`));
                if (links.length === 0) return '';
                
                // Find the container
                let container = links[0].parentElement;
                for (let i = 0; i < 10; i++) {{
                    if (!container) break;
                    
                    // Find abstract button
                    const abstractBtn = container.querySelector('button[aria-label="show abstract"]');
                    if (abstractBtn) {{
                        abstractBtn.click();
                        
                        // Wait for abstract to appear
                        await new Promise(resolve => setTimeout(resolve, 2000));
                        
                        // Find abstract text (in <p> tags)
                        const paragraphs = container.querySelectorAll('p');
                        for (const p of paragraphs) {{
                            const text = p.textContent || '';
                            if (text.length > 100) {{
                                return text.trim();
                            }}
                        }}
                    }}
                    
                    container = container.parentElement;
                }}
                
                return '';
            }}
            """, arxiv_id)
            
            return abstract if isinstance(abstract, str) else ""
        
        except Exception as e:
            logger.debug(f"Could not extract abstract: {e}")
            return ""
    
    def _extract_teaser_figures_generic(self, page: Page, title: str, paper: Paper) -> List[TeaserFigure]:
        """Extract teaser figures for non-arXiv papers by finding the paper container via title."""
        figures = []
        
        try:
            figures_data = page.evaluate(f"""
            async (paperTitle) => {{
                console.log(`\n=== DEBUG: Extracting figures for paper: ${{paperTitle.substring(0, 50)}} ===`);
                
                const figuresData = [];
                
                // Find the title link to locate the paper container
                const allLinks = Array.from(document.querySelectorAll('a'));
                let titleLink = null;
                
                for (const link of allLinks) {{
                    const linkText = (link.textContent || '').trim();
                    // Match title (allow some variation)
                    if (linkText.length > 30 && paperTitle && 
                        (linkText.includes(paperTitle.substring(0, 30)) || 
                         paperTitle.includes(linkText.substring(0, 30)))) {{
                        titleLink = link;
                        break;
                    }}
                }}
                
                if (!titleLink) {{
                    console.log('Title link not found, cannot locate paper container');
                    return [];
                }}
                
                // Find the paper container by traversing up from the title link
                let paperContainer = titleLink;
                for (let i = 0; i < 15; i++) {{
                    if (!paperContainer) break;
                    
                    // Check for "show more" button and click it
                    const showMoreBtn = paperContainer.querySelector('button[aria-label="show more"]');
                    if (showMoreBtn) {{
                        console.log(`  Found 'show more' button at level ${{i}}, clicking...`);
                        showMoreBtn.click();
                        // Wait for images to load
                        await new Promise(resolve => setTimeout(resolve, 2000));
                    }}
                    
                    // Look for images within this container
                    const imagesInContainer = paperContainer.querySelectorAll('img');
                    
                    // Check if this container has images with .jpeg/.jpg extension
                    const validImages = Array.from(imagesInContainer).filter(img => {{
                        const src = img.src || '';
                        const filename = src.substring(src.lastIndexOf('/') + 1);
                        // Match pattern: number.number.jpeg (e.g., 4449266.0.jpeg)
                        return /^\\d+\\.\\d+\\.jpe?g$/i.test(filename);
                    }});
                    
                    if (validImages.length > 0) {{
                        console.log(`Found paper container at level ${{i}} with ${{validImages.length}} images`);
                        
                        // Extract each image with its caption
                        for (let imgIdx = 0; imgIdx < validImages.length; imgIdx++) {{
                            const img = validImages[imgIdx];
                            const src = img.src;
                            const filename = src.substring(src.lastIndexOf('/') + 1);
                            
                            console.log(`\nProcessing image ${{imgIdx + 1}}: ${{filename}}`);
                            
                            // Find the figure container (colored box) by traversing up from the image
                            let figContainer = img.parentElement;
                            let caption = '';
                            
                            for (let level = 0; level < 8; level++) {{
                                if (!figContainer) break;
                                
                                const containerText = figContainer.textContent || '';
                                
                                // Check if this container has a figure caption
                                const captionMatch = containerText.match(/(Fig\\.?\\s*\\d+|Figure\\s*\\d+|TABLE\\s*[IVX]+)[.:]/i);
                                
                                if (captionMatch) {{
                                    console.log(`  Level ${{level}}: Found caption starting with: ${{captionMatch[0]}}`);
                                    
                                    // Extract full caption text
                                    const captionPattern = new RegExp(`(${{captionMatch[0]}}[^\\n]*(?:\\n[^\\n]+)*)`, 'i');
                                    const fullCaptionMatch = containerText.match(captionPattern);
                                    
                                    if (fullCaptionMatch) {{
                                        caption = fullCaptionMatch[1]
                                            .replace(/\\s+/g, ' ')
                                            .trim()
                                            .substring(0, 500);
                                        
                                        console.log(`  Extracted caption: ${{caption.substring(0, 100)}}...`);
                                        break;
                                    }}
                                }}
                                
                                figContainer = figContainer.parentElement;
                            }}
                            
                            // Fallback: if no caption found, use default
                            if (!caption) {{
                                caption = `図${{imgIdx + 1}}`;
                                console.log(`  No caption found, using default: ${{caption}}`);
                            }}
                            
                            figuresData.push({{
                                url: src,
                                caption: caption
                            }});
                        }}
                        
                        break;
                    }}
                    
                    paperContainer = paperContainer.parentElement;
                }}
                
                console.log(`\nTotal figures extracted: ${{figuresData.length}}`);
                return figuresData;
            }}
            """, title)
            
            # Download images (remove duplicates by URL and caption combination)
            seen_combinations = set()
            unique_figures = []
            for fig_data in figures_data:
                # Create a unique key from URL and caption prefix (first 50 chars)
                caption_prefix = fig_data['caption'][:50] if fig_data['caption'] else ''
                combination_key = (fig_data['url'], caption_prefix)
                
                if combination_key not in seen_combinations:
                    seen_combinations.add(combination_key)
                    unique_figures.append(fig_data)
            
            logger.info(f"Extracted {len(figures_data)} figures, {len(unique_figures)} unique after deduplication")
            
            # Use a generic ID for non-arXiv papers (based on title hash)
            import hashlib
            paper_id = hashlib.md5(title.encode()).hexdigest()[:12]
            
            for idx, fig_data in enumerate(unique_figures):
                local_path = self._download_image(fig_data['url'], paper_id, idx)
                if local_path:
                    figures.append(TeaserFigure(
                        image_url=fig_data['url'],
                        caption=fig_data['caption'],
                        local_path=str(local_path)
                    ))
                    logger.info(f"Downloaded figure {idx + 1}: {fig_data['caption'][:50]}...")
        
        except Exception as e:
            logger.warning(f"Failed to extract teaser figures for non-arXiv paper: {e}")
        
        return figures
    
    def _extract_teaser_figures_for_arxiv(self, page: Page, arxiv_id: str, paper: Paper) -> List[TeaserFigure]:
        """Extract teaser figures with proper captions for specific arXiv ID."""
        figures = []
        
        try:
            figures_data = page.evaluate(f"""
            async (arxivId) => {{
                console.log(`\n=== DEBUG: Extracting figures for arXiv ID ${{arxivId}} ===`);
                
                // Strategy: Find the paper container first, then extract all images within it
                const figuresData = [];
                
                // Find links with this arXiv ID to locate the paper container
                const links = Array.from(document.querySelectorAll(`a[href*="${{arxivId}}"]`));
                console.log(`Found ${{links.length}} links with arXiv ID ${{arxivId}}`);
                
                if (links.length === 0) {{
                    console.log('No links found, cannot locate paper container');
                    return [];
                }}
                
                // Find the paper container by traversing up from the first link
                let paperContainer = links[0];
                for (let i = 0; i < 15; i++) {{
                    if (!paperContainer) break;
                    
                    // Check for "show more" button and click it
                    const showMoreBtn = paperContainer.querySelector('button[aria-label="show more"]');
                    if (showMoreBtn) {{
                        console.log(`  Found 'show more' button at level ${{i}}, clicking...`);
                        showMoreBtn.click();
                        // Wait for images to load
                        await new Promise(resolve => setTimeout(resolve, 2000));
                    }}
                    
                    // Look for images within this container
                    const imagesInContainer = paperContainer.querySelectorAll('img');
                    
                    // Check if this container has images with .jpeg/.jpg extension
                    const validImages = Array.from(imagesInContainer).filter(img => {{
                        const src = img.src || '';
                        const filename = src.substring(src.lastIndexOf('/') + 1);
                        // Match pattern: number.number.jpeg (e.g., 4449266.0.jpeg)
                        return /^\\d+\\.\\d+\\.jpe?g$/i.test(filename);
                    }});
                    
                    if (validImages.length > 0) {{
                        console.log(`Found paper container at level ${{i}} with ${{validImages.length}} images`);
                        
                        // Extract each image with its caption
                        for (let imgIdx = 0; imgIdx < validImages.length; imgIdx++) {{
                            const img = validImages[imgIdx];
                            const src = img.src;
                            const filename = src.substring(src.lastIndexOf('/') + 1);
                            
                            console.log(`\nProcessing image ${{imgIdx + 1}}: ${{filename}}`);
                            
                            // Find the figure container (colored box) by traversing up from the image
                            let figContainer = img.parentElement;
                            let caption = '';
                            
                            for (let level = 0; level < 8; level++) {{
                                if (!figContainer) break;
                                
                                const containerText = figContainer.textContent || '';
                                
                                // Check if this container has a figure caption
                                const captionMatch = containerText.match(/(Fig\\.?\\s*\\d+|Figure\\s*\\d+|TABLE\\s*[IVX]+)[.:]/i);
                                
                                if (captionMatch) {{
                                    console.log(`  Level ${{level}}: Found caption starting with: ${{captionMatch[0]}}`);
                                    
                                    // Extract full caption text
                                    const captionPattern = new RegExp(`(${{captionMatch[0]}}[^\\n]*(?:\\n[^\\n]+)*)`, 'i');
                                    const fullCaptionMatch = containerText.match(captionPattern);
                                    
                                    if (fullCaptionMatch) {{
                                        caption = fullCaptionMatch[1]
                                            .replace(/\\s+/g, ' ')
                                            .trim()
                                            .substring(0, 500);
                                        
                                        console.log(`  Extracted caption: ${{caption.substring(0, 100)}}...`);
                                        break;
                                    }}
                                }}
                                
                                figContainer = figContainer.parentElement;
                            }}
                            
                            // Fallback: if no caption found, use default
                            if (!caption) {{
                                caption = `図${{imgIdx + 1}}`;
                                console.log(`  No caption found, using default: ${{caption}}`);
                            }}
                            
                            figuresData.push({{
                                url: src,
                                caption: caption
                            }});
                        }}
                        
                        break;
                    }}
                    
                    paperContainer = paperContainer.parentElement;
                }}
                
                console.log(`\nTotal figures extracted: ${{figuresData.length}}`);
                return figuresData;
            }}
            """, arxiv_id)
            
            # Download images (remove duplicates by URL and caption combination)
            seen_combinations = set()
            unique_figures = []
            for fig_data in figures_data:
                # Create a unique key from URL and caption prefix (first 50 chars)
                caption_prefix = fig_data['caption'][:50] if fig_data['caption'] else ''
                combination_key = (fig_data['url'], caption_prefix)
                
                if combination_key not in seen_combinations:
                    seen_combinations.add(combination_key)
                    unique_figures.append(fig_data)
            
            logger.info(f"Extracted {len(figures_data)} figures, {len(unique_figures)} unique after deduplication")
            
            for idx, fig_data in enumerate(unique_figures):
                local_path = self._download_image(fig_data['url'], arxiv_id, idx)
                if local_path:
                    figures.append(TeaserFigure(
                        image_url=fig_data['url'],
                        caption=fig_data['caption'],
                        local_path=str(local_path)
                    ))
                    logger.info(f"Downloaded figure {idx + 1}: {fig_data['caption'][:50]}...")
        
        except Exception as e:
            logger.debug(f"Could not extract teaser figures: {e}")
        
        return figures
    
    def _parse_authors(self, authors_text: str) -> List[str]:
        """Parse authors from text."""
        if not authors_text:
            return []
        
        # Split by comma
        authors = [a.strip() for a in authors_text.split(',') if a.strip()]
        return authors
    
    def _download_image(self, url: str, arxiv_id: str, index: int) -> Optional[Path]:
        """Download and cache an image."""
        try:
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                url = 'https://scholar-inbox.com' + url
            
            ext = '.jpg'
            if '.png' in url:
                ext = '.png'
            elif '.gif' in url:
                ext = '.gif'
            elif '.webp' in url:
                ext = '.webp'
            
            # Use URL hash to ensure unique filenames for different images
            import hashlib
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"{arxiv_id}_fig_{index}_{url_hash}{ext}"
            filepath = self.cache_dir / filename
            
            # Always download and overwrite to avoid stale cache issues
            # (Previous runs may have left incorrect files)
            response = requests.get(url, timeout=10, verify=False)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return filepath
        
        except Exception as e:
            logger.warning(f"Failed to download image {url}: {e}")
            return None
    
    def cleanup_images(self, papers: List[Paper]):
        """Delete cached images after posting to Slack."""
        for paper in papers:
            for figure in paper.teaser_figures:
                if figure.local_path:
                    try:
                        path = Path(figure.local_path)
                        if path.exists():
                            path.unlink()
                            logger.debug(f"Deleted cached image: {path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete {figure.local_path}: {e}")
