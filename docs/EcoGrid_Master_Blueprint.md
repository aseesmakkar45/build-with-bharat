# EcoGrid AI - Master Blueprint (Single Source of Truth)

## 1. Executive Summary & Core USPs
EcoGrid AI is an intelligent energy manager that predicts renewable generation and energy demand, optimizing batteries, flexible loads, and grid interaction to maximize renewable utilization while minimizing energy cost, peak demand, and carbon emissions.

**Core USPs:**
1.  **Proactive "What-If" Digital Twin:** Simulate infrastructure changes (e.g., adding solar panels) to forecast ROI and carbon reduction before physical deployment.
2.  **Explainable AI (XAI) Energy Copilot:** Translates complex mathematical optimization into plain-English justifications for non-technical facility managers.
3.  **Eco-Efficiency Score:** A gamified 0-100 score aggregating grid dependency, renewable usage, and peak reduction for at-a-glance system health.

---

## 2. System Architecture (The Stack)
A decoupled, microservices architecture designed for real-time processing and easy deployment.

*   **Data Simulator:** Python script acting as the physical campus (IoT proxy).
*   **Message Broker:** Eclipse Mosquitto (MQTT) for high-frequency pub/sub data streams.
*   **Database:** TimescaleDB (PostgreSQL optimized for time-series) for storing historical data and predictions.
*   **Backend / AI Engine:** FastAPI (Python) hosting REST endpoints, ML inference (XGBoost), and the Optimization solver (OR-Tools).
*   **Frontend Dashboard:** React.js with Tailwind CSS and Recharts for live visualizations.
*   **Hardware (Optional):** Arduino connected via USB Serial to act as a physical "flexible load" relay and interactive demand sensor.

---

## 3. Data Schema & Flow

### MQTT Topics
*   `ecogrid/campus/status` (Current real-time state)
*   `ecogrid/hardware/knob` (Arduino input)

### TimescaleDB Schema: `energy_log`
*   `timestamp` (TIMESTAMPTZ, Primary Key)
*   `solar_gen_kw` (FLOAT)
*   `demand_kw` (FLOAT)
*   `battery_soc_percent` (FLOAT)
*   `grid_import_kw` (FLOAT)
*   `grid_export_kw` (FLOAT)

---

## 4. AI Pipeline Specifications

### Agent 1: The Forecaster
*   **Model:** XGBoost Regressor (Train on simulated historical data).
*   **Inputs:** `hour_of_day`, `day_of_week`, `current_cloud_cover_percent`, `temp_celsius`.
*   **Output:** 24-hour array of predicted `solar_gen_kw` and `demand_kw`.

### Agent 2: The Optimizer
*   **Model:** Google OR-Tools (Linear Programming).
*   **Objective Function:** `Minimize (Grid_Import_kW * Grid_Price) + (Grid_Import_kW * Grid_Carbon_Intensity)`.
*   **Constraints:**
    *   `Battery_SoC >= 10%` and `<= 100%`.
    *   `Battery_Charge_Rate <= Max_Charge_kW`.
    *   `Demand_kW = Solar_Used_kW + Battery_Discharge_kW + Grid_Import_kW`.
*   **Output:** 24-hour array scheduling battery charging/discharging and grid import/export.

### Agent 3: The Copilot
*   **Model:** Groq API (Llama 3 8B) or OpenAI API (GPT-4o-mini).
*   **Prompt Architecture:** 
    ```
    You are the EcoGrid AI Copilot. 
    CURRENT STATE: {json_state}
    OPTIMIZATION DECISION: {optimization_result}
    USER QUESTION: {user_query}
    Explain why the optimization decision was made based on the current state in 2 clear sentences.
    ```

---

## 5. API Contracts (FastAPI)

*   `GET /api/v1/state/live`
    *   Returns the latest row from the `energy_log` table.
*   `GET /api/v1/predict`
    *   Triggers the XGBoost model and returns the 24-hour forecast array.
*   `POST /api/v1/optimize`
    *   Runs the OR-Tools solver based on the forecast and returns the scheduled actions.
*   `POST /api/v1/copilot/ask`
    *   Body: `{ "query": "string" }`
    *   Returns the natural language explanation from the LLM.

---

## 6. Hardware / Arduino Integration Plan
*   **Arduino Code (C++):** Reads an analog Potentiometer (A0) and maps the value (0-1023) to a demand spike (0-50kW). Listens for serial commands ('1' or '0') to turn an LED on/off.
*   **Python Serial Bridge:** Runs alongside the simulator. Uses `pyserial` to read the Arduino and inject the demand spike into the `simulator.py` logic. Reads optimization outputs from FastAPI and sends '1' (Turn On Load) or '0' (Turn Off Load) to the Arduino via USB.
