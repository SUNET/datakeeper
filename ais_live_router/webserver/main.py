import os
import asyncio
import numpy as np
import time, datetime, json
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from ais_live_router.webserver import sse_manager
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, StreamingResponse
from ais_live_router.webserver.requests import PolicyBase, JobBase
from ais_live_router.webserver.data_ingestion import DataIngestion

@asynccontextmanager
async def lifespan(app: FastAPI):
    sse_manager.job_event_queue = asyncio.Queue()
    sse_manager.data_event_queue = asyncio.Queue()
    sse_manager.set_main_event_loop(asyncio.get_running_loop())
    yield
    sse_manager.job_event_queue = None
    sse_manager.data_event_queue = None

def generate_vessels():
    vessels = []
    for i in range(5):
        angle = np.random.random() * 2 * np.pi
        distance = np.random.random() * 0.5
        lat = 59.612 + distance * np.cos(angle)
        lon = 17.387 + distance * np.sin(angle)
        vessels.append({
            "id": f"vessel_{i}",
            "name": f"Ship {i}",
            "type": np.random.choice(["Cargo", "Tanker", "Passenger", "Fishing"]),
            "lat": lat,
            "lon": lon,
            "speed": round(np.random.random() * 15 + 5, 2),
            "heading": round(np.random.random() * 360, 2),
            "timestamp": datetime.datetime.now().isoformat()
        })
    return vessels


# API application
app = FastAPI(
    title="DataKeeper API", description="Management API for DataKeeper Policy System",
    lifespan=lifespan
)
ais_data = DataIngestion(data_source=os.environ.get("data_type", 'mongodb'))

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

# @app.get("/", response_class=HTMLResponse)
@app.get("/")
async def index(request: Request):
    # with open("templates/index.html") as f:
    #     return HTMLResponse(f.read())
    return templates.TemplateResponse(
        "index.html", {"request": request, "jobs": []}
    )
    
async def event_stream():
    while True:
        vessels = generate_vessels()
        yield f"data: {json.dumps(vessels)}\n\n"
        await asyncio.sleep(15)
        
async def event_stream_ais():
    while True:
        vessels = ais_data._get_vessel_data()
        yield f"data: {json.dumps(vessels)}\n\n"
        await asyncio.sleep(15)

@app.get("/events")
async def sse():
    return StreamingResponse(event_stream_ais(), media_type="text/event-stream")
