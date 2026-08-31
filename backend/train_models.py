import pandas as pd
import xgboost as xgb
import os
import pickle

# Configuration
DATA_DIR = "data"
MODELS_DIR = "models"
DEMAND_CSV = "PJME_hourly.csv"
SOLAR_CSV = "Plant_1_Generation_Data.csv"
WEATHER_CSV = "Plant_1_Weather_Sensor_Data.csv"

def train_demand_model():
    demand_path = os.path.join(DATA_DIR, DEMAND_CSV)
    if not os.path.exists(demand_path):
        print(f"File not found: {demand_path}")
        return
    
    print("Training Demand Model on PJME_hourly.csv...")
    df = pd.read_csv(demand_path)
    
    # Preprocessing
    df['Datetime'] = pd.to_datetime(df['Datetime'])
    df = df.sort_values('Datetime')
    
    # Feature Engineering
    df['hour'] = df['Datetime'].dt.hour
    df['dayofweek'] = df['Datetime'].dt.dayofweek
    df['month'] = df['Datetime'].dt.month
    df['is_weekend'] = df['dayofweek'].apply(lambda x: 1 if x >= 5 else 0)
    
    # Define Features (X) and Target (y)
    X = df[['hour', 'dayofweek', 'month', 'is_weekend']]
    y = df['PJME_MW']
    
    # Train Model
    print("Fitting XGBoost Demand Regressor...")
    model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.1, max_depth=5)
    model.fit(X, y)
    
    model_path = os.path.join(MODELS_DIR, "demand_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"Saved Demand Model: {model_path}")

def train_solar_model():
    solar_path = os.path.join(DATA_DIR, SOLAR_CSV)
    weather_path = os.path.join(DATA_DIR, WEATHER_CSV)
    
    if not os.path.exists(solar_path) or not os.path.exists(weather_path):
        print("Solar or Weather dataset not found!")
        return
    
    print("Training Solar Model...")
    df_solar = pd.read_csv(solar_path)
    df_weather = pd.read_csv(weather_path)
    
    # Preprocessing (The Kaggle dataset uses 'dd-mm-yyyy HH:MM' or similar, pandas can usually infer)
    df_solar['DATE_TIME'] = pd.to_datetime(df_solar['DATE_TIME'], format="mixed")
    df_weather['DATE_TIME'] = pd.to_datetime(df_weather['DATE_TIME'], format="mixed")
    
    # Merge on DATE_TIME and PLANT_ID
    df = pd.merge(df_solar, df_weather, on=['DATE_TIME', 'PLANT_ID'], how='inner')
    
    # Feature Engineering
    df['hour'] = df['DATE_TIME'].dt.hour
    df['month'] = df['DATE_TIME'].dt.month
    
    # Features: hour, month, ambient_temperature, irradiation
    # Target: AC_POWER (usable solar power)
    features = ['hour', 'month', 'AMBIENT_TEMPERATURE', 'IRRADIATION']
    df = df.dropna(subset=features + ['AC_POWER'])
    
    X = df[features]
    y = df['AC_POWER']
    
    print("Fitting XGBoost Solar Regressor...")
    model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.1, max_depth=5)
    model.fit(X, y)
    
    model_path = os.path.join(MODELS_DIR, "solar_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"Saved Solar Model: {model_path}")

if __name__ == "__main__":
    os.makedirs(MODELS_DIR, exist_ok=True)
    train_demand_model()
    train_solar_model()
    print("Machine Learning Training Pipeline Complete!")
