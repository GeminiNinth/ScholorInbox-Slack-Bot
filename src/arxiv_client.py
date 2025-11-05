"""arXiv API client and PDF handling module."""

import logging
import re
from pathlib import Path
from typing import Optional

import arxiv
import httpx
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class ArxivClient:
    """Client for fetching papers from arXiv API and processing PDFs."""
    
    def __init__(self, cache_dir: str = "data/cache"):
        """Initialize arXiv client.
        
        Args:
            cache_dir: Directory to cache downloaded PDFs
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_arxiv_id(self, url: str) -> Optional[str]:
        """Extract arXiv ID from URL.
        
        Args:
            url: URL containing arXiv ID
            
        Returns:
            arXiv ID if found, None otherwise
        """
        match = re.search(r'arxiv\.org/(?:abs|pdf|html)/(\d+\.\d+)', url, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def is_arxiv_url(self, url: str) -> bool:
        """Check if URL is an arXiv URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is from arXiv, False otherwise
        """
        return 'arxiv.org' in url.lower()
    
    def _build_metadata(self, paper) -> dict:
        """Convert arxiv.Result into metadata dictionary."""
        published = paper.published.strftime('%Y-%m-%d') if getattr(paper, 'published', None) else None
        updated = paper.updated.strftime('%Y-%m-%d') if getattr(paper, 'updated', None) else None

        metadata = {
            'title': paper.title.strip() if paper.title else None,
            'authors': [author.name for author in getattr(paper, 'authors', [])],
            'abstract': paper.summary.strip() if getattr(paper, 'summary', None) else None,
            'published': published,
            'updated': updated,
            'pdf_url': paper.pdf_url,
            'entry_id': paper.entry_id,
            'primary_category': paper.primary_category,
            'categories': list(paper.categories) if getattr(paper, 'categories', None) else [],
            'comment': paper.comment,
            'journal_ref': paper.journal_ref,
            'doi': paper.doi,
        }

        # Provide convenience URLs when available
        if paper.entry_id:
            metadata['abs_url'] = paper.entry_id
        if getattr(paper, 'get_short_id', None):
            metadata['arxiv_id'] = paper.get_short_id()

        return metadata

    def _fetch_paper_metadata_internal(self, arxiv_id: str) -> Optional[dict]:
        """Internal helper to fetch metadata from arXiv API."""
        try:
            logger.info(f"Fetching metadata for arXiv:{arxiv_id}")

            search = arxiv.Search(id_list=[arxiv_id])
            paper = next(search.results(), None)

            if not paper:
                logger.warning(f"Paper not found: arXiv:{arxiv_id}")
                return None

            metadata = self._build_metadata(paper)

            logger.info(f"Successfully fetched metadata for arXiv:{arxiv_id}")
            return metadata

        except Exception as e:
            logger.error(f"Error fetching metadata for arXiv:{arxiv_id}: {e}")
            return None

    async def fetch_paper_metadata(self, arxiv_id: str) -> Optional[dict]:
        """Fetch paper metadata from arXiv API (async wrapper)."""
        return self._fetch_paper_metadata_internal(arxiv_id)

    def fetch_paper_metadata_sync(self, arxiv_id: str) -> Optional[dict]:
        """Fetch paper metadata from arXiv API (synchronous)."""
        return self._fetch_paper_metadata_internal(arxiv_id)
    
    def download_pdf_sync(self, url: str, arxiv_id: Optional[str] = None) -> Optional[Path]:
        """Download PDF from URL - synchronous version.
        
        Args:
            url: PDF URL
            arxiv_id: Optional arXiv ID for caching
            
        Returns:
            Path to downloaded PDF, or None if download failed
        """
        try:
            # Determine cache filename
            if arxiv_id:
                pdf_path = self.cache_dir / f"{arxiv_id}.pdf"
            else:
                # Use hash of URL as filename
                import hashlib
                url_hash = hashlib.md5(url.encode()).hexdigest()
                pdf_path = self.cache_dir / f"{url_hash}.pdf"
            
            # Check if already cached
            if pdf_path.exists():
                logger.info(f"Using cached PDF: {pdf_path}")
                return pdf_path
            
            # Download PDF
            logger.info(f"Downloading PDF from {url}")
            import requests
            response = requests.get(url, timeout=60.0, verify=False, allow_redirects=True)
            response.raise_for_status()
            
            # Save to cache
            pdf_path.write_bytes(response.content)
            logger.info(f"Downloaded PDF to {pdf_path}")
            return pdf_path
                
        except Exception as e:
            logger.error(f"Error downloading PDF from {url}: {e}")
            return None
    
    async def download_pdf(self, url: str, arxiv_id: Optional[str] = None) -> Optional[Path]:
        """Download PDF from URL.
        
        Args:
            url: PDF URL
            arxiv_id: Optional arXiv ID for caching
            
        Returns:
            Path to downloaded PDF, or None if download failed
        """
        try:
            # Determine cache filename
            if arxiv_id:
                pdf_path = self.cache_dir / f"{arxiv_id}.pdf"
            else:
                # Use hash of URL as filename
                import hashlib
                url_hash = hashlib.md5(url.encode()).hexdigest()
                pdf_path = self.cache_dir / f"{url_hash}.pdf"
            
            # Check if already cached
            if pdf_path.exists():
                logger.info(f"Using cached PDF: {pdf_path}")
                return pdf_path
            
            # Download PDF
            logger.info(f"Downloading PDF from {url}")
            async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
                # Save to cache
                pdf_path.write_bytes(response.content)
                logger.info(f"Downloaded PDF to {pdf_path}")
                return pdf_path
                
        except Exception as e:
            logger.error(f"Error downloading PDF from {url}: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_path: Path, max_pages: int = 20) -> Optional[str]:
        """Extract text from PDF file.
        
        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum number of pages to extract (to avoid huge PDFs)
            
        Returns:
            Extracted text, or None if extraction failed
        """
        try:
            logger.info(f"Extracting text from PDF: {pdf_path}")
            
            reader = PdfReader(pdf_path)
            num_pages = min(len(reader.pages), max_pages)
            
            text_parts = []
            for i in range(num_pages):
                page = reader.pages[i]
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            full_text = '\n\n'.join(text_parts)
            logger.info(f"Extracted {len(full_text)} characters from {num_pages} pages")
            
            return full_text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return None
    
    def get_paper_content_sync(self, url: str, arxiv_id: Optional[str] = None) -> Optional[str]:
        """Get paper content from URL (HTML or PDF) - synchronous version.
        
        Args:
            url: Paper URL (arXiv HTML, PDF, or other)
            arxiv_id: Optional arXiv ID
            
        Returns:
            Paper content as text, or None if retrieval failed
        """
        try:
            # Try HTML first for arXiv papers
            if arxiv_id:
                html_url = f"https://arxiv.org/html/{arxiv_id}"
                logger.info(f"Trying arXiv HTML: {html_url}")
                
                try:
                    import requests
                    response = requests.get(html_url, timeout=30.0)
                    if response.status_code == 200:
                        # Extract text from HTML (simplified)
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Remove script and style elements
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        text = soup.get_text()
                        # Clean up whitespace
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = '\n'.join(chunk for chunk in chunks if chunk)
                        
                        logger.info(f"Successfully fetched arXiv HTML content ({len(text)} chars)")
                        return text
                except Exception as e:
                    logger.info(f"arXiv HTML not available, will try PDF: {e}")
            
            # Try PDF
            pdf_url = url
            if arxiv_id and not url.endswith('.pdf'):
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            
            pdf_path = self.download_pdf_sync(pdf_url, arxiv_id)
            if pdf_path:
                return self.extract_text_from_pdf(pdf_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting paper content: {e}")
            return None
    
    async def get_paper_content(self, url: str, arxiv_id: Optional[str] = None) -> Optional[str]:
        """Get paper content from URL (HTML or PDF).
        
        Args:
            url: Paper URL (arXiv HTML, PDF, or other)
            arxiv_id: Optional arXiv ID
            
        Returns:
            Paper content as text, or None if retrieval failed
        """
        try:
            # Try HTML first for arXiv papers
            if arxiv_id:
                html_url = f"https://arxiv.org/html/{arxiv_id}"
                logger.info(f"Trying arXiv HTML: {html_url}")
                
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(html_url)
                        if response.status_code == 200:
                            # Extract text from HTML (simplified)
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(response.text, 'html.parser')
                            
                            # Remove script and style elements
                            for script in soup(["script", "style"]):
                                script.decompose()
                            
                            text = soup.get_text()
                            # Clean up whitespace
                            lines = (line.strip() for line in text.splitlines())
                            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                            text = '\n'.join(chunk for chunk in chunks if chunk)
                            
                            logger.info(f"Successfully fetched arXiv HTML content ({len(text)} chars)")
                            return text
                except Exception as e:
                    logger.info(f"arXiv HTML not available, will try PDF: {e}")
            
            # Try PDF
            pdf_url = url
            if arxiv_id and not url.endswith('.pdf'):
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            
            pdf_path = await self.download_pdf(pdf_url, arxiv_id)
            if pdf_path:
                return self.extract_text_from_pdf(pdf_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting paper content: {e}")
            return None
