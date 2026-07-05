# Hiring Radar AI 🎯

A powerful asynchronous Python CLI application designed to automate the discovery and analysis of software companies and hiring trends. It searches the web, intelligently scrapes target websites and job portals, and leverages OpenAI-compatible LLMs (like Gemini) to extract structured hiring data, contact emails, and tech stacks.

## 🚀 Features

- **Intelligent Discovery**: Uses the Serper API to find relevant companies based on custom search queries.
- **Smart Scraping Engine**: Asynchronously crawls corporate websites and seamlessly handles major job platforms (LinkedIn, Indeed, Naukri, Glassdoor) without breaking their specific URLs.
- **AI-Powered Data Extraction**: Utilizes LLMs with Structured Outputs (Pydantic) to accurately extract rich metadata including:
  - Tech stacks and tools
  - Open positions and job counts
  - Remote work policies
  - **Career & Contact Emails** (Perfect for outreach!)
- **Robust Storage**: Upserts extracted data into MongoDB to prevent duplicates and track crawl history.
- **Beautiful CLI**: Features a stunning, interactive terminal UI with live progress bars and formatted tables using `Rich`.
- **Easy Export**: One-click export of all structured data and emails into a clean CSV format.

## 🛠️ Tech Stack

- **Language**: Python 3.12+
- **Network**: `httpx` (async HTTP client) & `bs4` (HTML parsing)
- **AI/Extraction**: `openai` (Python SDK for LLM integration) & `pydantic` (Data schemas)
- **Database**: `motor` (Async MongoDB driver)
- **UI**: `rich` & `rich-cli` (Terminal styling)
- **Deployment**: Docker & Docker Compose

## 📋 Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/smart-job-scraper.git
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
- `OPENAI_API_KEY`: Your LLM API key (OpenAI or Gemini 3.1 Pro via OpenAI-compatible endpoints)
- `SERPER_API_KEY`: Your search API key from [Serper.dev](https://serper.dev/)

### 4. Database Setup
Ensure you have a MongoDB instance running locally. You can easily start one using the included Docker configuration:
```bash
docker-compose up -d mongodb
```

## 💻 Usage

Start the CLI application:
```bash
python -m src.main
```
*Alternatively, if you're using Make: `make run`*

**Workflow:**
1. You will be prompted to enter a search query (e.g., `"Python development companies in Berlin hiring"`).
2. The tool fetches Google search results via Serper.
3. It concurrently crawls the identified websites and job platform profiles.
4. The LLM processes the scraped text to extract structured insights and contact emails.
5. Results are securely saved to MongoDB.
6. A summary table is presented in the terminal.
7. You are prompted to export the detailed data to a CSV file.

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
