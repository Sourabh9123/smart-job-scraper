# Smart Job Scraper 🎯 (Agentic Edition)

A powerful, autonomous Python CLI application designed to automate the discovery and analysis of software companies and hiring trends. Powered by a **LangGraph** AI agent, it intelligently crafts Google Dork queries, searches the web, decides which target websites and job portals to scrape, and leverages OpenAI-compatible LLMs (like Gemini or GPT-4o) to extract structured hiring data, contact emails, and tech stacks.

## 🚀 Features

- **Autonomous Agentic Workflow**: Built with **LangGraph** and **LangChain**. The AI agent determines the optimal strategy to find companies based on your natural language prompt.
- **Smart Query Optimization**: The agent automatically converts your request into a highly optimized Google Dork query for the Serper API.
- **Dynamic Scraping Engine**: Asynchronously crawls corporate websites and seamlessly handles major job platforms (LinkedIn, Indeed, Naukri, Glassdoor). The agent filters out generic sites and selectively crawls the most promising URLs.
- **AI-Powered Data Extraction**: Utilizes LLMs with Structured Outputs (Pydantic) to accurately extract rich metadata including:
  - Tech stacks and tools
  - Open positions and job counts
  - Remote work policies
  - **Career & Contact Emails** (Perfect for outreach!)
- **Robust Storage & Raw Caching**: 
  - Upserts extracted structured data into a MongoDB `companies` collection.
  - Caches the complete HTML/Text in a `raw_scrapes` collection linked via `source_id`, enabling future re-processing without hitting the website again.
- **Beautiful CLI & Agent Streaming**: Features a stunning, interactive terminal UI using `Rich`. Watch the AI agent's "thought process" and tool calls stream live in your terminal!
- **Easy Export**: One-click export of all structured data and emails into a clean CSV format.

## 🛠️ Tech Stack

- **Language**: Python 3.12+
- **Agent Framework**: `langgraph`, `langchain-openai`, `langchain-core`
- **Network**: `httpx` (async HTTP client) & `bs4` (HTML parsing)
- **AI/Extraction**: `openai` (Python SDK) & `pydantic` (Data schemas)
- **Database**: `motor` (Async MongoDB driver)
- **UI**: `rich` (Terminal styling)
- **Deployment**: Docker & Docker Compose

## 📋 Setup & Installation

### 1. Clone the repository
```bash
git clone git@github.com:Sourabh9123/smart-job-scraper.git
cd smart-job-scraper
```

### 2. Install dependencies
Using a virtual environment is recommended:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the `.env.example` file to create your own `.env`:
```bash
cp .env.example .env
```
Fill in your API keys in the `.env` file:
- `OPENAI_API_KEY`: Your LLM API key (OpenAI or Gemini via OpenAI-compatible endpoints)
- `SERPER_API_KEY`: Your search API key from [Serper.dev](https://serper.dev/)

### 4. Database Setup
Ensure you have a MongoDB instance running locally. You can easily start one using the included Docker configuration:
```bash
docker-compose up -d mongodb
```

## 💻 Usage

Start the agentic CLI application:
```bash
python -m src.main
```
*Alternatively, if you're using Make: `make run`*

**Workflow:**
1. You will be prompted to enter a natural language search query (e.g., `"Find me Python development companies in Berlin actively hiring"`).
2. The LangGraph agent intercepts your prompt and formulates a strategy.
3. 🤖 **Tool Call (`optimize_search_query`)**: The agent generates an optimized Google Dork.
4. 🤖 **Tool Call (`search_web`)**: The agent fetches Google search results via Serper.
5. 🤖 **Tool Call (`scrape_and_extract`)**: The agent selectively crawls the identified websites and job platform profiles in parallel.
6. The LLM processes the scraped text to extract structured insights and contact emails, saving everything to MongoDB.
7. 🤖 **Final Report**: The agent streams a final Markdown summary directly to your terminal.
8. You are prompted to export all the detailed data currently in your DB to a CSV file.

### 💡 Example Prompts to Maximize Cold Email Leads

The AI generates 5 diverse search strategies based on your input. Try these to get the best results:

- **For High Volume:** 
  > *"Find me a massive list of software companies, IT services, and product startups in India that are actively hiring developers right now. Focus on extracting their contact emails."*
- **For Specific Tech Stacks:** 
  > *"Find me modern software companies and startups in Bangalore or remote that are currently hiring Python, Django, or FastAPI developers."*
- **For High-Quality Startups:** 
  > *"Find me Y-Combinator startups, early-stage SaaS companies, and AI product companies in India that are expanding their engineering teams."*



## 🐳 Docker Support

Run the entire application in a containerized environment:

```bash
# Build the Docker image
docker build -t hiring-radar .

# Run the container (Ensure MongoDB URI in .env points to host, e.g., mongodb://host.docker.internal:27017)
docker run --env-file .env -it hiring-radar
```

## 📝 License

This project is licensed under the MIT License.
