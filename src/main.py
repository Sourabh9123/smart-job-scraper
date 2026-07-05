import asyncio
import sys
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt
from urllib.parse import urlparse
import tldextract

from src.db import db
from src.search import search_companies
from src.scraper import scraper
from src.llm import extract_company_info
from src.models import CompanyDocument
from src.utils import export_to_csv

console = Console()

def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

async def process_company(result: dict, query: str, progress: Progress, task_id) -> CompanyDocument | None:
    website = result.get('link')
    name = result.get('title')
    
    if not website or not is_valid_url(website):
        progress.update(task_id, advance=1)
        return None
        
    ext = tldextract.extract(website)
    # Skip only generic social media that are unlikely to yield good extraction results directly
    if ext.domain in ['facebook', 'twitter', 'instagram', 'tiktok']:
        progress.update(task_id, advance=1)
        return None

    # We use rich console updates via progress
    progress.update(task_id, description=f"[cyan]Scraping {ext.domain}...[/cyan]")
    
    # Scrape
    scraped_text = await scraper.crawl_company(website)
    
    if not scraped_text:
        progress.update(task_id, advance=1)
        return None
        
    progress.update(task_id, description=f"[magenta]Analyzing {ext.domain}...[/magenta]")
    
    # Extract via LLM
    company_info = await extract_company_info(scraped_text, website)
    
    if not company_info:
        progress.update(task_id, advance=1)
        return None
        
    # Build Document
    doc = CompanyDocument(
        **company_info.model_dump(),
        search_query=query
    )
    
    # Save to DB
    await db.save_company(doc)
    
    progress.update(task_id, advance=1)
    return doc

async def main():
    console.rule("[bold blue]Software Company Discovery & Hiring Info Extractor[/bold blue]")
    
    # Initialize DB
    await db.init_db()
    
    query = Prompt.ask("\n[bold yellow]Enter your search query (e.g., 'Python development companies Bangalore')[/bold yellow]")
    
    if not query:
        console.print("[red]Query cannot be empty. Exiting.[/red]")
        sys.exit(1)
        
    console.print(f"\n[bold green]Searching for:[/bold green] {query}\n")
    
    with console.status("[bold cyan]Searching via Serper API...[/bold cyan]"):
        results = await search_companies(query)
        
    if not results:
        console.print("[yellow]No results found or error occurred during search.[/yellow]")
        sys.exit(0)
        
    console.print(f"[green]Found {len(results)} potential results.[/green]\n")
    
    successful_docs = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Processing companies...", total=len(results))
        
        # Concurrently process with semaphore to prevent rate limiting / overloading
        sem = asyncio.Semaphore(5)
        
        async def bounded_process(r):
            async with sem:
                return await process_company(r, query, progress, task)
                
        tasks = [bounded_process(r) for r in results]
        docs = await asyncio.gather(*tasks)
        successful_docs = [d for d in docs if d is not None]

    console.print("\n[bold green]Processing Complete![/bold green]\n")
    
    if not successful_docs:
        console.print("[yellow]No company information could be successfully extracted.[/yellow]")
        sys.exit(0)
        
    # Display Results in a Table
    table = Table(title=f"Results for '{query}'", show_lines=True)
    table.add_column("Company", style="cyan", no_wrap=True)
    table.add_column("Website", style="blue")
    table.add_column("Emails", style="green")
    table.add_column("Jobs Listed", style="green")
    table.add_column("Remote?", style="magenta")
    table.add_column("Tech Stack", style="yellow")
    
    for doc in successful_docs:
        jobs_count = len(doc.jobs)
        remote = "Yes" if doc.remote_mentioned else "No"
        tech = ", ".join(doc.tech_stack[:3]) + ("..." if len(doc.tech_stack) > 3 else "")
        emails = ", ".join(doc.contact_emails[:2]) + ("..." if len(doc.contact_emails) > 2 else "") if doc.contact_emails else "None"
        table.add_row(
            doc.company, 
            doc.website, 
            emails,
            str(jobs_count), 
            remote,
            tech
        )
        
    console.print(table)
    
    # Export Option
    export = Prompt.ask("\n[bold yellow]Do you want to export results to CSV?[/bold yellow]", choices=["y", "n"], default="y")
    if export.lower() == "y":
        filename = Prompt.ask("[bold yellow]Enter filename[/bold yellow]", default="companies_export.csv")
        export_to_csv(successful_docs, filename)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[red]Process interrupted by user.[/red]")
        sys.exit(0)
