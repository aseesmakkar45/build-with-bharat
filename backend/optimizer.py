from ortools.linear_solver import pywraplp
from datetime import datetime
import dateutil.parser
import json

# Constraints Configuration
BATTERY_CAPACITY = 500.0       # kWh
MAX_CHARGE_RATE = 100.0        # kW per hour
MAX_DISCHARGE_RATE = 100.0
INITIAL_SOC = 250.0            # Start at 50% capacity
EFFICIENCY = 0.95
PEAK_PRICE = 0.25              # $0.25/kWh
OFF_PEAK_PRICE = 0.10          # $0.10/kWh
SELL_PRICE = 0.05              # $0.05/kWh sold back to grid
EMISSION_FACTOR = 0.4          # kg CO2 per kWh imported

def get_price_for_hour(hour: int):
    if 17 <= hour <= 21: # Evening Peak
        return PEAK_PRICE
    return OFF_PEAK_PRICE

def optimize_grid(forecast_data):
    """
    Takes 24-hour prediction array and returns optimal dispatch schedule.
    Also calculates the 'before optimization' baseline.
    """
    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver:
        return {"error": "OR-Tools solver unavailable."}

    num_hours = len(forecast_data)
    
    # 1. Calculate Scenario A: Baseline (No Battery, Default EV at 18:00)
    baseline = {
        "grid_import_kwh": 0.0,
        "grid_export_kwh": 0.0,
        "cost_dollars": 0.0,
        "co2_emissions_kg": 0.0,
        "renewable_utilized_kwh": 0.0
    }
    
    for t in range(num_hours):
        dt = dateutil.parser.parse(forecast_data[t]['timestamp'])
        h = dt.hour
        demand = forecast_data[t]['predicted_demand_kw']
        solar = forecast_data[t]['predicted_solar_kw']
        
        # Default EV behavior: charges from 18 to 20 (3 hours) at 50kW
        ev_load = 50.0 if 18 <= h <= 20 else 0.0
        total_demand = demand + ev_load
        
        if solar >= total_demand:
            baseline["renewable_utilized_kwh"] += total_demand
            export = solar - total_demand
            baseline["grid_export_kwh"] += export
            baseline["cost_dollars"] -= export * SELL_PRICE
        else:
            baseline["renewable_utilized_kwh"] += solar
            imp = total_demand - solar
            baseline["grid_import_kwh"] += imp
            baseline["cost_dollars"] += imp * get_price_for_hour(h)
            baseline["co2_emissions_kg"] += imp * EMISSION_FACTOR
            
    # 2. Optimization Variables
    battery_charge = []
    battery_discharge = []
    grid_import = []
    grid_export = []
    soc = []
    ev_active = [] # Binary-like (0 to 1) for GLOP, representing portion of EV charging in hour t
    
    for t in range(num_hours):
        battery_charge.append(solver.NumVar(0.0, MAX_CHARGE_RATE, f'charge_{t}'))
        battery_discharge.append(solver.NumVar(0.0, MAX_DISCHARGE_RATE, f'discharge_{t}'))
        grid_import.append(solver.NumVar(0.0, solver.infinity(), f'import_{t}'))
        grid_export.append(solver.NumVar(0.0, solver.infinity(), f'export_{t}'))
        soc.append(solver.NumVar(0.0, BATTERY_CAPACITY, f'soc_{t}'))
        # EV variable: max 1.0 (means fully running at 50kW for this hour)
        ev_active.append(solver.NumVar(0.0, 1.0, f'ev_{t}'))

    # 3. Constraints
    ev_total_hours = 3.0
    solver.Add(sum(ev_active) == ev_total_hours) # EV must run for exactly 3 hours total
    
    for t in range(num_hours):
        dt = dateutil.parser.parse(forecast_data[t]['timestamp'])
        h = dt.hour
        
        demand = forecast_data[t]['predicted_demand_kw']
        solar = forecast_data[t]['predicted_solar_kw']
        ev_kw = ev_active[t] * 50.0 # 50kW load
        
        # Energy Balance
        solver.Add(solar + grid_import[t] + battery_discharge[t] == 
                   demand + ev_kw + grid_export[t] + battery_charge[t])
        
        # SOC Evolution
        if t == 0:
            solver.Add(soc[t] == INITIAL_SOC + (battery_charge[t] * EFFICIENCY) - (battery_discharge[t] / EFFICIENCY))
        else:
            solver.Add(soc[t] == soc[t-1] + (battery_charge[t] * EFFICIENCY) - (battery_discharge[t] / EFFICIENCY))
            
        # EV window constraint: only allowed to charge between 08:00 and 22:00
        if not (8 <= h <= 22):
            solver.Add(ev_active[t] == 0)

    # 4. Objective: Minimize Cost
    objective = solver.Objective()
    for t in range(num_hours):
        dt = dateutil.parser.parse(forecast_data[t]['timestamp'])
        buy_price = get_price_for_hour(dt.hour)
        objective.SetCoefficient(grid_import[t], buy_price)
        objective.SetCoefficient(grid_export[t], -SELL_PRICE)
    objective.SetMinimization()

    # 5. Solve
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        schedule = []
        optimized_metrics = {
            "grid_import_kwh": 0.0,
            "grid_export_kwh": 0.0,
            "cost_dollars": round(objective.Value(), 2),
            "co2_emissions_kg": 0.0,
            "renewable_utilized_kwh": 0.0
        }
        
        # Detect AI reasoning based on EV shift
        ev_shifted = False
        ev_optimal_start = -1
        
        for t in range(num_hours):
            dt = dateutil.parser.parse(forecast_data[t]['timestamp'])
            imp = grid_import[t].solution_value()
            exp = grid_export[t].solution_value()
            ev_val = ev_active[t].solution_value()
            
            optimized_metrics["grid_import_kwh"] += imp
            optimized_metrics["grid_export_kwh"] += exp
            optimized_metrics["co2_emissions_kg"] += imp * EMISSION_FACTOR
            
            # Simple assumption: solar not exported is utilized
            optimized_metrics["renewable_utilized_kwh"] += forecast_data[t]['predicted_solar_kw'] - exp
            
            if ev_val > 0.5 and ev_optimal_start == -1:
                ev_optimal_start = dt.hour
                
            charge_val = battery_charge[t].solution_value()
            discharge_val = battery_discharge[t].solution_value()
            
            action = "IDLE"
            if charge_val > 5:
                action = "CHARGE"
            elif discharge_val > 5:
                action = "DISCHARGE"
                
            schedule.append({
                "timestamp": forecast_data[t]['timestamp'],
                "demand_kw": forecast_data[t]['predicted_demand_kw'],
                "solar_kw": forecast_data[t]['predicted_solar_kw'],
                "action": action,
                "battery_charge_kw": round(charge_val, 2),
                "battery_discharge_kw": round(discharge_val, 2),
                "grid_import_kw": round(imp, 2),
                "grid_export_kw": round(exp, 2),
                "ev_kw": round(ev_val * 50.0, 2),
                "soc_kwh": round(soc[t].solution_value(), 2)
            })
            
        reason = f"Battery optimized for peak prices. EV charging scheduled for optimal solar availability."
        if ev_optimal_start != -1 and ev_optimal_start != 18:
            reason = f"Shifted EV charging from 18:00 to {ev_optimal_start}:00 to maximize solar usage and reduce peak demand."

        # Round all metrics
        for k in baseline: baseline[k] = round(baseline[k], 2)
        for k in optimized_metrics: optimized_metrics[k] = round(optimized_metrics[k], 2)

        return {
            "status": "OPTIMAL",
            "reason": reason,
            "baseline": baseline,
            "optimized": optimized_metrics,
            "schedule": schedule
        }
    else:
        return {"status": "FAILED", "reason": "Could not find mathematical solution."}
