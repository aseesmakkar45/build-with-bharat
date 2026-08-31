import time
import json
import math
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
import os

# Configuration
BROKER = os.getenv("MQTT_BROKER_URL", "test.mosquitto.org")
PORT = 1883
TOPIC_STATE = "ecogrid/telemetry/state"
TOPIC_HARDWARE = "ecogrid/telemetry/hardware_sensors"

# Battery Constraints
BATTERY_CAPACITY = 500.0
MAX_CHARGE_RATE = 100.0
MAX_DISCHARGE_RATE = 100.0
EFFICIENCY = 0.95

# Flexible Load Configs
LOADS = {
    "ev": {"power": 50, "duration_hours": 3, "preferred_start": 18, "status": "idle"},
    "hvac": {"power": 30, "duration_hours": 24, "status": "running"},
    "water_pump": {"power": 20, "duration_hours": 2, "preferred_start": 17, "status": "idle"}
}

hardware_data = {"active": False, "solar_kw": 0, "demand_kw": 0, "last_seen": 0}

client = mqtt.Client(client_id="EcoGrid_Simulator")
def on_connect(client, userdata, flags, rc):
    print(f"Simulator connected to MQTT Broker ({BROKER})")
    client.subscribe(TOPIC_HARDWARE)

def on_message(client, userdata, msg):
    global hardware_data
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("hardware_active"):
            hardware_data["active"] = True
            hardware_data["solar_kw"] = payload["solar_kw"]
            hardware_data["demand_kw"] = payload["demand_kw"]
            hardware_data["last_seen"] = time.time()
    except:
        pass

client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_start()

battery_soc_kwh = 250.0  # start at 50%
sim_time = datetime.now()

try:
    print("Starting Deterministic 24h Data Simulation...")
    while True:
        # For demo purposes, we will advance simulation time quickly (1 hour per 5 seconds)
        # However, to allow POT/LDR interaction, we keep it stable unless fast-forwarded.
        # Let's just use real time for stability, but we can override this if needed.
        sim_time = datetime.now()
        
        hour = sim_time.hour + sim_time.minute / 60.0
        
        # 1. Deterministic Solar (Peak at 13:00)
        # Sine wave from 6 to 18
        if 6 <= hour <= 18:
            # 0 to 1 curve
            solar_curve = math.sin(math.pi * (hour - 6) / 12)
            solar_kw = max(0, 150.0 * solar_curve)
        else:
            solar_kw = 0.0
            
        # 2. Deterministic Demand
        # Base load
        demand_kw = 40.0
        # Morning peak (8-10)
        if 7 <= hour <= 11:
            demand_kw += 60.0 * math.sin(math.pi * (hour - 7) / 4)
        # Evening peak (17-21)
        if 17 <= hour <= 22:
            demand_kw += 80.0 * math.sin(math.pi * (hour - 17) / 5)
            
        # Hardware Override Logic
        hardware_mode_active = False
        if time.time() - hardware_data["last_seen"] < 5.0: # 5 second timeout
            solar_kw = hardware_data["solar_kw"]
            demand_kw = hardware_data["demand_kw"]
            hardware_mode_active = True
            
        # Add flexible loads (default behavior without optimization)
        # EV charges at 18:00
        if 18 <= hour <= 21:
            LOADS["ev"]["status"] = "running"
            demand_kw += LOADS["ev"]["power"]
        else:
            LOADS["ev"]["status"] = "idle"
            
        # Water pump at 17:00
        if 17 <= hour <= 19:
            LOADS["water_pump"]["status"] = "running"
            demand_kw += LOADS["water_pump"]["power"]
        else:
            LOADS["water_pump"]["status"] = "idle"

        # HVAC is always running but varied by temp
        demand_kw += LOADS["hvac"]["power"] * (1.0 + 0.3 * math.sin(math.pi * (hour-6)/12 if 6<=hour<=18 else 0))

        # 3. Basic Rule-Based Energy Balance (Fall-back if no optimizer)
        battery_charge_kw = 0.0
        battery_discharge_kw = 0.0
        grid_import_kw = 0.0
        grid_export_kw = 0.0
        renewable_used_kw = 0.0
        renewable_curtailed_kw = 0.0

        if solar_kw >= demand_kw:
            renewable_used_kw = demand_kw
            surplus = solar_kw - demand_kw
            # Try to charge battery
            chargeable = min(surplus, MAX_CHARGE_RATE)
            if battery_soc_kwh + chargeable <= BATTERY_CAPACITY:
                battery_charge_kw = chargeable
                surplus -= chargeable
                battery_soc_kwh += chargeable * EFFICIENCY
            # Export rest
            grid_export_kw = surplus
            renewable_curtailed_kw = 0  # In a grid-tied system, we export, not curtail
        else:
            renewable_used_kw = solar_kw
            deficit = demand_kw - solar_kw
            # Try to discharge battery
            dischargeable = min(deficit, MAX_DISCHARGE_RATE)
            if battery_soc_kwh - dischargeable >= 0:
                battery_discharge_kw = dischargeable
                deficit -= dischargeable
                battery_soc_kwh -= dischargeable / EFFICIENCY
            # Import rest
            grid_import_kw = deficit

        battery_soc_percent = (battery_soc_kwh / BATTERY_CAPACITY) * 100.0

        # Construct Unified State
        state = {
            "timestamp": sim_time.isoformat(),
            "mode": "hardware" if hardware_mode_active else "simulation",
            "solar_kw": round(solar_kw, 2),
            "demand_kw": round(demand_kw, 2),
            "battery_soc_percent": round(battery_soc_percent, 2),
            "battery_soc_kwh": round(battery_soc_kwh, 2),
            "battery_charge_kw": round(battery_charge_kw, 2),
            "battery_discharge_kw": round(battery_discharge_kw, 2),
            "grid_import_kw": round(grid_import_kw, 2),
            "grid_export_kw": round(grid_export_kw, 2),
            "renewable_used_kw": round(renewable_used_kw, 2),
            "renewable_curtailed_kw": round(renewable_curtailed_kw, 2),
            "loads": LOADS
        }
        
        client.publish(TOPIC_STATE, json.dumps(state), retain=True)
        print(f"[{state['timestamp']}] Sim State: Solar={state['solar_kw']}kW | Demand={state['demand_kw']}kW | SOC={state['battery_soc_percent']}% | Grid={state['grid_import_kw']}kW")
        
        time.sleep(2)

except KeyboardInterrupt:
    print("Stopping simulator...")
    client.loop_stop()
    client.disconnect()
