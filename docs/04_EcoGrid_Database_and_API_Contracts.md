# Database & API Contracts
**Project Name:** EcoGrid AI

## 1. Database Schema (TimescaleDB / PostgreSQL)

### Table: `energy_log`
This is a hypertable optimized for time-series data insertion and querying.

```sql
CREATE TABLE energy_log (
    time TIMESTAMPTZ NOT NULL,
    solar_gen_kw DOUBLE PRECISION NOT NULL,
    demand_kw DOUBLE PRECISION NOT NULL,
    battery_soc_percent DOUBLE PRECISION NOT NULL,
    grid_import_kw DOUBLE PRECISION NOT NULL,
    grid_export_kw DOUBLE PRECISION NOT NULL,
    carbon_intensity_gco2_kwh DOUBLE PRECISION
);

-- Convert to TimescaleDB Hypertable partitioned by 1 day chunks
SELECT create_hypertable('energy_log', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_energy_log_time ON energy_log (time DESC);
```

## 2. MQTT Topic Structure
The Mosquitto broker handles high-frequency data streams.
*   **Topic:** `ecogrid/campus/live`
*   **Payload (JSON):**
    ```json
    {
      "timestamp": "2024-05-20T14:30:00Z",
      "solar_gen_kw": 85.5,
      "demand_kw": 42.1,
      "battery_soc_percent": 78.0
    }
    ```
*   **Topic:** `ecogrid/hardware/actuator` (Used by Python to send commands to Arduino)
    *   Payload: `{"relay_state": 1}`

## 3. REST API Contracts (FastAPI)

### 3.1 Get Live Status
*   **Endpoint:** `GET /api/v1/state/live`
*   **Description:** Fetches the most recent row from the `energy_log` table.
*   **Response (200 OK):**
    ```json
    {
      "status": "success",
      "data": {
        "timestamp": "2024-05-20T14:30:00Z",
        "solar_gen_kw": 85.5,
        "demand_kw": 42.1,
        "battery_soc_percent": 78.0,
        "grid_import_kw": 0.0,
        "grid_export_kw": 43.4,
        "eco_score": 92
      }
    }
    ```

### 3.2 Trigger Forecast
*   **Endpoint:** `GET /api/v1/predict`
*   **Description:** Triggers the XGBoost models to predict the next 24 hours.
*   **Response (200 OK):**
    ```json
    {
      "status": "success",
      "forecast_horizon_hours": 24,
      "predictions": [
        {"time": "15:00", "pred_solar_kw": 80.0, "pred_demand_kw": 45.0},
        {"time": "16:00", "pred_solar_kw": 60.0, "pred_demand_kw": 50.0}
        // ... (up to 24 steps)
      ]
    }
    ```

### 3.3 Trigger Optimization
*   **Endpoint:** `POST /api/v1/optimize`
*   **Description:** Runs OR-Tools based on the latest forecast.
*   **Response (200 OK):**
    ```json
    {
      "status": "success",
      "schedule": [
        {"time": "15:00", "action": "CHARGE_BATTERY", "amount_kw": 35.0},
        {"time": "16:00", "action": "SHIFT_LOAD", "amount_kw": -10.0}
      ]
    }
    ```

### 3.4 AI Copilot Query
*   **Endpoint:** `POST /api/v1/copilot/ask`
*   **Request Body:**
    ```json
    {
      "query": "Why did the system export power to the grid at 2 PM?"
    }
    ```
*   **Response (200 OK):**
    ```json
    {
      "status": "success",
      "explanation": "At 2 PM, the battery was at 100% capacity and solar generation exceeded campus demand by 43kW. To prevent wasting this surplus, the system automatically exported it to the grid."
    }
    ```
