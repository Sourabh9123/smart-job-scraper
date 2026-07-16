# Smart Job Scraper (Agentic Edition) - Memory Context

## Project Overview
This project is an autonomous Python CLI application designed to discover software companies and extract hiring data, tech stacks, and contact emails. It leverages a LangGraph-powered AI agent to formulate search strategies, execute web searches (via Serper API), and scrape websites asynchronously.

## Architecture & Core Modules
- **`src/main.py`**: The main entry point. Provides a stunning CLI UI using `rich`. Offers two operational modes:
  1. **Standard Discovery**: Driven by LLM Agent -> Google Search -> Scrape.
  2. **OSM Pipeline**: Uses OpenStreetMap to find businesses in a location -> Database -> Google Search -> Scrape.
- **`src/agent.py`**: Defines the `create_react_agent` with tools:
  - `optimize_search_query`: Generates diverse Google Dorks.
  - `search_web`: Searches Serper API and resolves job board links to official company domains.
  - `scrape_and_extract`: Triggers scraping and LLM data extraction.
- **`src/scraper.py`**: A robust async scraper using `httpx` and `BeautifulSoup`. Features a large pool of rotating User-Agents (Windows/Mac/Linux, Chrome/Firefox/Safari/Edge/Mobile) and automatically attempts to scrape standard paths (`/`, `/careers`, `/jobs`, `/about`, etc.).
- **`src/llm.py`**: Manages LLM interactions for structured data extraction using Pydantic schemas, query optimization, and automatic search pivoting.
- **`src/db.py`**: Manages async MongoDB interactions using `motor`. Handles saving extracted structured data (`CompanyDocument`) and caches raw scraped HTML to avoid re-fetching.
- **`src/osm.py`**: Handles querying OpenStreetMap via Overpass API for location-based business discovery.

## Tech Stack
- **Language**: Python 3.12+
- **Agent Framework**: `langgraph`, `langchain-openai`, `langchain-core`
- **Network/Scraping**: `httpx`, `bs4`, `tldextract`
- **AI**: `openai` (Structured Outputs), `pydantic`
- **Database**: `motor` (MongoDB)
- **UI**: `rich`

## Key Mechanisms
- **Agentic Loop**: The agent operates in batches. It evaluates search results, selectively scrapes domains not already in the DB, and auto-pivots the search strategy every 5 batches to avoid staleness.
- **Job Board Resolution**: If the search returns a job board (LinkedIn, Indeed, etc.), the agent tries to extract the company name and runs a sub-search to find the official company website instead of scraping the heavily protected job board.
- **Duplicate Prevention**: The system checks MongoDB for existing domains before initiating any scraping.
- **Raw Caching**: The complete text of scraped websites is saved in a `raw_scrapes` collection, allowing re-extraction without hitting the website again.
