from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from src.config import settings
from src.search import search_companies
from src.scraper import scraper
from src.llm import extract_company_info, optimize_search_query
from src.db import db
from src.models import CompanyDocument
from rich.console import Console
import tldextract

console = Console()

@tool
async def search_web(queries: list[str]) -> str:
    """
    Search the web for software companies based on a list of highly optimized queries.
    Returns a combined JSON string of unique search results containing titles and links.
    """
    if isinstance(queries, str):
        try:
            import ast
            parsed = ast.literal_eval(queries)
            if isinstance(parsed, list):
                queries = parsed
            else:
                queries = [queries]
        except (ValueError, SyntaxError):
            queries = [queries]
            
    console.print(f"[cyan]Action:[/cyan] Running {len(queries)} diverse web searches to maximize results...")
    
    tasks = [search_companies(q) for q in queries]
    all_results = await asyncio.gather(*tasks)
    
    # Flatten and deduplicate by domain
    unique_domains = set()
    aggregated_output = []
    
    for results in all_results:
        for r in results:
            link = r.get('link')
            title = r.get('title')
            if not link:
                continue
            ext = tldextract.extract(link)
            domain = f"{ext.domain}.{ext.suffix}"
            if domain not in unique_domains:
                unique_domains.add(domain)
                aggregated_output.append(f"Title: {title}\nLink: {link}")
    
    if not aggregated_output:
        return "No results found."
        
    return "\n\n".join(aggregated_output)

@tool
async def scrape_and_extract(url: str, user_context: str) -> str:
    """
    Scrape a company's website or job board link and extract structured hiring information.
    Saves the data directly to the MongoDB database.
    Returns a summary of the extracted company information.
    """
    ext = tldextract.extract(url)
    if ext.domain in ['facebook', 'twitter', 'instagram', 'tiktok', 'youtube', 'linkedin', 'indeed', 'glassdoor', 'naukri', 'wellfound']:
        return f"Skipped scraping {ext.domain} due to strong anti-bot protections. Please try scraping an official company website instead."

    console.print(f"[magenta]Action:[/magenta] Scraping and extracting: {url}")
    scraped_text = await scraper.crawl_company(url)
    
    if not scraped_text:
        return f"Failed to extract any text from {url}"
        
    source_id = await db.save_raw_scrape(url, scraped_text)
    company_info = await extract_company_info(scraped_text, url)
    
    if not company_info:
        return f"Failed to extract structured data from {url}"
        
    doc = CompanyDocument(
        **company_info.model_dump(),
        search_query=user_context,
        source_id=source_id
    )
    
    await db.save_company(doc)
    
    jobs = len(doc.jobs)
    emails = ", ".join(doc.contact_emails) if doc.contact_emails else "None"
    tech = ", ".join(doc.tech_stack) if doc.tech_stack else "None"
    
    return f"Successfully processed {doc.company}. Jobs found: {jobs}, Emails: {emails}, Tech stack: {tech}."

llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0.1)
tools = [optimize_search_query, search_web, scrape_and_extract]

system_prompt = """You are an autonomous AI agent specialized in finding software companies, extracting hiring data, and aggregating the results.
You have access to three tools:
1. `optimize_search_query`: First, pass the user's raw input to this tool to get a highly optimized Google Dork query.
2. `search_web`: Search Google for companies hiring. Pass the optimized query from the first step to this tool.
3. `scrape_and_extract`: Takes a URL from the search results and the original user context, scrapes the page, extracts structured data, saves it to the database, and returns a summary.

Instructions:
1. When the user gives you a request, first call `optimize_search_query` to generate a list of 5 diverse search queries.
2. Take the list of optimized queries and call `search_web` to aggregate a massive list of unique companies.
3. Look at the search results. Identify the best matching links. **CRITICAL**: ONLY select official company websites or direct company career pages (e.g. company.com/careers). DO NOT try to scrape LinkedIn, Indeed, Glassdoor, Naukri, or Wellfound as they block automated scrapers.
4. Call `scrape_and_extract` on the 10 most promising official company URLs to maximize the amount of cold email prospects. You can call this tool multiple times in parallel for different URLs.
5. Finally, summarize all your findings and the companies you successfully processed in a clear, concise markdown report for the user. Mention the emails and jobs found. Do not invent data.
"""

agent = create_react_agent(llm, tools, prompt=system_prompt)
