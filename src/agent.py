import asyncio
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
    
    # We will use another asyncio loop to find official domains for job board links
    company_name_resolution_tasks = []
    
    for results in all_results:
        for r in results:
            link = r.get('link')
            title = r.get('title')
            if not link or not title:
                continue
                
            ext = tldextract.extract(link)
            domain = f"{ext.domain}.{ext.suffix}"
            
            # Job Board Bypass Strategy
            if ext.domain in ['linkedin', 'indeed', 'naukri', 'glassdoor', 'wellfound']:
                # Extract potential company name from the title
                parts = title.replace('|', '-').split('-')
                if len(parts) > 1:
                    company_name = parts[-2].strip() if len(parts) >= 2 else parts[0].strip()
                    company_name = company_name.replace('Jobs', '').strip()
                    if company_name and len(company_name) > 2:
                        company_name_resolution_tasks.append((company_name, f"{company_name} official company website"))
            else:
                # Official website
                if domain not in unique_domains:
                    unique_domains.add(domain)
                    aggregated_output.append({"title": title, "link": link, "domain": domain})
                    
    # Resolve job board company names to official domains concurrently
    if company_name_resolution_tasks:
        # Limit to 20 resolutions per run to keep things fast and avoid giant batches
        company_name_resolution_tasks = company_name_resolution_tasks[:20]
        
        console.print(f"[cyan]Action:[/cyan] Resolving {len(company_name_resolution_tasks)} companies from job boards to their official websites...")
        
        # Create the coroutines AFTER slicing so we don't leave any unawaited coroutines
        resolution_results = await asyncio.gather(*[search_companies(query) for _, query in company_name_resolution_tasks])
        for (company_name, _), results in zip(company_name_resolution_tasks, resolution_results):
            if results:
                # Take the first organic result as the official website
                best_result = results[0]
                link = best_result.get('link')
                if link:
                    ext = tldextract.extract(link)
                    if ext.domain not in ['linkedin', 'indeed', 'glassdoor', 'naukri', 'wellfound']:
                        domain = f"{ext.domain}.{ext.suffix}"
                        if domain not in unique_domains:
                            unique_domains.add(domain)
                            aggregated_output.append({"title": f"{company_name} (Resolved from Job Board)", "link": link, "domain": domain})

    # Filter out companies that are ALREADY in the database to save scraping time
    final_output = []
    console.print(f"[cyan]Action:[/cyan] Checking {len(aggregated_output)} domains against the database...")
    for item in aggregated_output:
        domain = item['domain']
        is_existing = await db.domain_exists(domain)
        if not is_existing:
            final_output.append(f"Title: {item['title']}\nLink: {item['link']}")
        else:
            console.print(f"[dim]Skipping {domain} (already in DB)[/dim]")
    
    if not final_output:
        return "CRITICAL INSTRUCTION: No new companies found. All discovered companies are already in the database. YOU MUST STOP NOW and output your final report. DO NOT CALL ANY MORE TOOLS."
        
    return "\n\n".join(final_output)

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
You must strictly follow this exact sequence of steps. Do NOT deviate. Do NOT loop.

STEP 1: Call `optimize_search_query` EXACTLY ONCE to generate 5 diverse search queries.
STEP 2: Call `search_web` EXACTLY ONCE with the list of optimized queries.
STEP 3: Evaluate the results from `search_web`. 
  - If it says no new companies were found, STOP IMMEDIATELY and output your final report.
  - Otherwise, select up to {settings.batch_size} of the best official company URLs.
STEP 4: Call `scrape_and_extract` on the selected URLs. YOU MUST DO THIS. Do NOT skip this step. Do NOT go back to Step 1 or Step 2.
STEP 5: Output your final Markdown report summarizing the successfully scraped companies. STOP.

CRITICAL RULES:
- NEVER call `optimize_search_query` more than once per batch.
- NEVER call `search_web` more than once per batch.
- If you have search results, your ONLY allowed next action is `scrape_and_extract` or finalizing the report.
"""

agent = create_react_agent(llm, tools, prompt=system_prompt)
