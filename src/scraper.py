import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import tldextract
import asyncio
import random
from rich.console import Console

console = Console()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
]

class Scraper:
    def __init__(self):
        self.target_paths = ['/', '/careers', '/jobs', '/hiring', '/about', '/contact', '/about-us']

    def get_random_headers(self):
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def fetch_page(self, client: httpx.AsyncClient, url: str) -> str:
        try:
            response = await client.get(url, headers=self.get_random_headers(), timeout=15.0, follow_redirects=True)
            if response.status_code == 200:
                return response.text
            return ""
        except Exception:
            # Silently ignore individual page fetch errors as we try multiple paths
            return ""

    def extract_text(self, html: str) -> str:
        if not html:
            return ""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Truncate to avoid massive token counts
        return text[:10000]

    def get_urls_to_scrape(self, base_url: str) -> list[str]:
        ext = tldextract.extract(base_url)
        
        # For job boards and directories, the provided URL is the specific company profile or job post.
        # We don't want to append generic paths like '/careers' to their root domain.
        if ext.domain in ['linkedin', 'indeed', 'naukri', 'glassdoor', 'google', 'ycombinator', 'wellfound', 'angel']:
            return [base_url]
            
        parsed = urlparse(base_url)
        root_url = f"{parsed.scheme}://{parsed.netloc}"
        
        urls = [base_url]
        for path in self.target_paths:
            if path != '/':
                urls.append(root_url + path)
        return list(set(urls))

    async def crawl_company(self, website: str) -> str:
        """
        Visits the homepage and common hiring pages to extract visible text.
        """
        base_url = website if website.startswith('http') else f"https://{website}"
        extracted_texts = []
        
        async with httpx.AsyncClient() as client:
            tasks = []
            urls_to_scrape = self.get_urls_to_scrape(base_url)
            for url in urls_to_scrape:
                tasks.append(self.fetch_page(client, url))
            
            html_results = await asyncio.gather(*tasks)
            
            for html in html_results:
                text = self.extract_text(html)
                if text:
                    extracted_texts.append(text)
                    
        return "\n---\n".join(extracted_texts)

scraper = Scraper()
