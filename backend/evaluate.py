import pandas as pd
import xgboost as xgb
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

DATA_DIR = "data"
DEMAND_CSV = "PJME_hourly.csv"
SOLAR_CSV = "Plant_1_Generation_Data.csv"
WEATHER_CSV = "Plant_1_Weather_Sensor_Data.csv"

print("--- EVALUATING DEMAND MODEL ---")
df = pd.read_csv(os.path.join(DATA_DIR, DEMAND_CSV))
df['Datetime'] = pd.to_datetime(df['Datetime'])
df['hour'] = df['Datetime'].dt.hour
df['dayofweek'] = df['Datetime'].dt.dayofweek
df['month'] = df['Datetime'].dt.month
df['is_weekend'] = df['dayofweek'].apply(lambda x: 1 if x >= 5 else 0)

X = df[['hour', 'dayofweek', 'month', 'is_weekend']]
y = df['PJME_MW']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.1, max_depth=5)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)

print(f"Demand RMSE: {mean_squared_error(y_test, y_pred) ** 0.5:.2f}")
print(f"Demand MAE: {mean_absolute_error(y_test, y_pred):.2f}")
print(f"Demand R2 Score: {r2_score(y_test, y_pred):.4f}\n")

print("--- EVALUATING SOLAR MODEL ---")
df_solar = pd.read_csv(os.path.join(DATA_DIR, SOLAR_CSV))
df_weather = pd.read_csv(os.path.join(DATA_DIR, WEATHER_CSV))

df_solar['DATE_TIME'] = pd.to_datetime(df_solar['DATE_TIME'], format="mixed")
df_weather['DATE_TIME'] = pd.to_datetime(df_weather['DATE_TIME'], format="mixed")

df_s = pd.merge(df_solar, df_weather, on=['DATE_TIME', 'PLANT_ID'], how='inner')
df_s['hour'] = df_s['DATE_TIME'].dt.hour
df_s['month'] = df_s['DATE_TIME'].dt.month

features = ['hour', 'month', 'AMBIENT_TEMPERATURE', 'IRRADIATION']
df_s = df_s.dropna(subset=features + ['AC_POWER'])

X_s = df_s[features]
y_s = df_s['AC_POWER']

X_train_s, X_test_s, y_train_s, y_test_s = train_test_split(X_s, y_s, test_size=0.2, random_state=42)
model_s = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.1, max_depth=5)
model_s.fit(X_train_s, y_train_s)
y_pred_s = model_s.predict(X_test_s)

print(f"Solar RMSE: {mean_squared_error(y_test_s, y_pred_s) ** 0.5:.2f}")
print(f"Solar MAE: {mean_absolute_error(y_test_s, y_pred_s):.2f}")
print(f"Solar R2 Score: {r2_score(y_test_s, y_pred_s):.4f}")
