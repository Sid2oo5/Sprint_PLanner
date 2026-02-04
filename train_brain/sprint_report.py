import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
import os
import urllib.parse
from dotenv import load_dotenv

# --- 1. SECURE CONNECTION ---
load_dotenv()
user = os.getenv("DB_USER")
password = urllib.parse.quote_plus(os.getenv("DB_PASSWORD"))
host = os.getenv("DB_HOST")
db = os.getenv("DB_NAME")

engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}/{db}")

# --- 2. FETCH DATA ---
query = """
    SELECT s.assigned_to, s.predicted_hours, d.experience_level 
    FROM sprint_table s
    JOIN developers d ON s.assigned_to = d.name
    WHERE s.status = 'Assigned'
"""
df = pd.read_sql(query, con=engine)

# --- 3. AGGREGATE WORKLOAD ---
# Calculate total hours assigned to each person
workload = df.groupby(['assigned_to', 'experience_level'])['predicted_hours'].sum().reset_index()

# Define Capacity (Standard 40-hour week)
CAPACITY = 40.0
workload['utilization_%'] = (workload['predicted_hours'] / CAPACITY) * 100

print("\n--- 📈 Quick Stats ---")
print(f"Total Developers Assigned: {workload['assigned_to'].nunique()}")
print(f"Average Utilization: {workload['utilization_%'].mean():.1f}%")

# --- 4. VISUALIZATION ---
plt.figure(figsize=(14, 7))
sns.set_theme(style="whitegrid")

# Create a Bar Chart showing top 20 most loaded developers
top_loaded = workload.sort_values(by='predicted_hours', ascending=False).head(20)

sns.barplot(
    data=top_loaded, 
    x='assigned_to', 
    y='predicted_hours', 
    hue='experience_level',
    palette='magma'
)

# Add a "Red Line" for the 40-hour capacity limit
plt.axhline(y=CAPACITY, color='red', linestyle='--', label='Max Capacity (40h)')

plt.title('Top 20 Developer Workloads (Sprint Phase 1)', fontsize=16)
plt.xticks(rotation=45)
plt.ylabel('Total Predicted Hours')
plt.xlabel('Developer Name')
plt.legend()

plt.tight_layout()
plt.show()