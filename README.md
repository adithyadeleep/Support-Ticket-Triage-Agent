Table of contents

Quick demo

How to run locally

Prerequisites

Install dependencies (Conda)

Start the service

Call the /triage endpoint (examples)

Run with Docker (optional)

Project layout

Agent design & implementation notes

How the LLM is used

KB search / tools

Orchestration & separation of concerns

Trade-offs made due to time / resource constraints

Bonus features included

Production considerations

Deployment & scaling

Logging & monitoring

Configuration & secrets

Latency, cost, and rate-limiting strategy

Security

Testing

Contributing / License / Contact

Quick demo

Launch the app (see below).

Open the browser:

UI: http://127.0.0.1:8000/

Swagger: http://127.0.0.1:8000/docs

Submit a description such as:

VPN error 800 cannot connect since morning.
Result: structured JSON with summary, category, severity, key_entities, similar_issues, suggested_action, and known_issue.

How to run locally

The repository is intentionally lightweight — the default provider is a mock LLM so you can run everything on low-RAM machines (4GB). Swap in a cloud LLM later for production.

Prerequisites

Conda (Miniconda/Anaconda) installed on Windows/macOS/Linux

Git (optional)

Python 3.11 (the Conda env below installs it)

Port 8000 free

Install dependencies (Conda)

Open Anaconda Prompt (Windows) or terminal (macOS/Linux):

# Create and activate the conda env
conda create -n triage python=3.11 -y
conda activate triage

# From project root (where requirements.txt lives)
pip install -r requirements.txt


requirements.txt contains:

fastapi
uvicorn
pydantic
rank_bm25
python-dotenv
jinja2

Start the service

From project root:

uvicorn app.main:app --reload --port 8000


You should see Uvicorn running on http://127.0.0.1:8000.

Call the /triage endpoint (examples)
Using Swagger UI

Open: http://127.0.0.1:8000/docs → POST /triage → provide JSON body:

{ "text": "VPN error 800 cannot connect" }

Using curl (Linux / macOS)
curl -X POST "http://127.0.0.1:8000/triage" \
  -H "Content-Type: application/json" \
  -d '{"text":"VPN error 800 cannot connect"}'

Using PowerShell (Windows)
Invoke-RestMethod -Method POST "http://127.0.0.1:8000/triage" `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{ "text": "VPN error 800 cannot connect" }'

Run with Docker (optional)

Build and run (small image):

docker build -t triage-agent:local .
docker run -d --name triage-agent --memory="512m" --cpus="1.0" -p8000:8000 triage-agent:local


Limit the container memory to avoid OOM on low-RAM hosts.

Project layout
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

Agent design & implementation notes
How the LLM is used

The code is written to call a provider through a single interface (provider.analyze(text)).

Default provider: MockProvider, deterministic and very lightweight (no external API keys required).

For production, you can plug in any provider (OpenAI/Gemini/Groq) by implementing the same analyze async method in app/services/provider.py. The rest of the system remains unchanged.

KB search / tools

Local KB stored in data/kb.json (JSON array of entries).

app/services/kb.py builds a BM25 index using rank_bm25 for memory-efficient lexical retrieval (no embeddings, no heavy libraries).

The agent:

Calls provider.analyze → get structured analysis.

Builds a simple KB query from category + key_entities.

Retrieves top-N results (default 3) from BM25.

Combines analysis + KB hits into a final response: known_issue (true/false), suggested_action.

Orchestration & separation of concerns

Provider (LLM): responsible for natural-language understanding and producing schema-aligned JSON.

KB (Tool): deterministic retrieval tool for domain knowledge.

Agent: orchestration logic, retries/timeouts, and synthesis of final output.

API: Stable interface for clients and UI.

Trade-offs made due to time & resource constraints

Uses a mock LLM by default so the prototype runs on a 4GB machine. Running local frontier LLMs is not practical on such hardware; cloud LLMs are recommended for production.

Uses BM25 (lexical search) instead of vector search to avoid the heavy memory and dependency footprint of embedding models and vector DBs.

Rate limiting is in-memory and suitable for single-instance demos; production should use Redis or CDN-based throttling.

Bonus features included

Retry + exponential-backoff for provider calls (decorator-style).

Timeouts on provider requests to avoid hanging.

Simple in-memory rate limiter (per-IP) to demonstrate throttling behavior.

Light professional UI (server-rendered Jinja2 templates).

Multi-environment config support (.env.development / .env.production).

Production considerations
Deployment & scaling

Containerize the app (Dockerfile provided). For production:

Deploy as containers on AWS ECS/Fargate, GCP Cloud Run, Azure App Service, or Kubernetes.

Use an autoscaling group (K8s HPA / Cloud Run concurrency) behind a load balancer.

For high QPS, horizontally scale the FastAPI service; make KB read-only and shared between instances (store kb.json in S3 + warm local cache on startup).

Use a managed LLM (Gemini, OpenAI, Groq) for inference — do not attempt local model hosting on low-RAM nodes.

Logging & monitoring

Emit structured JSON logs (timestamp, level, request id, latency, provider latency, KB hits).

Integrate with observability platforms:

Tracing: OpenTelemetry + Jaeger / Datadog APM or LangFuse for LLM call tracing.

Metrics: Prometheus + Grafana (request rate, error rate, provider latency, KB lookup time).

Centralized logs: ELK / Datadog / Splunk.

Add request IDs and correlate logs across LLM calls and KB queries.

Configuration & secrets

Never store API keys in repo. Use environment variables or a secret manager:

AWS Secrets Manager, GCP Secret Manager, Azure Key Vault, or HashiCorp Vault.

In Kubernetes, use Secrets (or sealed secrets), mounted as env vars or files.

Use a 12-factor approach: all config from env vars. .env.* is for dev convenience only.

Latency, cost, and rate limiting

Latency:

LLM calls are the dominant factor. Reduce prompt size, use structured “JSON mode” if available, and cache results for repeated tickets.

Use asynchronous calls and connection pooling.

Cost:

Use a hybrid strategy: local BM25 for KB + cloud LLM only for reasoning. This reduces tokens and therefore cost.

Batch similar tickets or debounce low-priority tickets.

Rate limiting:

Implement per-user or per-IP token buckets. For multi-instance deploys, use Redis for centralized counters.

For expensive LLM endpoints, implement a queue with worker pool and SLA-based prioritization.

Security

Validate and sanitize user input; reject extremely long or malicious payloads.

Strict Pydantic schemas ensure response shape — helps to avoid injection when LLMs are used.

Limit body size and file uploads; enforce authentication for production endpoints (OAuth2 / API keys / mTLS).

Use HTTPS everywhere (TLS termination at LB / ingress).
