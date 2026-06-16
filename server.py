"""
SPEES402 - Practical Version A
Flask backend: reads temperature from Arduino over Serial,
publishes to MQTT broker, and serves live data to the web dashboard.

Install dependencies first:
    pip install flask pyserial paho-mqtt

Run:
    python server.py

Then open in browser:
    http://localhost:5000
"""

import utils.session
import serial
import threading
import time
from flask import Flask, jsonify, send_from_directory
import paho.mqtt.client as mqtt

# ---- CONFIG: change these ----
SERIAL_PORT = "COM4"          # change to your Arduino's port
BAUD_RATE = 9600

MQTT_BROKER = "broker.hivemq.com"   # replace with your VPS address if required
MQTT_PORT = 1883
MQTT_TOPIC = "spees402/temperature/mucyo_bertrand"  # replace candidate_name

CANDIDATE_NAME = "IRASUBIZA MUCYO Bertrand"  # change to your name
# --------------------------------

app = Flask(__name__)

# Shared state between the Serial-reading thread and the Flask routes
latest_data = {
    "temp": None,
    "status": None,
    "timestamp": None,
    "connected": False
}
readings_log = []  # keeps recent readings for the chart/log
LOG_MAX = 30
state_lock = threading.Lock()


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"[MQTT] Connected to {MQTT_BROKER}")
    else:
        print(f"[MQTT] Connection failed, reason code: {reason_code}")


def serial_worker():
    """Runs in a background thread: reads Serial, updates state, publishes to MQTT."""

    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect

    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
    except Exception as e:
        print(f"[MQTT] Could not connect: {e}")

    ser = None
    while ser is None:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print(f"[Serial] Connected on {SERIAL_PORT}")
            time.sleep(2)  # allow Arduino to reset
        except serial.SerialException as e:
            print(f"[Serial] Could not open {SERIAL_PORT}: {e}. Retrying in 3s...")
            time.sleep(3)

    while True:
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            parts = line.split(",")
            if len(parts) != 2:
                print(f"[Serial] Ignoring malformed line: {line}")
                continue

            temp_str, status = parts[0], parts[1]
            try:
                temp_value = float(temp_str)
            except ValueError:
                print(f"[Serial] Could not parse temperature: {line}")
                continue

            print(f"Temperature: {temp_value:.1f} C | Status: {status}")

            with state_lock:
                latest_data["temp"] = round(temp_value, 1)
                latest_data["status"] = status
                latest_data["timestamp"] = time.time()
                latest_data["connected"] = True

                readings_log.append({
                    "temp": round(temp_value, 1),
                    "status": status,
                    "timestamp": time.time()
                })
                if len(readings_log) > LOG_MAX:
                    readings_log.pop(0)

            payload = f"{temp_value:.1f},{status}"
            mqtt_client.publish(MQTT_TOPIC, payload)

        except serial.SerialException as e:
            print(f"[Serial] Error: {e}")
            with state_lock:
                latest_data["connected"] = False
            time.sleep(2)


@app.route("/")
def serve_dashboard():
    return send_from_directory(".", "index.html")


@app.route("/data")
def get_data():
    with state_lock:
        return jsonify({
            "candidate_name": CANDIDATE_NAME,
            "latest": latest_data,
            "log": readings_log
        })


if __name__ == "__main__":
    worker_thread = threading.Thread(target=serial_worker, daemon=True)
    worker_thread.start()

    app.run(host="0.0.0.0", port=5000, debug=False)
