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
async def search_web(query: str) -> str:
    """
    Search the web for software companies based on a highly optimized query.
    Returns a JSON string of search results containing titles and links.
    """
    console.print(f"[cyan]Action:[/cyan] Searching web for: {query}")
    results = await search_companies(query)
    
    if not results:
        return "No results found."
        
    output = []
    for r in results[:15]: # Limit to top 15
        output.append(f"Title: {r.get('title')}\nLink: {r.get('link')}")
    return "\n\n".join(output)

@tool
async def scrape_and_extract(url: str, user_context: str) -> str:
    """
    Scrape a company's website or job board link and extract structured hiring information.
    Saves the data directly to the MongoDB database.
    Returns a summary of the extracted company information.
    """
    ext = tldextract.extract(url)
    if ext.domain in ['facebook', 'twitter', 'instagram', 'tiktok', 'youtube']:
        return f"Skipped generic social media URL: {url}"

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
1. When the user gives you a request, first call `optimize_search_query`.
2. Take the optimized query and call `search_web`.
3. Look at the search results. Identify the best matching links (e.g., official company websites, LinkedIn jobs, Indeed links). Ignore generic irrelevant links.
4. Call `scrape_and_extract` on the 3-5 most promising URLs. You can call this tool multiple times in parallel for different URLs.
5. Finally, summarize all your findings and the companies you successfully processed in a clear, concise markdown report for the user. Mention the emails and jobs found. Do not invent data.
"""

agent = create_react_agent(llm, tools, prompt=system_prompt)
