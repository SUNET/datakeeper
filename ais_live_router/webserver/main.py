import os
import asyncio
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, Form, Depends, status
from ais_live_router.webserver.requests import PolicyBase, JobBase
from ais_live_router.webserver import sse_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    sse_manager.job_event_queue = asyncio.Queue()
    sse_manager.data_event_queue = asyncio.Queue()
    sse_manager.set_main_event_loop(asyncio.get_running_loop())
    yield
    sse_manager.job_event_queue = None
    sse_manager.data_event_queue = None

# API application
app = FastAPI(
    title="DataKeeper API", description="Management API for DataKeeper Policy System",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_FOLDER = os.path.join(os.path.dirname(__file__), "static")
TEMPLATES_FOLDER = os.path.join(os.path.dirname(__file__), "templates")

app.mount("/static", StaticFiles(directory=STATIC_FOLDER), name="static")
templates = Jinja2Templates(directory=TEMPLATES_FOLDER)

@app.get("/")
def read_root(request: Request):
    jobs_dict = []
    return templates.TemplateResponse(
        "index.html", {"request": request, "jobs": jobs_dict}
    )

@app.get("/events")
async def sse_endpoint():
    # return StreamingResponse(event_generator(), media_type="text/event-stream")
    return StreamingResponse(sse_manager.event_stream(), media_type="text/event-stream")

@app.get(
    "/status",
    status_code=status.HTTP_200_OK,
)
def get_status(request: Request):
    return {"status": "running"}
