from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. LAT/LNG DICTIONARY
LOCATION_MAPPING = {
    "Shivajinagar": {"lat": 18.5302, "lng": 73.8523, "type": "hub"},
    "Kothrud": {"lat": 18.5020, "lng": 73.8150, "type": "hub"},
    "Hadapsar": {"lat": 18.4967, "lng": 73.9417, "type": "hub"},
    "Baner": {"lat": 18.5590, "lng": 73.7868, "type": "hub"},
    "Swargate": {"lat": 18.4996, "lng": 73.8586, "type": "hub"},
    "Wakad": {"lat": 18.5987, "lng": 73.7688, "type": "hub"},
    "Warje": {"lat": 18.4834, "lng": 73.7958, "type": "regional"},
    "Wagholi": {"lat": 18.5794, "lng": 73.9806, "type": "regional"},
    "Lonikand": {"lat": 18.6360, "lng": 74.0110, "type": "regional"},
    "Manjari": {"lat": 18.4981, "lng": 73.9880, "type": "regional"},
    "Velhe Village": {"lat": 18.2917, "lng": 73.6267, "type": "regional"},
    "Baramati": {"lat": 18.1520, "lng": 74.5760, "type": "regional"},
    "Lonavala": {"lat": 18.7480, "lng": 73.4071, "type": "regional"},
    "Junnar": {"lat": 19.2025, "lng": 73.8761, "type": "regional"},
    "Shirur": {"lat": 18.8267, "lng": 74.3753, "type": "regional"}
}

def get_location_data(town_name):
    if town_name in LOCATION_MAPPING:
        return LOCATION_MAPPING[town_name]
    return {
        "lat": 18.5204 + random.uniform(-0.4, 0.4),
        "lng": 73.8567 + random.uniform(-0.4, 0.4),
        "type": "regional"
    }

# 2. LOAD CSV DATA
try:
    df = pd.read_csv("pune_predictive_city_pulse_dataset.csv")
    df = df.sort_values(by="Timestamp", ascending=False)
    latest_df = df.drop_duplicates(subset="Town/Ward/Village", keep="first")
    print(f"✅ Successfully loaded {len(latest_df)} unique locations from CSV.")
except Exception as e:
    print("❌ Error loading CSV:", e)
    latest_df = pd.DataFrame()

# 3. AI LOGIC & UI HELPERS
def determine_color(score):
    if score < 50: return "#00ff00" # Green
    if score < 80: return "orange"  # Orange
    return "red"                    # Red

def generate_issue_text(feature, score):
    """Auto-generates contextual status text based on feature and score."""
    if feature == "traffic":
        if score < 50: return "Clear roads. Smooth traffic flow."
        if score < 80: return "Moderate congestion. Expect slight delays."
        return "Severe gridlock detected. Recommend alternative routing."
    
    elif feature == "flood":
        if score < 50: return "Dry conditions. No waterlogging detected."
        if score < 80: return "Minor water accumulation. Drive carefully."
        return "Critical flood risk. Avoid area immediately."
    
    elif feature == "garbage":
        if score < 50: return "Clean area. Bins have ample capacity."
        if score < 80: return "Bins filling up. Scheduled pickup recommended."
        return "Waste bins exceeding max capacity. High sanitation risk."
    
    elif feature == "crowd":
        if score < 50: return "Optimal crowd levels. Area is clear."
        if score < 80: return "Busy area. Moderate footfall."
        return "Dangerous crowd density. Not recommended to go out in this location."
    
    else: # Fallback
        if score < 50: return "All systems nominal. Area is optimal."
        if score < 80: return "Elevated activity detected. Monitor conditions."
        return "Critical anomaly detected."

# 4. API ENDPOINT
@app.get("/api/data")
def get_city_data(
    mode: str = Query("current"),
    feature: str = Query("all")
):
    response_data = []

    if latest_df.empty:
        return {"status": "error", "message": "CSV data not loaded"}

    for _, row in latest_df.iterrows():
        town = row["Town/Ward/Village"]
        loc_data = get_location_data(town)
        
        if mode == "current":
            state_data = {
                "traffic": row["Traffic_Now(0-100)"],
                "flood": row["Flood_Now(0-100)"],
                "garbage": row["Garbage_Fill_Now(%)"],
                "crowd": min((row["Crowd_Count_Now"] / 50000.0) * 100, 100) 
            }
        else:
            state_data = {
                "traffic": row["Traffic_Pred_30min(0-100)"],
                "flood": row["Flood_Pred_30min(0-100)"],
                "garbage": row["Garbage_Pred_30min(%)"],
                "crowd": min((row["Crowd_Pred_30min"] / 50000.0) * 100, 100)
            }

        if feature == "all" and loc_data["type"] == "regional":
            continue

        if feature == "all":
            max_risk = max(state_data.values())
            color = determine_color(max_risk)
            
            # Find the exact feature causing the highest risk to give accurate commentary
            primary_feature = "all"
            for f_key, f_val in state_data.items():
                if f_val == max_risk:
                    primary_feature = f_key
                    break
                    
            status_message = generate_issue_text(primary_feature, max_risk)

            response_data.append({
                "name": town, "lat": loc_data["lat"], "lng": loc_data["lng"],
                "risk": round(max_risk), "color": color, "issue": status_message
            })
            
        elif feature in state_data:
            risk_score = state_data[feature]
            color = determine_color(risk_score)
            status_message = generate_issue_text(feature, risk_score)
                
            response_data.append({
                "name": town, "lat": loc_data["lat"], "lng": loc_data["lng"],
                "risk": round(risk_score), "color": color, "issue": status_message
            })

    return {
        "status": mode,
        "feature": feature,
        "zones": response_data
    }