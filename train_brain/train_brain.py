import pandas as pd
import os
from sqlalchemy import create_engine
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
import joblib
import urllib.parse
import pathlib
from dotenv import load_dotenv

# 1. Database Connection

load_dotenv()

user = os.getenv("DB_USER")
raw_password = os.getenv("DB_PASSWORD")
password = urllib.parse.quote_plus(raw_password)
engine = create_engine(f"mysql+pymysql://{user}:{password}@localhost/smart_planner")

# 2. Fetch the new data (including is_failed)
query = """
SELECT t.story_points, t.actual_hours, t.is_failed, d.experience_level, s.team_load_percentage 
FROM historical_tasks t
JOIN developers d ON t.dev_id = d.dev_id
JOIN sprint_context s ON t.sprint_id = s.sprint_id;
"""
df = pd.read_sql(query, con=engine)

# 3. Encoding
level_map = {'Junior': 1, 'Mid': 2, 'Senior': 3}
df['experience_level'] = df['experience_level'].map(level_map)

# 4. Define Inputs (X)
X = df[['story_points', 'experience_level', 'team_load_percentage']]

# --- BRAIN 1: THE REGRESSOR (Predicts Time) ---
model_time = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
model_time.fit(X, df['actual_hours'])

# --- BRAIN 2: THE CLASSIFIER (Predicts Failure Probability) ---
model_risk = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
model_risk.fit(X, df['is_failed'])

# 5. Save both brains
joblib.dump(model_time, 'time_model.pkl')
joblib.dump(model_risk, 'risk_model.pkl')

print("✅ Phase 4.5 Training Complete: Both brains are ready!")