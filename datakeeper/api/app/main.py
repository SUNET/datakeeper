import os
import asyncio
from typing import List, Tuple
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from datakeeper.api.app.models import Policy, Job
from fastapi.middleware.cors import CORSMiddleware
from datakeeper.api.app.db import get_db, db_engine, Base
from fastapi import FastAPI, Request, Form, Depends, status
from datakeeper.api.app.requests import PolicyResponseModel, JobResponseModel
from datakeeper.api.app import sse_manager


def init_db(Base):
    Base.metadata.create_all(bind=db_engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    sse_manager.job_event_queue = asyncio.Queue()
    sse_manager.data_event_queue = asyncio.Queue()
    sse_manager.set_main_event_loop(asyncio.get_running_loop())
    yield
    sse_manager.job_event_queue = None
    sse_manager.data_event_queue = None

init_db(Base)
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
def read_root(request: Request, db: Session = Depends(get_db)):
    jobs = db.query(Job).all()

    # Convert all the jobs data to a json dict
    jobs_dict = [JobResponseModel.model_validate(job).model_dump() for job in jobs]

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
def get_status(request: Request, db: Session = Depends(get_db)):
    return {"status": "running"}



@app.get(
    "/policy",
    status_code=status.HTTP_200_OK,
    response_model=List[PolicyResponseModel],
)
def get_policies(request: Request, db: Session = Depends(get_db)):
    policies = db.query(Policy).all()
    return policies


@app.get(
    "/job",
    status_code=status.HTTP_200_OK,
    response_model=List[JobResponseModel],
)
def get_jobs(request: Request, db: Session = Depends(get_db)):
    jobs = db.query(Job).all()
    return jobs

@app.post("/add")
def add_task(request: Request, title: str = Form(...), db: Session = Depends(get_db)):
    new_task = Policy(title=title)
    db.add(new_task)
    db.commit()
    return templates.TemplateResponse(
        "tasks.html", {"request": request, "tasks": db.query(Policy).all()}
    )


@app.post("/delete/{task_id}")
def delete_task(request: Request, task_id: int, db: Session = Depends(get_db)):
    task = db.query(Policy).filter(Policy.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()
    return templates.TemplateResponse(
        "tasks.html", {"request": request, "tasks": db.query(Policy).all()}
    )
