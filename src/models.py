from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime, timezone

class SearchQueryOptimization(BaseModel):
    optimized_query: str = Field(description="The optimized Google search query string designed to find companies hiring")


class CompanyInfo(BaseModel):
    company: str = Field(description="Name of the company")
    website: str = Field(description="Official website URL")
    description: str = Field(description="Brief description of what the company does")
    locations: List[str] = Field(description="Office locations mentioned", default_factory=list)
    tech_stack: List[str] = Field(description="Technologies the company uses or builds with", default_factory=list)
    careers_url: Optional[str] = Field(description="URL to the careers/jobs page", default=None)
    jobs: List[str] = Field(description="List of open positions or roles", default_factory=list)
    linkedin: Optional[str] = Field(description="LinkedIn URL of the company", default=None)
    hiring_locations: List[str] = Field(description="Locations where they are hiring", default_factory=list)
    hiring_technologies: List[str] = Field(description="Technologies mentioned in job postings", default_factory=list)
    remote_mentioned: bool = Field(description="Whether remote work is mentioned", default=False)
    contact_emails: List[str] = Field(description="Contact or career emails found", default_factory=list)

class CompanyDocument(CompanyInfo):
    last_crawled: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    search_query: str
    source_id: Optional[str] = Field(description="ID of the raw scrape document", default=None)
