import pandas as pd
import random
import urllib.parse
from sqlalchemy import create_engine

# --- 0. CONNECTION SETUP ---
# user = "root"
# raw_password = "12410279"
# password = urllib.parse.quote_plus(raw_password)
# host = "localhost"
# db = "smart_planner"

engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}/{db}")

print(" Starting Phase 1: Full Database Population...")

# --- 1. TABLE: DEVELOPERS ---
devs_data = [
    {'dev_id': 1, 'name': 'Alice', 'experience_level': 'Senior', 'primary_skill': 'Backend'},
    {'dev_id': 2, 'name': 'Bob', 'experience_level': 'Junior', 'primary_skill': 'Frontend'},
    {'dev_id': 3, 'name': 'Charlie', 'experience_level': 'Mid', 'primary_skill': 'API'},
    {'dev_id': 4, 'name': 'David', 'experience_level': 'Senior', 'primary_skill': 'DevOps'},
    {'dev_id': 5, 'name': 'Eve', 'experience_level': 'Junior', 'primary_skill': 'UI/UX'},
    {'dev_id': 6, 'name': 'Frank', 'experience_level': 'Mid', 'primary_skill': 'Backend'},
    {'dev_id': 7, 'name': 'Grace', 'experience_level': 'Senior', 'primary_skill': 'Frontend'},
    {'dev_id': 8, 'name': 'Heidi', 'experience_level': 'Junior', 'primary_skill': 'API'},
    {'dev_id': 9, 'name': 'Ivan', 'experience_level': 'Mid', 'primary_skill': 'Database'},
    {'dev_id': 10, 'name': 'Judy', 'experience_level': 'Senior', 'primary_skill': 'Security'}
]
df_devs = pd.DataFrame(devs_data)

# --- 2. TABLE: SPRINT_CONTEXT ---
# Simulating the last 5 sprints
sprints_data = []
for i in range(1, 30):
    sprints_data.append({
        'sprint_id': i,
        'team_load_percentage': random.choice([80, 90, 100, 110]), # Overloaded or underloaded
        'is_holiday_season': 1 if i == 5 else 0 # Pretend Sprint 5 was during holidays
    })
df_sprints = pd.DataFrame(sprints_data)

# --- 3. TABLE: HISTORICAL_TASKS (With Failure Logic) ---
tasks_data = []
for i in range(1, 2001): 
    assigned_dev = random.choice(devs_data)
    sprint = random.choice(sprints_data)
    est_points = random.choice([1, 2, 3, 5, 8])
    
    # NEW ACCURACY LOGIC: Give every level a distinct "speed"
    multiplier = 1.0
    if assigned_dev['experience_level'] == 'Junior': 
        multiplier = 1.8   # Junior is slowest
    elif assigned_dev['experience_level'] == 'Mid': 
        multiplier = 1.3   # Mid is in between
    elif assigned_dev['experience_level'] == 'Senior': 
        multiplier = 0.9   # Senior is fastest (even faster than base)
    
    # Add fatigue if team is overloaded
    if sprint['team_load_percentage'] > 100: 
        multiplier *= 1.2
    
    # Calculate final hours with slight randomness
    actual_hrs = (est_points * 8) * multiplier + random.uniform(-2, 2)
    
    # Failure Logic
    expected_hours = est_points * 8
    is_failed = 1 if actual_hrs > (expected_hours * 1.25) else 0
    
    tasks_data.append({
        'task_id': i,
        'dev_id': assigned_dev['dev_id'],
        'sprint_id': sprint['sprint_id'],
        'category': assigned_dev['primary_skill'],
        'story_points': est_points,
        'actual_hours': round(actual_hrs, 2),
        'is_failed': is_failed 
    })
df_tasks = pd.DataFrame(tasks_data)

# --- 4. PUSHING TO MYSQL (Corrected Order) ---
try:
    # We must drop the "Child" table (tasks) first because it depends on the others
    # Then we drop and recreate the "Parent" tables (devs and sprints)
    
    print("⏳ Clearing and updating tables...")
    
    # Push Parents First
    df_devs.to_sql('developers', con=engine, if_exists='replace', index=False)
    print("Table 1: 'developers' updated.")
    
    df_sprints.to_sql('sprint_context', con=engine, if_exists='replace', index=False)
    print("Table 2: 'sprint_context' updated.")
    
    # Push Child Last
    df_tasks.to_sql('historical_tasks', con=engine, if_exists='replace', index=False)
    print("Table 3: 'historical_tasks' updated.")
    
    print("\n PHASE 1 COMPLETE! All 3 tables populated.")

except Exception as e:
    print(f" Error: {e}")