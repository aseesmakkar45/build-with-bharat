from fastapi import FastAPI
import paho.mqtt.client as mqtt
import threading
import json
import os
import pickle
import pandas as pd
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
import numpy as np

# Import our Optimization Engine
import optimizer
from services.forecasting import solar_forecast, demand_forecast

app = FastAPI(title="EcoGrid AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state
latest_telemetry = {}

# AI Models are now loaded in their respective services in backend/services/forecasting/
# MQTT Setup
BROKER = os.getenv("MQTT_BROKER_URL", "test.mosquitto.org")
PORT = 1883
TOPIC = "ecogrid/telemetry/state"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"FastAPI connected to MQTT Broker ({BROKER})")
        client.subscribe(TOPIC)
    else:
        print(f"FastAPI failed to connect to MQTT, return code {rc}")

def on_message(client, userdata, msg):
    global latest_telemetry
    try:
        payload = json.loads(msg.payload.decode())
        latest_telemetry = payload
    except Exception as e:
        print(f"Error parsing MQTT message: {e}")

import random
def start_mqtt():
    client_id = f"EcoGrid_FastAPI_Backend_ML_{random.randint(1000, 9999)}"
    client = mqtt.Client(client_id=client_id)
    client.on_connect = on_connect
    client.on_message = on_message
    
    print("FastAPI connecting to MQTT broker...")
    client.connect(BROKER, PORT, 60)
    client.loop_forever()

# Start MQTT background thread
mqtt_thread = threading.Thread(target=start_mqtt, daemon=True)
mqtt_thread.start()

@app.get("/")
def read_root():
    return {"message": "Welcome to EcoGrid AI API (Phase 3 Active)"}

@app.get("/api/v1/state/live")
def get_live_state():
    if not latest_telemetry:
        return {"status": "waiting_for_data"}
    return latest_telemetry

@app.get("/api/v1/forecast")
def get_24h_forecast():
    """Uses the forecasting services to predict the next 24 hours."""
    forecasts = []
    current_time = datetime.now()
    
    for i in range(24):
        future_time = current_time + timedelta(hours=i)
        
        predicted_demand = demand_forecast.get_demand_prediction(future_time)
        predicted_solar = solar_forecast.get_solar_prediction(future_time)
        
        forecasts.append({
            "timestamp": future_time.isoformat(),
            "predicted_demand_kw": round(predicted_demand, 2),
            "predicted_solar_kw": round(predicted_solar, 2)
        })
        
    return {"forecast_24h": forecasts}

@app.get("/api/v1/optimize")
def get_optimization_schedule():
    """Generates 24h AI forecast and passes it to OR-Tools to solve battery dispatch."""
    # 1. Get the forecast
    forecast_response = get_24h_forecast()
    
    if "error" in forecast_response:
        return forecast_response
        
    forecast_data = forecast_response["forecast_24h"]
    
    # 2. Pass to OR-Tools Mathematical Solver
    optimal_schedule = optimizer.optimize_grid(forecast_data)
    
    # Publish actuator state to MQTT for Arduino (fire-and-forget)
    if optimal_schedule.get("status") == "OPTIMAL":
        def publish_action():
            try:
                current_ev_action = "EV_ON" if optimal_schedule["schedule"][0]["ev_kw"] > 0 else "EV_OFF"
                client = mqtt.Client(client_id=f"EcoGrid_Opt_{random.randint(1000, 9999)}")
                client.connect(BROKER, PORT, 5) # 5 second keepalive
                client.publish("ecogrid/telemetry/actuators", json.dumps({"command": current_ev_action}))
                client.disconnect()
            except Exception as e:
                print(f"Failed to publish actuator command: {e}")
                
        threading.Thread(target=publish_action, daemon=True).start()
            
    return optimal_schedule

from pydantic import BaseModel
class ChatRequest(BaseModel):
    message: str

import copilot

@app.post("/api/v1/chat")
def chat_with_copilot(req: ChatRequest):
    """Passes user chat message, schedule, and live telemetry to the LLM."""
    # Fetch the latest schedule to give context to the AI
    schedule_response = get_optimization_schedule()
    
    # Pass live telemetry to the AI as well
    global latest_telemetry
    live_state = latest_telemetry if latest_telemetry else {}
    
    if "error" in schedule_response:
        ai_response = copilot.ask_copilot(req.message, {}, live_state)
    else:
        ai_response = copilot.ask_copilot(req.message, schedule_response, live_state)
        
    return {"reply": ai_response}

# --- NEW ENDPOINTS (Modules 8, 10, 11) ---

@app.get("/api/v1/score")
def get_green_score():
    """Calculates Green Efficiency Score dynamically."""
    if not latest_telemetry:
        return {"score": 0, "components": {}}
    
    # Calculate based on live state for simple demo, 
    # ideally this uses 24h rolling averages
    solar = latest_telemetry.get("solar_kw", 0)
    grid = latest_telemetry.get("grid_import_kw", 0)
    total = solar + grid + 0.1
    ren_util = (solar / total) * 100.0
    
    return {
        "score": round(ren_util, 1),
        "components": {
            "renewable_utilization": round(ren_util, 1),
            "carbon_reduction": round(ren_util * 0.9, 1), # mock component for UX
            "grid_independence": round(ren_util * 0.95, 1) # mock component for UX
        }
    }

class SimControlRequest(BaseModel):
    device: str
    action: str

@app.post("/api/v1/simulation/control")
def control_simulation(req: SimControlRequest):
    """Overrides smart grid state (EV, HVAC, Pump). In a real app this publishes to MQTT."""
    # Since our state is maintained by simulator.py via MQTT, 
    # to actually change it we'd publish a command topic that simulator reads.
    # For now, we'll return success to let the frontend know the API exists.
    command = {"device": req.device, "action": req.action}
    
    client = mqtt.Client()
    client.connect(BROKER, PORT, 60)
    client.publish("ecogrid/telemetry/commands", json.dumps(command))
    client.disconnect()
    
@app.get("/api/v1/carbon")
def get_carbon_metrics():
    """Returns actual calculated carbon metrics."""
    if not latest_telemetry:
        return {"co2_emitted_kg": 0.0, "co2_avoided_kg": 0.0, "carbon_intensity": 0.0}
    
    grid = latest_telemetry.get("grid_import_kw", 0)
    solar_used = latest_telemetry.get("renewable_used_kw", 0)
    
    # 0.4 kg CO2 per kWh grid, solar displaces this
    emitted = round(grid * 0.4, 2)
    avoided = round(solar_used * 0.4, 2)
    intensity = round(emitted / max(0.1, grid + solar_used), 2)
    
    return {
        "co2_emitted_kg": emitted,
        "co2_avoided_kg": avoided,
        "carbon_intensity": intensity
    }

@app.get("/api/v1/alerts")
def get_dynamic_alerts():
    """Generates alerts based on current state and upcoming forecast."""
    alerts = []
    
    if latest_telemetry:
        soc = latest_telemetry.get("battery_soc_percent", 50)
        grid = latest_telemetry.get("grid_import_kw", 0)
        
        if grid > 100:
            alerts.append({"type": "WARNING", "msg": f"High grid import ({grid}kW). Recommend discharging battery."})
        if soc < 20:
            alerts.append({"type": "CRITICAL", "msg": "Battery SOC very low. Avoid non-essential flexible loads."})
            
    # Add an upcoming forecast alert
    try:
        current_time = datetime.now()
        next_hour = current_time + timedelta(hours=1)
        pred_solar = solar_forecast.get_solar_prediction(next_hour)
        pred_demand = demand_forecast.get_demand_prediction(next_hour)
        if pred_solar > pred_demand + 20:
            alerts.append({"type": "INFO", "msg": f"High solar surplus expected at {next_hour.hour}:00. Good time to charge EV."})
    except:
        pass
        
    return {"alerts": alerts}

@app.post("/api/v1/simulation/reset")
def reset_simulation():
    """Resets the demo simulation loop."""
    client = mqtt.Client()
    client.connect(BROKER, PORT, 60)
    client.publish("ecogrid/telemetry/commands", json.dumps({"action": "reset"}))
    client.disconnect()
    return {"status": "Simulation reset command sent."}

# --- NEW ENDPOINTS (Master Prompt Fulfillment) ---

@app.get("/api/v1/carbon/history")
def get_carbon_history():
    """Returns historical carbon metrics (mocked for demo)."""
    return [
        {"name": "Jan", "savings": 400},
        {"name": "Feb", "savings": 450},
        {"name": "Mar", "savings": 600},
        {"name": "Apr", "savings": 800},
        {"name": "May", "savings": 950},
        {"name": "Jun", "savings": 1100},
        {"name": "Jul", "savings": 1245},
    ]

@app.get("/api/v1/battery/state")
def get_battery_state():
    if not latest_telemetry:
        return {"soc": 0, "soh": 100, "capacity_kwh": 50, "current_power": 0, "status": "Idle"}
    
    soc = latest_telemetry.get("battery_soc_percent", 0)
    power = latest_telemetry.get("battery_power_kw", 0)
    
    status = "Idle"
    if power > 0:
        status = "Discharging"
    elif power < 0:
        status = "Charging"
        
    return {
        "soc": soc,
        "soh": 98,
        "capacity_kwh": 50,
        "current_power": abs(power),
        "status": status,
        "min_soc": 20,
        "max_soc": 95,
        "temperature": 24.5
    }

from fastapi import Query
import random

@app.get("/api/v1/energy/history")
def get_energy_history(time_range: str = Query("day", alias="range", description="Time range for historical data: day, week, month")):
    """Returns historical energy mix for the specified range."""
    history = []
    
    if time_range == "day":
        current_time = datetime.now() - timedelta(hours=24)
        for i in range(24):
            t = current_time + timedelta(hours=i)
            hour = t.hour
            solar = 0 if hour < 6 or hour > 18 else (12 - abs(12 - hour)) * 3.5
            demand = 30 + (10 if 8 <= hour <= 18 else 0) + (15 if 18 <= hour <= 22 else 0)
            history.append({
                "time": f"{hour:02d}:00",
                "solar": round(solar, 1),
                "demand": round(demand, 1),
                "grid": round(max(0, demand - solar), 1)
            })
    elif time_range == "week":
        # Generate 7 days of data (Daily totals in kWh)
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        current_dow = datetime.now().weekday()
        ordered_days = days[current_dow+1:] + days[:current_dow+1]
        
        for i, day in enumerate(ordered_days):
            # Weekends (Sat/Sun) have lower demand
            is_weekend = day in ["Sat", "Sun"]
            # Daily total solar energy (kWh): ~210 on average
            solar_kwh = 210 + random.uniform(-40, 50)
            # Daily total demand (kWh): ~960 on weekdays, ~700 on weekends
            demand_kwh = (700 if is_weekend else 960) + random.uniform(-50, 60)
            
            history.append({
                "time": day,
                "solar": round(solar_kwh, 1),
                "demand": round(demand_kwh, 1),
                "grid": round(max(0, demand_kwh - solar_kwh), 1)
            })
    elif time_range == "month":
        # Generate 30 days of data (Daily totals in kWh)
        for i in range(1, 31):
            is_weekend = (i % 7 == 6 or i % 7 == 0)
            solar_kwh = 210 + random.uniform(-60, 80) # higher variance across month
            demand_kwh = (700 if is_weekend else 960) + random.uniform(-60, 80)
            
            history.append({
                "time": f"Day {i}",
                "solar": round(solar_kwh, 1),
                "demand": round(demand_kwh, 1),
                "grid": round(max(0, demand_kwh - solar_kwh), 1)
            })
            
    return history

@app.get("/api/v1/cost/tariff")
def get_tariff():
    """Returns hourly tariff prices."""
    tariffs = []
    for hour in range(24):
        price = 15 if 18 <= hour <= 22 else (8 if 10 <= hour <= 16 else 10)
        tariffs.append({"hour": f"{hour:02d}:00", "price": price})
    return {"tariffs": tariffs, "current": 10, "currency": "₹"}

@app.get("/api/v1/devices")
def get_devices():
    """Returns device registry."""
    loads = latest_telemetry.get("loads", {}) if latest_telemetry else {}
    return [
        {"id": "hvac_1", "name": "Smart HVAC", "type": "HVAC", "location": "Campus Hall", "power_kw": 15.0, "status": loads.get("hvac", {}).get("status", "idle")},
        {"id": "ev_1", "name": "EV Chargers", "type": "EV", "location": "Parking Lot A", "power_kw": 22.0, "status": loads.get("ev", {}).get("status", "idle")},
        {"id": "pump_1", "name": "Irrigation Pump", "type": "Pump", "location": "Greenhouse", "power_kw": 5.0, "status": loads.get("water_pump", {}).get("status", "idle")},
        {"id": "server_1", "name": "Data Center", "type": "Server", "location": "IT Rack B", "power_kw": 8.0, "status": "running"}
    ]

# Simple in-memory settings for demo purposes
app_settings = {
    "facility_name": "EcoGrid Alpha Campus",
    "simulation_mode": True,
    "battery_capacity": 50,
    "battery_min_soc": 20,
    "battery_max_soc": 95,
    "cost_weight": 0.5,
    "carbon_weight": 0.5
}

@app.get("/api/v1/settings")
def get_settings():
    return app_settings

class SettingsUpdate(BaseModel):
    settings: dict

@app.post("/api/v1/settings")
def update_settings(req: SettingsUpdate):
    global app_settings
    app_settings.update(req.settings)
    return {"status": "success", "settings": app_settings}
