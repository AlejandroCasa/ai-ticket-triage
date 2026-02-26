# 🛡️ AI-Driven ITSM Triage Engine

> An Enterprise-grade, asynchronous microservice for automated IT ticket classification. Powered by Large Language Models (LLMs), Semantic Caching (FinOps), and Retrieval-Augmented Generation (RAG).

![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Docker Compose](https://img.shields.io/badge/Docker_Compose-2496ED?style=for-the-badge&logo=docker)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Cache-FF4D4D?style=for-the-badge)
![Architecture](https://img.shields.io/badge/Architecture-Event_Driven-orange?style=for-the-badge)

## 📋 Executive Summary

This project demonstrates a production-grade approach to applying Generative AI in DevOps/IT Operations. It moves beyond simple API wrappers into a resilient, FinOps-optimized architecture capable of:
1.  **Asynchronous Ingestion:** Accepting high-volume ticket bursts without blocking the main thread.
2.  **Semantic Caching:** Slashing LLM API costs by up to 90% by mathematically identifying and resolving recurring issues locally.
3.  **Human-in-the-Loop (RAG):** Learning dynamically from human corrections without requiring expensive model retraining.

---

## 🏗️ Architecture

The system utilizes an Event-Driven API Gateway pattern paired with a local Vector Database for semantic memory.

```mermaid
graph TD
    User((Ops Team / Webhook)) -->|POST /classify| API[FastAPI Gateway]
    API -->|HTTP 202 Accepted| User

    API -->|Background Task| Worker[Async Worker]
    Worker -->|1. Check Similarity| Chroma[(ChromaDB Semantic Cache)]
    Chroma -- Cache Hit --> Worker

    Worker -->|2. Cache Miss + RAG Context| LLM{Gemini 1.5 API}
    LLM --> Worker

    Worker -->|3. Persist State| SQL[(SQLite State DB)]
    User -->|GET /tickets/{id}| API
    API --> SQL

```

## 🚀 Key Features

* **Asynchronous Processing:** Built with FastAPI `BackgroundTasks` to ensure millisecond response times (HTTP 202) during high-load traffic spikes.
* **FinOps Vector Shield:** Integrates `ChromaDB` (`all-MiniLM-L6-v2`) to vectorize incoming tickets. If a semantically similar ticket exists (Cosine distance > 0.6), the system bypasses the LLM API, saving quota and reducing latency.
* **Dynamic RAG & Human-in-the-Loop:** Features a `/feedback` endpoint. When a human corrects an AI misclassification, the vector brain is updated. Future requests will inject this historical truth into the LLM prompt (Few-Shot Prompting).
* **Self-Healing Adapters:** The `LLMProvider` interface automatically handles HTTP 429 (Rate Limits) using an Exponential Backoff & Jitter algorithm.
* **Infrastructure as Code:** Fully orchestrated via `docker-compose`, ensuring persistent volumes for both the SQL state and the Vector memory.

---

## 🛠️ Installation & Setup

### Prerequisites

* A Google Gemini API Key.
* Docker & Docker Compose.
* *(Alternative)* Python 3.13+ for bare-metal execution.

### Method A: Production Deployment (Docker Compose)

1. **Clone the repository:**

```bash
git clone [https://github.com/your-username/ai-ticket-triage.git](https://github.com/your-username/ai-ticket-triage.git)
cd ai-ticket-triage

```

2. **Configure Environment:**
Create a `.env` file in the root directory:

```ini
GEMINI_API_KEY=your_api_key_here
DB_URL=sqlite:////app/data/tickets.db

```

3. **Deploy the Infrastructure:**

```bash
docker compose up -d --build

```

*The API is now running at `http://localhost:8000/docs`.*

### Method B: Bare-Metal Execution (Windows 11 Native)

If Docker is unavailable, you can run the engine directly on your host machine.

1. **Create and activate a virtual environment:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1

```

2. **Install dependencies:**

```powershell
pip install -r requirements.txt

```

3. **Adjust `.env` for local paths:**

```ini
GEMINI_API_KEY=your_api_key_here
DB_URL=sqlite:///tickets.db

```

4. **Launch the FastAPI Server:**

```powershell
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload

```

---

## 🎯 Live Demo Protocol

To properly demonstrate the architectural capabilities, follow this 4-phase sequence via the Swagger UI (`http://localhost:8000/docs`):

### Phase 1: Asynchronous Ingestion & Latency Test

* **Action:** Execute `POST /classify` with a complex IT issue (e.g., *"Jenkins deployment timeout connecting to AWS"*).
* **Observation:** The API returns `HTTP 202 Accepted` instantly with a `ticket_id`. The heavy LLM processing happens in the background.

### Phase 2: State Polling

* **Action:** Execute `GET /tickets/{ticket_id}` using the ID from Phase 1.
* **Observation:** Verify the status has changed from `Pending` to `Classified_By_AI`.

### Phase 3: The Semantic Shield (FinOps Test)

* **Action:** Execute `POST /classify` with a *differently worded* version of the Phase 1 issue (e.g., *"AWS prod connection drops during CI/CD build"*).
* **Observation:** Check the status via `GET /tickets/{ticket_id}`. The status **must** be `Classified_By_Cache`. The system recognized the semantic intent and bypassed the LLM completely.

### Phase 4: Human-in-the-Loop (RAG Correction)

* **Action:** Execute `POST /tickets/{ticket_id}/feedback` to force a new category (e.g., change from "Software" to "Access").
* **Observation:** The Vector Database is updated. The next time a similar ticket arrives, the AI will use this corrected history as context and output "Access".

---

## 🔮 Future Roadmap

* [ ] **Distributed Task Queue:** Migrate `BackgroundTasks` to `Celery` + `Redis` for absolute data immortality and horizontal scaling.
* [ ] **Observability Dashboards:** Instrument the API with Prometheus to export Cache Hit Ratios and LLM latencies to Grafana.
* [ ] **Automated Backfill Script:** Implement a batch-processing CLI tool for migrating historical CSV data into the Vector Database efficiently.

---

**Author:** Alejandro Casa
