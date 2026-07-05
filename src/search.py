import httpx
import asyncio
from typing import List, Dict, Any
from src.config import settings
from rich.console import Console

import time

import time

console = Console()

_rate_limit_lock = asyncio.Lock()
_last_request_time = 0.0
_serper_keys = [k.strip() for k in settings.serper_api_key.split(',') if k.strip()]
_current_key_idx = 0

async def search_companies(query: str) -> List[Dict[str, Any]]:
    """
    Use Serper API to search for companies based on the query.
    Returns a list of search results.
    """
    global _last_request_time, _current_key_idx
    
    for attempt in range(3):
        async with _rate_limit_lock:
            now = time.time()
            elapsed = now - _last_request_time
            delay = 0.5 / len(_serper_keys) # Slower, safer delay
            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)
            _last_request_time = time.time()
            
            api_key = _serper_keys[_current_key_idx]
            _current_key_idx = (_current_key_idx + 1) % len(_serper_keys)
            
        url = "https://google.serper.dev/search"
        payload = {"q": query}
        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=15.0)
                if response.status_code == 429:
                    console.print(f"[yellow]Rate limit hit. Retrying in 2 seconds...[/yellow]")
                    await asyncio.sleep(2)
                    continue
                response.raise_for_status()
                data = response.json()
                return data.get("organic", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                console.print(f"[yellow]Rate limit hit via exception. Retrying in 2 seconds...[/yellow]")
                await asyncio.sleep(2)
                continue
            console.print(f"[bold red]HTTP Error calling Serper API: {e}[/bold red]")
            return []
        except httpx.RequestError as e:
            console.print(f"[yellow]Network timeout or error: {e}. Retrying...[/yellow]")
            await asyncio.sleep(2)
            continue
        except Exception as e:
            console.print(f"[bold red]Error calling Serper API: {e}[/bold red]")
            return []
            
    return []
