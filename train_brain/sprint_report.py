import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
import os
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

# --- 0. PATH & ENV CONFIG ---
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent  # /train_brain
PROJECT_ROOT = BASE_DIR.parent              # /SPRINT_PLANER

# Define where the image will be saved
# Ensure your 'Backend/static' folder exists!
REPORT_IMAGE_PATH = PROJECT_ROOT / "Backend" / "static" / "sprint_report.png"

user = os.getenv("DB_USER", "root")
raw_password = os.getenv("DB_PASSWORD", "")
password = urllib.parse.quote_plus(raw_password)
host = os.getenv("DB_HOST", "localhost")
db = os.getenv("DB_NAME", "smart_planner")

engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}/{db}")

# --- 1. CORE REPORTING FUNCTION ---
def generate_sprint_analytics():
    """
    Fetches assignment data from MySQL, aggregates utilization,
    and generates a workload visualization image.
    """
    try:
        # Fetch Data
        query = """
            SELECT s.assigned_to, s.predicted_hours, d.experience_level 
            FROM sprint_table s
            JOIN developers d ON s.assigned_to = d.name
            WHERE s.status = 'Assigned'
        """
        df = pd.read_sql(query, con=engine)

        if df.empty:
            return {"status": "error", "message": "No assigned tasks found in DB."}

        # Aggregate Workload
        workload = df.groupby(['assigned_to', 'experience_level'])['predicted_hours'].sum().reset_index()
        CAPACITY = 40.0
        workload['utilization_pct'] = (workload['predicted_hours'] / CAPACITY) * 100

        # --- VISUALIZATION (Server-Safe Mode) ---
        plt.switch_backend('Agg') # Essential for FastAPI
        plt.figure(figsize=(12, 6))
        sns.set_theme(style="whitegrid")

        top_loaded = workload.sort_values(by='predicted_hours', ascending=False).head(20)

        sns.barplot(
            data=top_loaded, 
            x='assigned_to', 
            y='predicted_hours', 
            hue='experience_level',
            palette='magma'
        )

        plt.axhline(y=CAPACITY, color='red', linestyle='--', label='Max Capacity (40h)')
        plt.title('Top 20 Developer Workloads (Current Sprint)', fontsize=15)
        plt.xticks(rotation=45)
        plt.ylabel('Total Predicted Hours')
        plt.legend()
        plt.tight_layout()

        # Save to static folder
        REPORT_IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(REPORT_IMAGE_PATH)
        plt.close()

        # Return Data for the Frontend
        return {
            "status": "success",
            "metrics": {
                "total_devs": int(workload['assigned_to'].nunique()),
                "avg_utilization": round(float(workload['utilization_pct'].mean()), 2),
                "overloaded_count": int(len(workload[workload['predicted_hours'] > CAPACITY]))
            },
            "report_url": "/static/sprint_report.png"
        }

    except Exception as e:
        print(f"🔥 Reporting Error: {e}")
        return {"status": "error", "message": str(e)}