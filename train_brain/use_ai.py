import joblib
import pandas as pd
from sqlalchemy import create_engine
import os
import urllib.parse
from dotenv import load_dotenv
from pathlib import Path

# --- 0. DYNAMIC PATH CONFIG (The Fix) ---
load_dotenv()
# BASE_DIR is /train_brain
BASE_DIR = Path(__file__).resolve().parent 
# MODEL_DIR is the Root folder (SPRINT_PLANER) where your .pkl files are
MODEL_DIR = BASE_DIR.parent 

user = os.getenv("DB_USER", "root")
raw_password = os.getenv("DB_PASSWORD") 
host = os.getenv("DB_HOST", "localhost")
db = os.getenv("DB_NAME", "smart_planner")

password = urllib.parse.quote_plus(raw_password) if raw_password else ""
engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}/{db}")

# --- 1. LOAD MODELS USING THE DYNAMIC PATH ---
# Changed from 'time_model.pkl' to MODEL_DIR / 'time_model.pkl'
try:
    time_model = joblib.load(MODEL_DIR / 'time_model.pkl')
    risk_model = joblib.load(MODEL_DIR / 'risk_model.pkl')
    print("✅ Models loaded successfully from Root directory")
except Exception as e:
    print(f"❌ Model Load Error: {e}")
    time_model = None
    risk_model = None

# --- 2. DB HELPER ---
def get_available_devs(level_name):
    query = f"SELECT name FROM developers WHERE experience_level = '{level_name}' LIMIT 3"
    try:
        devs = pd.read_sql(query, con=engine)
        return devs['name'].tolist()
    except Exception as e:
        print(f"DB Error: {e}")
        return []

# --- 3. CORE LOGIC FUNCTION (For FastAPI) ---
def process_tasks(tasks, team_load, user_deadline=40.0):
    if time_model is None:
        return None

    analysis_results = []
    levels = {1: "Junior", 2: "Mid", 3: "Senior"}

    for task in tasks:
        task_options = []
        pts = task.story_points
        
        for val, name in levels.items():
            feat = pd.DataFrame([[pts, val, team_load]], 
                                columns=['story_points', 'experience_level', 'team_load_percentage'])
            
            # Predict
            est_time = float(time_model.predict(feat)[0])
            risk_prob = float(risk_model.predict_proba(feat)[0][1] * 100)
            
            task_options.append({
                "level_name": name,
                "time": est_time,
                "risk": risk_prob,
                "is_reliable": risk_prob < 30,
                "is_on_time": est_time <= user_deadline
            })

        # Selection: Best AI (Lowest Risk)
        best_ai = sorted(task_options, key=lambda x: x['risk'])[0]
        dev_names = get_available_devs(best_ai['level_name'])

        analysis_results.append({
            "task_id": task.task_id,
            "recommended_level": best_ai['level_name'],
            "predicted_hours": round(best_ai['time'], 2),
            "risk_score": round(best_ai['risk'], 2),
            "suggested_developers": dev_names
        })

    return analysis_results