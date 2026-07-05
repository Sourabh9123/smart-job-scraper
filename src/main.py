import asyncio
import sys
from rich.console import Console
from rich.prompt import Prompt
from src.db import db
from src.agent import agent
from langchain_core.messages import HumanMessage
from src.utils import export_to_csv
from src.models import CompanyDocument
from src.config import settings

console = Console()

async def main():
    console.rule("[bold blue]Agentic Software Company Discovery[/bold blue]")
    
    # Initialize DB
    await db.init_db()
    
    while True:
        query = Prompt.ask("\n[bold yellow]Enter your request (or type 'exit'/'quit' to stop)[/bold yellow]")
        
        if not query or query.lower() in ['exit', 'quit']:
            break
            
        console.print(f"\n[bold green]Dispatching AI Agent for:[/bold green] {query}\n")
        console.print("[dim]The agent will run continuously in batches. Press Ctrl+C at any time to stop and export.[/dim]\n")
        
        iteration = 1
        try:
            while True:
                from src.llm import optimize_search_query
                from src.agent import search_web, scrape_and_extract
                import re
                
                # Step 1: Optimize Search Queries
                console.print(f"[cyan]🤖 Agent is generating highly optimized search queries...[/cyan]")
                queries = await optimize_search_query.ainvoke({"user_query": query})
                
                # Step 2: Search the Web
                console.print(f"[cyan]🤖 Agent is searching the web with queries: {queries}[/cyan]")
                search_results = await search_web.ainvoke({"queries": queries})
                
                if "CRITICAL INSTRUCTION" in search_results or "No new companies found" in search_results:
                    console.print(f"\n[bold magenta]🤖 Agent Final Report for Batch {iteration}:[/bold magenta]\nNo new companies were found in this batch (all were duplicates).")
                else:
                    # Parse URLs from the search results
                    links = re.findall(r"Link: (https?://[^\s]+)", search_results)
                    unique_links = list(dict.fromkeys(links))[:settings.batch_size]
                    
                    if not unique_links:
                        console.print(f"\n[bold magenta]🤖 Agent Final Report for Batch {iteration}:[/bold magenta]\nCould not extract any valid URLs to scrape.")
                    else:
                        # Step 3: Scrape and Extract
                        console.print(f"[cyan]🤖 Agent is scraping and extracting data from {len(unique_links)} companies...[/cyan]")
                        scrape_tasks = [
                            scrape_and_extract.ainvoke({"url": link, "user_context": query})
                            for link in unique_links
                        ]
                        scrape_results = await asyncio.gather(*scrape_tasks)
                        
                        report = "\n".join(scrape_results)
                        console.print(f"\n[bold magenta]🤖 Agent Final Report for Batch {iteration}:[/bold magenta]\n{report}")
                        
                iteration += 1
                console.print(f"\n[dim]Batch {iteration-1} complete. Automatically starting next batch...[/dim]\n")
                await asyncio.sleep(2) # Brief pause between batches
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Continuous search interrupted. All data up to this point is securely saved in the database.[/yellow]")
            
    export = Prompt.ask("\n[bold yellow]Do you want to export all scraped companies in the DB to CSV?[/bold yellow]", choices=["y", "n"], default="y")
    if export.lower() == "y":
        filename = Prompt.ask("[bold yellow]Enter filename[/bold yellow]", default="companies_export.csv")
        # Fetch all documents from the DB for export
        cursor = db.collection.find({})
        docs = []
        async for doc in cursor:
            # We can convert back to CompanyDocument for the CSV exporter
            doc.pop('_id', None)
            if doc.get('source_id'):
                doc['source_id'] = str(doc['source_id'])
            docs.append(CompanyDocument(**doc))
        export_to_csv(docs, filename)
        console.print(f"[green]Successfully exported {len(docs)} companies to {filename}![/green]")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
