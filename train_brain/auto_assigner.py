import joblib
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import urllib.parse
import os
from dotenv import load_dotenv

load_dotenv()
user = os.getenv("DB_USER", "root")
password = urllib.parse.quote_plus(os.getenv("DB_PASSWORD"))
engine = create_engine(f"mysql+pymysql://{user}:{password}@localhost/smart_planner")

# 1. Ensure Columns Exist First
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE sprint_table MODIFY COLUMN status VARCHAR(50)")) # Ensure status is wide enough
    try: conn.execute(text("ALTER TABLE sprint_table ADD COLUMN assigned_to VARCHAR(255)"))
    except: pass # Column already exists
    try: conn.execute(text("ALTER TABLE sprint_table ADD COLUMN predicted_hours FLOAT"))
    except: pass # Column already exists

# 2. Load Brains & Data
time_model = joblib.load('time_model.pkl')
risk_model = joblib.load('risk_model.pkl')

tasks_df = pd.read_sql("SELECT * FROM sprint_table WHERE status = 'Unassigned'", con=engine)
devs_df = pd.read_sql("SELECT * FROM developers", con=engine)

devs_df['remaining_hours'] = 40.0
level_map = {'Junior': 1, 'Mid': 2, 'Senior': 3}
devs_df['lv_val'] = devs_df['experience_level'].map(level_map)

assignments = []
tasks_df = tasks_df.sort_values(by='story_points', ascending=False)

print(f"⚡ Turbo Assigning {len(tasks_df)} tasks...")

# 3. Allocation Loop
for _, task in tasks_df.iterrows():
    input_data = pd.DataFrame({
        'story_points': [task['story_points']] * len(devs_df),
        'experience_level': devs_df['lv_val'].values,
        'team_load_percentage': [100] * len(devs_df)
    })
    
    all_times = time_model.predict(input_data)
    all_risks = risk_model.predict_proba(input_data)[:, 1]
    costs = all_times + (all_risks * 20)
    
    can_fit = devs_df['remaining_hours'].values >= all_times
    
    if np.any(can_fit):
        valid_indices = np.where(can_fit)[0]
        best_idx = valid_indices[np.argmin(costs[valid_indices])]
        
        dev_name = devs_df.at[best_idx, 'name']
        pred_time = all_times[best_idx]
        
        devs_df.at[best_idx, 'remaining_hours'] -= pred_time
        
        assignments.append({
            'task_id': task['task_id'],
            'assigned_to': dev_name,
            'predicted_hours': round(float(pred_time), 2),
            'status': 'Assigned'
        })

# 4. Bulk Update
if assignments:
    results_df = pd.DataFrame(assignments)
    results_df.to_sql('temp_assignments', con=engine, if_exists='replace', index=False)
    
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE sprint_table s
            JOIN temp_assignments t ON s.task_id = t.task_id
            SET s.assigned_to = t.assigned_to,
                s.status = t.status,
                s.predicted_hours = t.predicted_hours
        """))
        conn.execute(text("DROP TABLE temp_assignments"))
    print(f"🎉 Done! All {len(assignments)} tasks assigned.")