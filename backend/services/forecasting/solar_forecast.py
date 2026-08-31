import os
import pickle
import pandas as pd
import numpy as np
from datetime import datetime

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
solar_model = None

try:
    with open(os.path.join(MODELS_DIR, "solar_model.pkl"), "rb") as f:
        solar_model = pickle.load(f)
except Exception as e:
    print(f"Warning: Could not load solar_model.pkl: {e}")

def get_solar_prediction(future_time: datetime) -> float:
    """Predicts solar output for a given future hour."""
    hour = future_time.hour
    month = future_time.month
    
    # Simulate a typical weather curve for the hackathon
    ambient_temp = 20.0 + (10.0 * np.sin(np.pi * (hour - 6) / 12)) if 6 <= hour <= 18 else 18.0
    irradiation = max(0, 1.0 * np.sin(np.pi * (hour - 6) / 12)) if 6 <= hour <= 18 else 0.0
    
    if solar_model is None:
        # Fallback deterministic math if model fails
        return max(0, 150.0 * np.sin(np.pi * (hour - 6) / 12)) if 6 <= hour <= 18 else 0.0

    solar_features = pd.DataFrame([{
        'hour': hour,
        'month': month,
        'AMBIENT_TEMPERATURE': ambient_temp,
        'IRRADIATION': irradiation
    }])
    
    predicted_solar = solar_model.predict(solar_features)[0]
    # Scale to Microgrid level (~150 kW peak)
    return max(0, float(predicted_solar) / 20.0)
