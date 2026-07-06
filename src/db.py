from motor.motor_asyncio import AsyncIOMotorClient
from src.config import settings
from src.models import CompanyDocument
from rich.console import Console
from datetime import datetime, timezone
from bson import ObjectId
import tldextract

console = Console()

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(settings.mongodb_uri)
        self.db = self.client[settings.mongodb_db_name]
        self.collection = self.db.companies
        self.raw_collection = self.db.raw_scrapes
        self.osm_collection = self.db.osm_companies

    async def init_db(self):
        # Create a unique index on the domain
        await self.collection.create_index("domain", unique=True)
        # Create unique index on osm_id to prevent duplicates
        await self.osm_collection.create_index("osm_id", unique=True)

    @staticmethod
    def get_domain(url: str) -> str:
        ext = tldextract.extract(url)
        return f"{ext.domain}.{ext.suffix}"

    async def save_company(self, company: CompanyDocument) -> bool:
        """
        Saves or updates a company document. Returns True if inserted/updated, False on error.
        Uses the website domain as the unique identifier to avoid duplicates.
        """
        if self.collection is None:
            return False
        domain = self.get_domain(company.website)
        doc = company.model_dump()
        doc['domain'] = domain
        doc['last_crawled'] = datetime.now(timezone.utc)
        
        if doc.get('source_id'):
            doc['source_id'] = ObjectId(doc['source_id'])
            
        try:
            await self.collection.update_one(
                {"domain": domain},
                {"$set": doc},
                upsert=True
            )
            console.print(f"[bold green]💾 Successfully saved {company.company or domain} to database![/bold green]")
            return True
        except Exception as e:
            console.print(f"[bold red]Database error for {company.company}: {e}[/bold red]")
            return False

    async def save_osm_company(self, osm_company) -> bool:
        """Saves a company found via OSM to the database."""
        if self.osm_collection is None:
            return False
        doc = osm_company.model_dump()
        try:
            await self.osm_collection.update_one(
                {"osm_id": doc["osm_id"]},
                {"$set": doc},
                upsert=True
            )
            return True
        except Exception:
            return False

    async def get_unprocessed_osm_companies(self, limit: int = 5):
        """Gets companies from OSM that haven't been scraped yet."""
        if self.osm_collection is None:
            return []
        cursor = self.osm_collection.find({"processed": False}).limit(limit)
        return await cursor.to_list(length=limit)
        
    async def mark_osm_processed(self, osm_id: int):
        if self.osm_collection is not None:
            await self.osm_collection.update_one({"osm_id": osm_id}, {"$set": {"processed": True}})

    async def domain_exists(self, domain: str) -> bool:
        """Checks if a domain already exists in the main companies collection."""
        if self.collection is None:
            return False
        count = await self.collection.count_documents({"domain": domain}, limit=1)
        return count > 0

    async def save_raw_scrape(self, website: str, raw_text: str) -> str | None:
        """
        Saves raw scraped text and returns the inserted document ID as a string.
        """
        doc = {
            "website": website,
            "raw_text": raw_text,
            "scraped_at": datetime.now(timezone.utc)
        }
        try:
            result = await self.raw_collection.insert_one(doc)
            return str(result.inserted_id)
        except Exception as e:
            console.print(f"[bold red]Database error saving raw scrape for {website}: {e}[/bold red]")
            return None

db = Database()
