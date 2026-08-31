import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

t0 = time.time()
from services.forecasting import solar_forecast
from datetime import datetime
print(f"Import time: {time.time() - t0:.2f}s")

print("Calling get_solar_prediction 24 times...")
t1 = time.time()
for i in range(24):
    solar_forecast.get_solar_prediction(datetime.now())
print(f"Prediction loop time: {time.time() - t1:.2f}s")
