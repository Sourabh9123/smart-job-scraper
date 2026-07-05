import csv
from typing import List
from src.models import CompanyDocument
from rich.console import Console

console = Console()

def export_to_csv(data: List[CompanyDocument], filename: str = "export.csv"):
    if not data:
        console.print("[yellow]No data to export.[/yellow]")
        return
        
    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            # Get headers from the first Pydantic model
            headers = list(data[0].model_dump().keys())
            writer = csv.DictWriter(file, fieldnames=headers)
            
            writer.writeheader()
            for item in data:
                # Convert complex types to strings for CSV
                row = item.model_dump()
                row['locations'] = ", ".join(row.get('locations', []))
                row['tech_stack'] = ", ".join(row.get('tech_stack', []))
                row['jobs'] = ", ".join(row.get('jobs', []))
                row['hiring_locations'] = ", ".join(row.get('hiring_locations', []))
                row['hiring_technologies'] = ", ".join(row.get('hiring_technologies', []))
                row['contact_emails'] = ", ".join(row.get('contact_emails', []))
                row['last_crawled'] = row['last_crawled'].isoformat()
                writer.writerow(row)
        console.print(f"[bold green]Successfully exported data to {filename}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Failed to export CSV: {e}[/bold red]")
