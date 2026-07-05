import asyncio
from openai import AsyncOpenAI
from langchain_core.tools import tool
from src.config import settings
from src.models import CompanyInfo
from rich.console import Console

console = Console()
# Initialize without passing api_key if we expect it from environment, but passing it explicitly is safer
client = AsyncOpenAI(api_key=settings.openai_api_key)

async def _extract_chunk(text_chunk: str, website: str) -> CompanyInfo | None:
    prompt = f"""
    You are an expert data extractor. Given the text extracted from various pages of a company's website ({website}), 
    extract the relevant hiring and company information to populate the required schema. 
    
    If you cannot find a specific piece of information, use an empty list for arrays, False for booleans, or null/empty string for strings as appropriate.
    
    Scraped Text:
    {text_chunk}
    """

    try:
        completion = await client.beta.chat.completions.parse(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output structured JSON data based on a provided schema."},
                {"role": "user", "content": prompt},
            ],
            response_format=CompanyInfo,
            temperature=0.0
        )
        
        return completion.choices[0].message.parsed
        
    except Exception as e:
        console.print(f"[bold red]Error calling OpenAI API for chunk of {website}: {e}[/bold red]")
        return None

def _merge_info(info1: CompanyInfo, info2: CompanyInfo) -> CompanyInfo:
    return CompanyInfo(
        company=info1.company or info2.company,
        website=info1.website or info2.website,
        description=info1.description or info2.description,
        locations=list(set(info1.locations + info2.locations)),
        tech_stack=list(set(info1.tech_stack + info2.tech_stack)),
        careers_url=info1.careers_url or info2.careers_url,
        jobs=list(set(info1.jobs + info2.jobs)),
        linkedin=info1.linkedin or info2.linkedin,
        hiring_locations=list(set(info1.hiring_locations + info2.hiring_locations)),
        hiring_technologies=list(set(info1.hiring_technologies + info2.hiring_technologies)),
        remote_mentioned=info1.remote_mentioned or info2.remote_mentioned,
        contact_emails=list(set(info1.contact_emails + info2.contact_emails))
    )

async def extract_company_info(text: str, website: str) -> CompanyInfo | None:
    """
    Uses OpenAI API to extract structured information from the scraped text.
    If the text is large, it splits it into chunks and processes them in parallel (up to 2 chunks).
    """
    if not text.strip():
        return None

    # Chunk the text to avoid context limits and process data iteratively/parallelly
    CHUNK_SIZE = 30000 
    
    # We'll take up to 2 chunks (60k chars total) to prevent massive token usage,
    # but give it "in two go" as requested.
    max_length = CHUNK_SIZE * 2
    text_to_process = text[:max_length]
    
    chunks = [text_to_process[i:i + CHUNK_SIZE] for i in range(0, len(text_to_process), CHUNK_SIZE)]
    
    tasks = [_extract_chunk(chunk, website) for chunk in chunks]
    results = await asyncio.gather(*tasks)
    
    valid_results = [res for res in results if res is not None]
    
    if not valid_results:
        return None
        
    final_info = valid_results[0]
    for additional_info in valid_results[1:]:
        final_info = _merge_info(final_info, additional_info)
        
    return final_info

_previously_generated_queries = set()

@tool
async def optimize_search_query(user_query: str) -> list[str]:
    """
    Uses OpenAI API to convert a user's natural language request into a highly optimized 
    Google Search query (Dork) to find company websites and job listings.
    """
    global _previously_generated_queries
    import random
    
    # Format the previous queries nicely if any exist
    previous_queries_str = "None"
    if _previously_generated_queries:
        previous_queries_str = "\n".join(f"- {q}" for q in list(_previously_generated_queries)[-20:]) # Only show last 20 to save tokens

    strategies = [
        "Focus exclusively on specific sub-industries (e.g. Fintech, Edtech, Medtech, AI, Web3).",
        "Do NOT use site:linkedin.com or major job boards. Use negative operators (-linkedin -indeed -glassdoor) and look for organic 'careers' pages.",
        "Focus on obscure or senior job titles (e.g. 'Lead Architect', 'Backend Artisan', 'Staff Engineer').",
        "Focus on highly specific exact-match technology combinations (e.g. 'FastAPI + Celery + Redis', 'Django REST Framework + PostgreSQL').",
        "Target startup accelerators or funding rounds (e.g. 'Y Combinator', 'Series A', 'Seed funded').",
        "Use advanced operators like `intitle:'careers'` or `inurl:'jobs'` combined with niche keywords.",
        "Focus on B2B, Enterprise software, or consulting agencies."
    ]
    random_strategy = random.choice(strategies)

    prompt = f"""
    You are a search query string generator optimized for the Serper.dev API. Your task is to output highly optimized Google Search queries (Dorks).

    User Request:
    "{user_query}"
    
    PREVIOUSLY GENERATED QUERIES (DO NOT USE THESE, AND DO NOT JUST SHUFFLE THE WORDS):
    {previous_queries_str}

    CRITICAL STRATEGY FOR THIS BATCH:
    >>> {random_strategy} <<<
    
    You are currently stuck generating the exact same queries by just shuffling words around. Google ignores word order, so this wastes searches!
    To break the loop, you MUST strictly apply the CRITICAL STRATEGY above to invent 1 COMPLETELY NOVEL Google search query.

    CRITICAL GEOGRAPHY RULE:
    - You MUST KEEP the exact same geographic location (city/region/country) requested by the user. 
    - If the user explicitly asks for "Kolkata" or "Sector V", your Google query MUST contain those exact locations! Do not change the city!

    You can use operators like `site:linkedin.com`, `site:indeed.com`, `site:naukri.com`, `site:wellfound.com`, or `site:glassdoor.com`. 

    You must follow these formatting rules to prevent Serper HTTP 400 Bad Request errors:
    1. OUTPUT ONLY ONE SEARCH QUERY AT A TIME as plain text. Do not use brackets [], commas, or lists.
    2. KEEP IT ON A SINGLE LINE. Absolute no line breaks, enters, or hidden (\\n) characters.
    3. NEVER USE PLUS SIGNS (+). Change "React + Node.js" to "React Node.js".
    4. Do NOT explain anything.
    5. Do NOT use markdown or surrounding quotes.
    
    GOOD Query Example: Kolkata Sector V tech startups React Node.js site:linkedin.com
    BAD Query Example: ["Kolkata startups React + Node \\n site:naukri.com"]
    """
    try:
        completion = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a search query string generator optimized for the Serper.dev API."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3
        )
        
        query_str = completion.choices[0].message.content.strip(' "\'[]\n')
        
        # Save them to the persistent global state
        _previously_generated_queries.add(query_str)
            
        return [query_str]
        
    except Exception as e:
        console.print(f"[bold red]Error optimizing search query: {e}[/bold red]")
        return [user_query]

async def pivot_search_query(current_query: str, original_query: str) -> str:
    """
    Mutates the core search request to expand the search net when the current angle is exhausted.
    """
    prompt = f"""
    You are an expert lead generation strategist.
    
    The user originally asked for: "{original_query}"
    The current active search strategy is: "{current_query}"
    
    We have exhausted this current strategy and are hitting database duplicates.
    You MUST completely rewrite the strategy to cast a wider net while still respecting the spirit of the original request.
    
    CRITICAL RULE:
    - You MUST KEEP the exact same geographic location (city/region/country) requested by the user. Do NOT change the location! If they asked for Kolkata, it must stay Kolkata.
    
    Ideas to pivot (while keeping location the same):
    - Shift to adjacent tech stacks (e.g. from React to Vue/Angular, Python to Go/Node).
    - Change the company archetype (e.g. from 'Startups' to 'Enterprise SaaS', 'Web3', or 'B2B Services').
    - Target a different niche or sub-industry (e.g. HealthTech, EdTech, Fintech).
    
    Return ONLY the new, natural language request. Do NOT include quotes, explanations, or search operators.
    Example output: Find enterprise health-tech companies in Pune hiring backend developers.
    """
    try:
        completion = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a creative strategist."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        new_query = completion.choices[0].message.content.strip('"\' ')
        return new_query
    except Exception as e:
        console.print(f"[bold red]Error pivoting query: {e}[/bold red]")
        return current_query
