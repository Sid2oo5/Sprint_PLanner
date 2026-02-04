import joblib
import pandas as pd
from sqlalchemy import create_engine
import os
import urllib.parse
from dotenv import load_dotenv

# --- 0. DB CONNECTION ---
load_dotenv()
user = os.getenv("DB_USER", "root")
raw_password = os.getenv("DB_PASSWORD") 
host = os.getenv("DB_HOST", "localhost")
db = os.getenv("DB_NAME", "smart_planner")

password = urllib.parse.quote_plus(raw_password)
engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}/{db}")

# 1. Load the "Brains"
time_model = joblib.load('time_model.pkl')
risk_model = joblib.load('risk_model.pkl')

print("🏢 AI Project Consultant - Enterprise Mode")

# --- 2. GET USER INPUTS (Crucial Fix) ---
pts = int(input("\nEnter Story Points (1, 2, 3, 5, 8): "))
load = int(input("Enter Current Team Load % (e.g., 100): "))
deadline = float(input("Enter Your Max Allowed Hours (Deadline): "))

levels = {1: "Junior", 2: "Mid", 3: "Senior"}
analysis_results = []

print("\n--- 🔍 AI Level Analysis ---")

# --- 3. THE ANALYSIS LOOP ---
for val, name in levels.items():
    # Prepare features for prediction
    feat = pd.DataFrame([[pts, val, load]], 
                        columns=['story_points', 'experience_level', 'team_load_percentage'])
    
    est_time = time_model.predict(feat)[0]
    risk_prob = risk_model.predict_proba(feat)[0][1] * 100
    
    # Logic for Status
    ai_status = "✅ RELIABLE" if risk_prob < 30 else "⚠️ UNRELIABLE"
    user_status = "✅ ON-TIME" if est_time <= deadline else "❌ TOO SLOW"
    
    analysis_results.append({
        "level_val": val,
        "name": name,
        "time": est_time,
        "risk": risk_prob,
        "ai_status": ai_status,
        "user_status": user_status
    })
    
    print(f"{name:7} | Time: {est_time:4.1f}h | Risk: {risk_prob:4.1f}% | AI: {ai_status}")

# --- 4. FETCH REAL NAMES FUNCTION ---
def get_available_devs(level_name):
    """Fetch 3 real names from DB based on AI recommended level"""
    query = f"SELECT name FROM developers WHERE experience_level = '{level_name}' LIMIT 10"
    try:
        devs = pd.read_sql(query, con=engine)
        return devs['name'].tolist()
    except Exception as e:
        print(f"DB Error: {e}")
        return []

print("\n" + "="*60)

# --- 🎯 RECOMMENDATION 1: AI STANDARDS ---
ai_safe_list = [opt for opt in analysis_results if opt['ai_status'] == "✅ RELIABLE"]
print("🤖 [AI STANDARD RECOMMENDATION]")
if ai_safe_list:
    best_ai = sorted(ai_safe_list, key=lambda x: x['risk'])[0]
    names = get_available_devs(best_ai['name'])
    
    print(f"Recommended Level: **{best_ai['name']}**")
    print(f"Available Professionals: {', '.join(names) if names else 'None in DB'}")
    print(f"Reason: Lowest historical risk ({best_ai['risk']:.1f}%).")
else:
    print("Winner: NONE (AI predicts high failure risk for all levels on this task)")

print("-" * 30)

# --- 🎯 RECOMMENDATION 2: USER DEADLINE ---
user_valid_list = [opt for opt in analysis_results if opt['user_status'] == "✅ ON-TIME"]
print("⏱️ [USER DEADLINE RECOMMENDATION]")
if user_valid_list:
    # Pick lowest level that meets deadline (cost efficiency)
    best_user = sorted(user_valid_list, key=lambda x: x['level_val'])[0]
    names = get_available_devs(best_user['name'])
    
    print(f"Recommended Level: **{best_user['name']}**")
    print(f"Available Professionals: {', '.join(names) if names else 'None in DB'}")
    print(f"Reason: Meets your {deadline}h deadline while optimizing resources.")
else:
    print(f"Winner: NONE (No one is predicted to finish under your {deadline}h deadline)")

print("="*60)