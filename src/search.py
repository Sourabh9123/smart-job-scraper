import httpx
import asyncio
from typing import List, Dict, Any
from src.config import settings
from rich.console import Console

console = Console()

_serper_semaphore = None

async def search_companies(query: str) -> List[Dict[str, Any]]:
    """
    Use Serper API to search for companies based on the query.
    Returns a list of search results.
    """
    global _serper_semaphore
    if _serper_semaphore is None:
        _serper_semaphore = asyncio.Semaphore(4)
        
    async with _serper_semaphore:
        await asyncio.sleep(0.25) # Ensure we stay under 5 requests per second
        url = "https://google.serper.dev/search"
    payload = {
        "q": query
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
    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]HTTP Error calling Serper API: {e}[/bold red]")
        console.print(f"[bold red]Response Details: {e.response.text}[/bold red]")
        return []
    except Exception as e:
        console.print(f"[bold red]Error calling Serper API: {e}[/bold red]")
        return []
