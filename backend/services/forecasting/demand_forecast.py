import os
import pickle
import pandas as pd
import numpy as np
from datetime import datetime

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
demand_model = None

try:
    with open(os.path.join(MODELS_DIR, "demand_model.pkl"), "rb") as f:
        demand_model = pickle.load(f)
except Exception as e:
    print(f"Warning: Could not load demand_model.pkl: {e}")

def get_demand_prediction(future_time: datetime) -> float:
    """Predicts campus demand for a given future hour."""
    hour = future_time.hour
    dayofweek = future_time.weekday()
    month = future_time.month
    is_weekend = 1 if dayofweek >= 5 else 0
    
    if demand_model is None:
        # Fallback math if model fails
        base = 40.0
        if 7 <= hour <= 11: base += 60.0 * np.sin(np.pi * (hour - 7) / 4)
        if 17 <= hour <= 22: base += 80.0 * np.sin(np.pi * (hour - 17) / 5)
        return base

    demand_features = pd.DataFrame([{
        'hour': hour,
        'dayofweek': dayofweek,
        'month': month,
        'is_weekend': is_weekend
    }])
    
    predicted_demand = demand_model.predict(demand_features)[0]
    # Scale to Microgrid level (kW instead of Grid MW)
    return max(0, float(predicted_demand) / 200.0)
