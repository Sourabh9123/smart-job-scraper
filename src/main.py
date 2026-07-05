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
    
    query = Prompt.ask("\n[bold yellow]Enter your request (e.g., 'Find me Python development companies in Bangalore actively hiring')[/bold yellow]")
    
    if not query:
        console.print("[red]Query cannot be empty. Exiting.[/red]")
        sys.exit(1)
        
    console.print(f"\n[bold green]Dispatching AI Agent for:[/bold green] {query}\n")
    
    inputs = {"messages": [HumanMessage(content=query)]}
    
    try:
        # Stream the agent's actions
        async for event in agent.astream(inputs, stream_mode="values"):
            message = event["messages"][-1]
            if message.type == "ai":
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        console.print(f"[cyan]🤖 Agent decides to call tool: {tool_call['name']}[/cyan]")
                elif message.content:
                    console.print(f"\n[bold magenta]🤖 Agent Final Report:[/bold magenta]\n{message.content}")
            elif message.type == "tool":
                console.print(f"[green]✅ Tool {message.name} returned results.[/green]")
    except KeyboardInterrupt:
        console.print("\n[red]Process interrupted by user.[/red]")
        sys.exit(0)
        
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

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
