import serial
import time
import json
import os
import paho.mqtt.client as mqtt
import serial.tools.list_ports

# Configuration
BROKER = os.getenv("MQTT_BROKER_URL", "test.mosquitto.org")
PORT = 1883
TOPIC_HARDWARE = "ecogrid/telemetry/hardware_sensors"
TOPIC_ACTUATORS = "ecogrid/telemetry/actuators"
BAUD_RATE = 9600

ser_global = None

def find_arduino_port():
    """Attempts to auto-detect Arduino port."""
    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in sorted(ports):
        if "Arduino" in desc or "CH340" in desc or "usbmodem" in port.lower():
            return port
    # Fallback default
    if os.name == 'nt':
        return "COM3"
    return "/dev/ttyUSB0"

def on_message(client, userdata, msg):
    global ser_global
    try:
        if msg.topic == TOPIC_ACTUATORS and ser_global:
            payload = json.loads(msg.payload.decode())
            command = payload.get("command", "")
            if command in ["EV_ON", "EV_OFF"]:
                ser_global.write(f"{command}\n".encode())
                print(f"Sent actuator command to Arduino: {command}")
    except Exception as e:
        print(f"Error handling actuator message: {e}")

def connect_mqtt():
    client = mqtt.Client(client_id="EcoGrid_Hardware_Bridge")
    client.on_message = on_message
    try:
        client.connect(BROKER, PORT, 60)
        client.subscribe(TOPIC_ACTUATORS)
        client.loop_start()
        print(f"Connected to MQTT broker at {BROKER}")
        return client
    except Exception as e:
        print(f"Failed to connect to MQTT: {e}")
        return None

def main():
    global ser_global
    print("Starting EcoGrid Hardware Serial Bridge...")
    mqtt_client = connect_mqtt()
    port = find_arduino_port()
    
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=2)
        ser_global = ser
        print(f"Successfully connected to Arduino on {port}")
    except Exception as e:
        print(f"ERROR: Could not open serial port {port}. Is the Arduino plugged in?")
        print(f"Exception: {e}")
        return

    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                # Expected format: "pot:512,ldr:800"
                if "pot:" in line and "ldr:" in line:
                    parts = line.split(',')
                    pot_val = int(parts[0].split(':')[1])
                    ldr_val = int(parts[1].split(':')[1])
                    
                    # Map 10-bit ADC (0-1023) to physical constraints
                    # POT controls Campus Demand (20 to 300 kW)
                    mapped_demand = 20.0 + (pot_val / 1023.0) * 280.0
                    
                    # LDR controls Solar Output (0 to 200 kW)
                    # Lower LDR usually means darker if pull-up, assuming higher LDR = brighter
                    mapped_solar = (ldr_val / 1023.0) * 200.0
                    
                    payload = {
                        "hardware_active": True,
                        "pot_raw": pot_val,
                        "ldr_raw": ldr_val,
                        "demand_kw": round(mapped_demand, 2),
                        "solar_kw": round(mapped_solar, 2),
                        "timestamp": time.time()
                    }
                    
                    if mqtt_client:
                        mqtt_client.publish(TOPIC_HARDWARE, json.dumps(payload))
                        print(f"Published Hardware Data: {payload}")
            time.sleep(0.1)
        except Exception as e:
            print(f"Error reading serial: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
