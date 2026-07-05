import asyncio
import sys
from rich.console import Console
from rich.prompt import Prompt
from src.db import db
from src.agent import agent
from langchain_core.messages import HumanMessage
from src.utils import export_to_csv
from src.models import CompanyDocument

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
                console.rule(f"[bold cyan]Batch {iteration}[/bold cyan]")
                
                # Force the agent to try new angles each iteration
                agent_input = f"Find companies for this request: '{query}'. This is batch {iteration}. Generate 5 COMPLETELY NEW AND DIFFERENT search queries that you haven't tried yet. Focus on different sub-niches, different cities, or different keywords to find fresh companies. Then search and immediately scrape up to 5 best official company websites. If no new companies are found or if they are already in the DB, STOP immediately and output your report. Do not loop back to search again."
                
                inputs = {"messages": [HumanMessage(content=agent_input)]}
                
                # Stream the agent's actions
                async for event in agent.astream(inputs, stream_mode="values"):
                    message = event["messages"][-1]
                    if message.type == "ai":
                        if message.tool_calls:
                            for tool_call in message.tool_calls:
                                console.print(f"[cyan]🤖 Agent decides to call tool: {tool_call['name']}[/cyan]")
                        elif message.content:
                            console.print(f"\n[bold magenta]🤖 Agent Final Report for Batch {iteration}:[/bold magenta]\n{message.content}")
                    elif message.type == "tool":
                        console.print(f"[green]✅ Tool {message.name} returned results.[/green]")
                        
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
