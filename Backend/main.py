import sys
import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# --- 1. PATH SETUP ---
# Resolves the path to 'SPRINT_PLANER' root
BASE_DIR = Path(__file__).resolve().parent  # /Backend
PROJECT_ROOT = BASE_DIR.parent     

         # /SPRINT_PLANER

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# --- 2. IMPORT MODULES FROM train_brain ---
try:
    from train_brain import use_ai
    from train_brain import auto_assigner
    from train_brain import sprint_report
except Exception as e:
    print(f"❌ CRITICAL LOAD FAILURE: {e}")
    # This will stop the server if imports fail, so you don't get NameErrors later
    sys.exit(1)
# --- 3. APP CONFIG ---
load_dotenv()
app = FastAPI(title="Sprint Planer AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static folder for the generated report images
static_dir = PROJECT_ROOT / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# --- 4. SCHEMAS ---
class TaskItem(BaseModel):
    task_id: int
    story_points: int

class PredictionRequest(BaseModel):
    tasks: List[TaskItem]
    current_team_load: float
    deadline_limit: Optional[float] = 40.0

# --- 5. ENDPOINTS ---
@app.get("/", tags=["Health System"])
async def root():
    """
    Root Health Check: Confirms the API is reachable and provides doc links.
    Fixes the '404 Not Found' error on the home page.
    """
    return {
        "status": "online",
        "engine": "FastAPI + Scikit-Learn",
        "docs": "/docs",
        "health": "Green"
    }

@app.post("/api/predict-sprint")
async def predict(data: PredictionRequest):
    results = use_ai.process_tasks(data.tasks, data.current_team_load, data.deadline_limit)
    if not results:
        raise HTTPException(status_code=500, detail="AI Inference Failed")
    return {"predictions": results}

@app.post("/api/auto-assign")
async def assign():
    return auto_assigner.run_auto_assignment()


@app.get("/api/sprint-report")
async def get_report():
    """
    Triggers AI analytics and returns workload metrics 
    along with the report image URL.
    """
    result = sprint_report.generate_sprint_analytics()
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])
    return result