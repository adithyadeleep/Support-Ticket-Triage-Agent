from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from app.services.kb import KnowledgeBaseService
from app.services.agent import TriageAgent
from app.config import get_settings
from app.middleware import RateLimitMiddleware
import logging

logger = logging.getLogger(__name__)

app = FastAPI()
settings = get_settings()

# Mount templates
templates = Jinja2Templates(directory="templates")

# Add rate limit middleware (adjust settings here)
app.add_middleware(RateLimitMiddleware, max_requests=20, window_seconds=60)

# Initialize KB and agent
kb_service = KnowledgeBaseService(settings.KB_PATH)
agent = TriageAgent(kb_service)

class TicketInput(BaseModel):
    text: str

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Simple HTML form to submit a ticket.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/submit", response_class=HTMLResponse)
async def submit(request: Request, text: str = Form(...)):
    """
    Handle form submission from UI, call the agent and show results.
    """
    try:
        result = await agent.process(text)
    except Exception as e:
        logger.exception("Agent failed: %s", e)
        # Show error page
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e)})

    return templates.TemplateResponse("result.html", {"request": request, "result": result})

@app.post("/triage")
async def triage(input: TicketInput):
    if not input.text.strip():
        raise HTTPException(status_code=400, detail="Description required")
    try:
        return await agent.process(input.text)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
