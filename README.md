# Support Ticket Triage Agent

Lightweight production-ready prototype: an AI agent that classifies support tickets, searches a local KB (BM25), and suggests next actions.  
Built with FastAPI, rank_bm25, and a pluggable LLM provider (mock by default).  
Designed to run on constrained developer machines (works on 4GB RAM using the mock provider).

---

## Table of Contents

- [Quick demo](#quick-demo)
- [How to run locally](#how-to-run-locally)
  - [Prerequisites](#prerequisites)
  - [Install dependencies (Conda)](#install-dependencies-conda)
  - [Start the service](#start-the-service)
  - [Call the /triage endpoint (examples)](#call-the-triage-endpoint-examples)
  - [Run with Docker (optional)](#run-with-docker-optional)
- [Project layout](#project-layout)
- [Agent design & implementation notes](#agent-design--implementation-notes)
  - [How the LLM is used](#how-the-llm-is-used)
  - [KB search / tools](#kb-search--tools)
  - [Orchestration & separation of concerns](#orchestration--separation-of-concerns)
  - [Trade-offs made due to time / resource constraints](#trade-offs-made-due-to-time--resource-constraints)
  - [Bonus features included](#bonus-features-included)
- [Production considerations](#production-considerations)
  - [Deployment & scaling](#deployment--scaling)
  - [Logging & monitoring](#logging--monitoring)
  - [Configuration & secrets](#configuration--secrets)
  - [Latency, cost, and rate-limiting strategy](#latency-cost-and-rate-limiting-strategy)
  - [Security](#security)
- [Testing](#testing)
- [Contributing / License / Contact](#contributing--license--contact)
---

## Quick demo

Launch the app (see below).

Open the browser:

- **UI:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Submit a description such as:

> VPN error 800 cannot connect since morning.

Result: structured JSON with `summary, category, severity, key_entities, similar_issues, suggested_action, and known_issue`.

---

## How to run locally

The repository is intentionally lightweight — the default provider is a mock LLM so you can run everything on low-RAM machines (4GB). Swap in a cloud LLM later for production.

### Prerequisites

- Conda (Miniconda/Anaconda) installed on Windows/macOS/Linux
- Git (optional)
- Python 3.11 (the Conda env below installs it)
- Port 8000 free

### Install dependencies (Conda)

Open **Anaconda Prompt (Windows)** or **terminal (macOS/Linux)**:

```bash
# Create and activate the conda env
conda create -n triage python=3.11 -y
conda activate triage

# From project root (where requirements.txt lives)
pip install -r requirements.txt
```

**requirements.txt contains:**
```
fastapi
uvicorn
pydantic
rank_bm25
python-dotenv
jinja2
```

### Start the service

From project root:

```bash
uvicorn app.main:app --reload --port 8000
```

You should see Uvicorn running on [http://127.0.0.1:8000](http://127.0.0.1:8000).

### Call the `/triage` endpoint (examples)

#### Using Swagger UI

Open: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) → POST /triage → provide JSON body:

```json
{ "text": "VPN error 800 cannot connect" }
```

#### Using curl (Linux / macOS)

```bash
curl -X POST "http://127.0.0.1:8000/triage" \
  -H "Content-Type: application/json" \
  -d '{"text":"VPN error 800 cannot connect"}'
```

#### Using PowerShell (Windows)

```powershell
Invoke-RestMethod -Method POST "http://127.0.0.1:8000/triage" `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{ "text": "VPN error 800 cannot connect" }'
```

### Run with Docker (optional)

Build and run (small image):

```bash
docker build -t triage-agent:local .
docker run -d --name triage-agent --memory="512m" --cpus="1.0" -p8000:8000 triage-agent:local
```

Limit the container memory to avoid OOM on low-RAM hosts.

---

## Project layout

```
triage-agent/
├── requirements.txt
├── Dockerfile
├── README.md
├── data/
│   └── kb.json            # Knowledge base (10–15 entries)
├── templates/
│   ├── index.html         # UI
│   └── result.html
└── app/
    ├── main.py            # FastAPI app and routes
    ├── config.py         # environment settings loader
    ├── schemas.py        # Pydantic models
    └── services/
        ├── agent.py      # Orchestration
        ├── kb.py         # BM25 KB service
        └── provider.py   # Mock/provider factory
```

---

## Agent design & implementation notes

### How the LLM is used

The code is written to call a provider through a single interface (`provider.analyze(text)`).

- Default provider: **MockProvider**, deterministic and very lightweight (no external API keys required).
- For production, you can plug in any provider (OpenAI/Gemini/Groq) by implementing the same `analyze` async method in `app/services/provider.py`. The rest of the system remains unchanged.

### KB search / tools

- Local KB stored in `data/kb.json` (JSON array of entries).
- `app/services/kb.py` builds a BM25 index using **rank_bm25** for memory-efficient lexical retrieval (no embeddings, no heavy libraries).

The agent:
- Calls `provider.analyze` → get structured analysis.
- Builds a simple KB query from category + key_entities.
- Retrieves top-N results (default 3) from BM25.
- Combines analysis + KB hits into a final response: `known_issue` (true/false), `suggested_action`.

### Orchestration & separation of concerns

- **Provider (LLM):** natural-language understanding, produces schema-aligned JSON.
- **KB (Tool):** deterministic retrieval tool for domain knowledge.
- **Agent:** orchestration logic, retries/timeouts, synthesis of final output.
- **API:** stable interface for clients and UI.

### Trade-offs made due to time / resource constraints

- Uses a mock LLM by default so the prototype runs on a 4GB machine.
- Uses BM25 (lexical search) instead of vector search to save memory and dependencies.
- Rate limiting is in-memory for single-instance demos.

### Bonus features included

- Retry + exponential-backoff for provider calls (decorator-style).
- Timeouts on provider requests.
- Simple in-memory rate limiter (per-IP).
- Light professional UI (server-rendered Jinja2 templates).
- Multi-environment config support (.env.development / .env.production).

---

## Production considerations

### Deployment & scaling

- Containerize the app (Dockerfile provided).
- For production: deploy as containers on AWS ECS/Fargate, GCP Cloud Run, Azure App Service, or Kubernetes.
- Use an autoscaling group (K8s HPA / Cloud Run concurrency) behind a load balancer.
- For high QPS, horizontally scale the FastAPI service; make KB read-only and share between instances (kb.json in S3 + local cache).
- Use managed LLMs for inference (Gemini, OpenAI, Groq).

### Logging & monitoring

- Emit structured JSON logs (timestamp, level, request id, latency, provider latency, KB hits).
- Integrate with observability platforms:
  - **Tracing:** OpenTelemetry + Jaeger / Datadog APM / LangFuse
  - **Metrics:** Prometheus + Grafana
  - **Centralized logs:** ELK / Datadog / Splunk
- Add request IDs and correlate logs across LLM calls and KB queries.

### Configuration & secrets

- Store secrets in environment variables or a secret manager.
- Use 12-factor approach for config.
- .env.* is for local dev only.

### Latency, cost, and rate limiting

- **Latency:** LLM calls are dominant. Reduce prompt size, cache repeated results.
- **Cost:** Hybrid strategy — local BM25 for KB + cloud LLM for reasoning.
- **Rate limiting:** Per-user/IP; for production use centralized Redis.

### Security

- Validate/sanitize user input.
- Strict Pydantic schemas for enforcing response shapes.
- Limit body size, enforce authentication for production endpoints.
- Use HTTPS everywhere.

---

## Testing

**Unit tests:**

- agent.process (happy path & KB-match path)
- empty description (400)
- very long text (edge case)

**Integration tests:**

- Use test KB + mock provider

Example (`pytest`):

```bash
pip install pytest
pytest tests/
```

---

## Contributing

1. Fork the repo, create a feature branch, open a PR.
2. Write tests for new features.
3. Keep code style consistent (black / isort / flake8).

---

## License & Contact

**MIT License** (suggested). Add LICENSE file if open-sourcing.

Questions? Ping me on repo issues or add a contact line in README.

---

## Final notes

Enjoy!
