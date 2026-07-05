import asyncio
from openai import AsyncOpenAI
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
