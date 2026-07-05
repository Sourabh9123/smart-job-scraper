import httpx
from typing import List, Dict, Any
from src.config import settings
from rich.console import Console

console = Console()

async def search_companies(query: str) -> List[Dict[str, Any]]:
    """
    Use Serper API to search for companies based on the query.
    Returns a list of search results.
    """
    url = "https://google.serper.dev/search"
    payload = {
        "q": query,
        "num": 20 # Fetching enough results
    }
    headers = {
        'X-API-KEY': settings.serper_api_key,
        'Content-Type': 'application/json'
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            # Extract organic results
            return data.get("organic", [])
    except Exception as e:
        console.print(f"[bold red]Error calling Serper API: {e}[/bold red]")
        return []
