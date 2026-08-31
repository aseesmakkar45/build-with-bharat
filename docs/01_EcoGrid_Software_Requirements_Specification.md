# Software Requirements Specification (SRS)
**Project Name:** EcoGrid AI - Smart Campus Microgrid Platform
**Version:** 1.0

## 1. Introduction
### 1.1 Purpose
This document provides a comprehensive Software Requirements Specification (SRS) for EcoGrid AI. It details the functional and non-functional requirements necessary to build an AI-powered renewable energy management and optimization platform tailored for a smart campus microgrid.

### 1.2 Scope
EcoGrid AI will monitor real-time energy flow, forecast solar generation and building demand, and optimize the scheduling of battery storage and flexible loads (e.g., EV chargers) to minimize grid dependency and carbon emissions. 

## 2. Overall Description
### 2.1 User Characteristics (Personas)
*   **Facility Manager (Admin):** Requires deep technical visibility, the ability to override AI scheduling decisions, and access to the "What-If" digital twin for capital planning.
*   **Sustainability Officer (Viewer):** Requires access to high-level dashboards, the Eco-Efficiency score, and live carbon offset calculations.
*   **System Entity (IoT/Arduino):** Hardware endpoints that push telemetry data and execute physical load-shifting commands via MQTT/Serial.

### 2.2 Operating Environment
*   **Backend:** Python (FastAPI), Node.js (Optional WebSockets).
*   **Database:** TimescaleDB (PostgreSQL) for time-series telemetry.
*   **Frontend:** React.js, TailwindCSS, running on modern web browsers (Chrome/Firefox/Safari).
*   **Infrastructure:** Dockerized containers orchestrated via `docker-compose`.

## 3. Functional Requirements (FR)

### 3.1 Data Ingestion & Telemetry
*   **FR-1.1:** The system shall ingest IoT sensor data (Solar kW, Demand kW, Battery SoC) via an MQTT broker at a minimum frequency of 1 Hz.
*   **FR-1.2:** The system shall store telemetry data in a time-series database, indexed by timestamp.
*   **FR-1.3:** The system shall handle missing sensor data through linear interpolation preprocessing.

### 3.2 AI Forecasting Module
*   **FR-2.1:** The system shall generate a 24-hour forecast for Solar Generation (kW) every hour using historical data and weather API inputs.
*   **FR-2.2:** The system shall generate a 24-hour forecast for Campus Energy Demand (kW) every hour.

### 3.3 AI Optimization Engine
*   **FR-3.1:** The system shall execute a mathematical optimization solver (e.g., Linear Programming) based on the 24-hour forecasts.
*   **FR-3.2:** The system shall output an actionable schedule dictating Battery Charging/Discharging rates (kW) and Grid Import/Export rates (kW).
*   **FR-3.3:** The system shall automatically route commands to physical/simulated flexible loads (e.g., cutting EV charging during peak demand).

### 3.4 Dashboard and Visualization
*   **FR-4.1:** The system shall display a live energy flow diagram connecting Solar, Battery, Grid, and Demand nodes.
*   **FR-4.2:** The system shall calculate and display a live "Eco-Efficiency Score" (0-100).
*   **FR-4.3:** The system shall display the total carbon emissions avoided (in kg of CO2) based on real-time grid carbon intensity.

### 3.5 Explainable AI (XAI) Copilot
*   **FR-5.1:** The system shall expose a chat interface allowing users to query system decisions.
*   **FR-5.2:** The system shall generate natural language explanations for optimization decisions by passing system state and solver constraints to an LLM.

## 4. Non-Functional Requirements (NFR)

### 4.1 Performance Requirements
*   **NFR-1:** Dashboard telemetry widgets must update within 2 seconds of the sensor data arriving at the MQTT broker.
*   **NFR-2:** The Optimization Engine must compute the 24-hour dispatch schedule in under 10 seconds.

### 4.2 Scalability & Reliability
*   **NFR-3:** The architecture must decouple the high-frequency MQTT data ingestion from the REST API to prevent backend blocking.
*   **NFR-4:** The database must partition time-series data automatically (e.g., via TimescaleDB hypertables) to maintain sub-second query performance over 1 million+ rows.

### 4.3 Security
*   **NFR-5:** All REST API endpoints serving user data must require JWT (JSON Web Token) authentication.
*   **NFR-6:** IoT ingestion endpoints/brokers must require API keys or client certificates.
