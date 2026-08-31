# AI & Machine Learning Strategy
**Project Name:** EcoGrid AI

EcoGrid AI applies AI strictly where it provides meaningful value, rather than relying on black-box neural networks for everything.

## 1. Agent 1: Anomaly Detection (Monitoring)
*   **Goal:** Identify unusual energy behavior (e.g., HVAC overload, equipment malfunction).
*   **Recommended Algorithm:** **Isolation Forest**.
    *   *Justification:* Isolation forests are incredibly efficient at identifying outliers in high-dimensional time-series data without needing massive amounts of labeled "failure" data.
*   **Inputs:** Current demand vs. historical moving averages for that specific time/day.

## 2. Agent 2: Energy Forecasting (Predictive)
*   **Goal:** Predict future electricity demand and solar generation 24 hours out.
*   **Demand Forecasting Inputs:** Historical consumption, time of day, day of week, temperature, occupancy status, holiday/weekend status.
*   **Solar Forecasting Inputs:** Historical generation, cloud cover, solar irradiance, temperature, weather conditions.
*   **Recommended Algorithms:** **XGBoost / Random Forest**.
    *   *Justification:* Provides the best balance between accuracy, training speed, explainability, and implementation effort for a hackathon. (LSTM-based time-series forecasting is noted as a future extension).

## 3. Agent 3: Energy Optimization
*   **Goal:** Determine the optimal energy allocation (Battery scheduling, Load scheduling, Grid interaction).
*   **Recommended Algorithm:** **Linear Programming (LP)** or Mixed Integer Linear Programming (MILP) using Google OR-Tools or PuLP.
*   **Objective Function:**
    *   *Minimize:* Electricity Cost + Carbon Emissions + Peak Demand + Battery Degradation Penalty + Unnecessary Grid Dependency.
    *   *Maximize:* Renewable Energy Utilization + Renewable Self-Consumption + Battery Efficiency + Energy Cost Savings.
*   **Constraints:** Maximum discharging rate, minimum battery SOC, energy demand requirements, flexible-load operating windows, grid import/export limits.

## 4. Agent 4: Carbon Agent (Analytics)
*   **Goal:** Calculate environmental impact.
*   **Logic:** `Grid Electricity Consumed × Grid Emission Factor`. This agent constantly updates the TimescaleDB with live avoided carbon metrics and aggregates the total system performance into the **Eco Efficiency Score** (0-100).

## 5. Agent 5: Recommendation Agent (AI Copilot)
*   **Goal:** Explain system decisions.
*   **Logic:** Receives the results of the Forecasting and Optimization engines and converts them into understandable recommendations.
    *   *Example Output:* “High solar generation is predicted between 11 AM and 2 PM. Schedule EV charging and water-pump operation during this period and reserve part of the battery capacity for the evening demand peak.”
*   **Recommended Implementation:** Generative AI (LLM) utilizing a strict prompt template that forces the LLM to only explain the provided JSON constraints.
