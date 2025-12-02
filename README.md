# 📊 Analyst-9000

> A conversational AI agent powered by **LangGraph** that processes e-commerce data and derives meaningful business insights using natural language.

---

## 📁 Project Structure

```
analyst-9000/
├── src/
│   └── analyst_9000/
│       ├── main.py                     # Application entry point
│       ├── frontend/
│       │   └── index.html              # Static chatbot UI
│       └── backend/
│           ├── ai_core/
│           │   ├── graph/
│           │   │   ├── graph.py        # LangGraph definition
│           │   │   ├── nodes.py        # Graph nodes (router, QA, SQL, etc.)
│           │   │   ├── states.py       # Agent state schema
│           │   │   └── tools.py        # BigQuery tool
│           │   ├── llm/
│           │   │   ├── registry.py     # Model registry (configurable models)
│           │   │   ├── callbacks.py    # Custom LLM callbacks for monitoring
│           │   │   └── llm_utils.py    # Reasoning budget utilities
│           │   └── prompts/
│           │       ├── router.py       # Intent classification prompt
│           │       ├── qa_model.py     # General QA assistant prompt
│           │       ├── sql_generator.py # SQL generation prompt
│           │       └── response_synthesizer.py # Data-to-insight prompt
│           ├── core/
│           │   ├── config.py           # Application settings
│           │   ├── constants.py        # Configuration constants
│           │   ├── logger.py           # Structured JSON logging + webhook
│           │   ├── bigquery_handler.py # BigQuery client & schema extraction
│           │   ├── session_store.py    # Async session store (PostgreSQL/SQLite)
│           │   └── setup.py            # Logging initialization
│           ├── routers/
│           │   ├── chatbot.py          # Chat API endpoints
│           │   └── health.py           # Health check endpoint
│           ├── services/
│           │   ├── app_startup/        # FastAPI lifespan & configuration
│           │   ├── chatbot/            # Chat completion orchestration
│           │   └── chat_history/       # Conversation persistence
│           ├── schemas/
│           │   ├── api_schemas.py      # API request/response models
│           │   ├── db_schemas.py       # Database models
│           │   └── llm_output.py       # Structured LLM outputs
│           ├── helpers/
│           │   ├── utils.py            # Utility functions
│           │   └── sql_queries/        # SQL templates
│           ├── middleware/
│           │   └── middleware.py       # Correlation ID middleware
│           └── exceptions/
│               └── api_exceptions.py   # Custom exception handlers
├── secrets/
│   └── credentials.json                # GCP service account (you create this)
├── data/
│   └── analyst_9000.db                 # SQLite database (auto-created)
├── docker-compose.yml                  # Docker deployment
├── Dockerfile
├── pyproject.toml
├── .env                                # Environment variables (you create this)
└── .env_example                        # Template for .env
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.13+**
- **Google Cloud Platform** account with BigQuery access
- **Gemini API key** from [Google AI Studio](https://aistudio.google.com)

---

### Step 1: Create Environment File

Create a `.env` file in the project root with at least your Gemini API key:

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here
```

> 💡 Get your API key from [Google AI Studio](https://aistudio.google.com)

---

### Step 2: Set Up BigQuery Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a **Service Account** with the following roles:
   - `BigQuery Job User`
   - `BigQuery Read Session User`
3. Generate a **JSON key** for the service account
4. Rename the file to `credentials.json`
5. Place it in the `secrets/` folder

```
secrets/
└── credentials.json   # Your GCP service account key
```

---

### Step 3 (Optional): Configure Monitoring

Add these to your `.env` file for enhanced observability:

```bash
# Webhook for error notifications (e.g., Slack, Discord, webhook.site)
WEBHOOK_URI="https://webhook.site/your-webhook-id"

# LangSmith tracing for LLM monitoring
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=your-project-name
```

---

## 🖥️ Deployment Options

### Option 1: Local Development

1. **Install [uv](https://docs.astral.sh/uv/)** (Python package manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Activate the virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

4. **Run the application**:
   ```bash
   analy
   ```

5. **Access the chatbot**: Open [http://localhost:6757](http://localhost:6757)

> 📝 Local development uses **SQLite** for session storage automatically.

---

### Option 2: Docker Deployment

1. **Build and run with Docker Compose**:
   ```bash
   docker compose up --build
   ```

2. **Access the chatbot**: Open [http://localhost:6757](http://localhost:6757)

> 📝 Docker deployment uses **PostgreSQL** for session storage.

**To stop**:
```bash
docker compose down
```

**To reset data** (including PostgreSQL):
```bash
docker compose down -v
```

---

## 💬 Using the Chatbot

Once running, you'll find a modern chatbot interface where you can:

- **Select Model**: Choose between `Flash` (fast) or `Pro` (more capable)
- **Adjust Temperature**: Control response creativity (0.0 = deterministic, 1.0 = creative)
- **Set Reasoning Effort**: `Low`, `Medium`, or `High` thinking budget

### This isn't just a query agent—it's a full chatbot with memory!

You can have natural conversations, ask follow-up questions, and the agent remembers context within a session.

---

## 📊 Example Queries

Try these queries to explore your e-commerce data:

```
Show me the top 5 best-selling products (by total revenue) over the last 12 months.
```

```
What were the top 3 product categories by revenue in the last quarter?
```

```
Which products have the highest profit margins?
```

```
What is the average order value for repeat customers versus new customers?
```

```
Show me the historical sales trends for the past year.
```

```
Which product categories have the highest profit margin, and which are underperforming?
```

```
Segment customers into 3–4 groups based on their total lifetime spend and number of orders, 
and summarise each segment (size, % of revenue, average order value).
```

---

## 🔧 Configuration

Key settings in `src/analyst_9000/backend/core/constants.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `LOCAL_DEV_PORT` | `6757` | Development server port |
| `MAX_ITERATIONS` | `3` | Max SQL retry attempts |
| `MAX_HISTORY_MESSAGES` | `30` | Messages kept in context |
| `DB_POOL_SIZE` | `5` | Connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Max overflow connections |

---
