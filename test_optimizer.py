import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from main import get_24h_forecast
import optimizer

forecast = get_24h_forecast()["forecast_24h"]
print("Forecast generated. Calling optimizer...")
res = optimizer.optimize_grid(forecast)
print("Optimizer status:", res["status"])
