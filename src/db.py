from motor.motor_asyncio import AsyncIOMotorClient
from src.config import settings
from src.models import CompanyDocument
from rich.console import Console
from datetime import datetime, timezone
import tldextract

console = Console()

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(settings.mongodb_uri)
        self.db = self.client[settings.mongodb_db_name]
        self.collection = self.db.companies

    async def init_db(self):
        # Create a unique index on the domain
        await self.collection.create_index("domain", unique=True)

    @staticmethod
    def get_domain(url: str) -> str:
        ext = tldextract.extract(url)
        return f"{ext.domain}.{ext.suffix}"

    async def save_company(self, company: CompanyDocument) -> bool:
        """
        Saves or updates a company document. Returns True if inserted/updated, False on error.
        Uses the website domain as the unique identifier to avoid duplicates.
        """
        domain = self.get_domain(company.website)
        doc = company.model_dump()
        doc['domain'] = domain
        doc['last_crawled'] = datetime.now(timezone.utc)
        
        try:
            await self.collection.update_one(
                {"domain": domain},
                {"$set": doc},
                upsert=True
            )
            return True
        except Exception as e:
            console.print(f"[bold red]Database error for {company.company}: {e}[/bold red]")
            return False

db = Database()
