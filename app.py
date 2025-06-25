from flask import Flask, render_template, jsonify, request, Response
import random
import time
import json
import os
from flask_socketio import SocketIO
import eventlet
import csv
import struct
import datetime
from flask_cors import CORS

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Persistent storage path for Render Disk
DATA_DIR = '/opt/render/data'
FLIGHT_HISTORY_FILE = os.path.join(DATA_DIR, 'flight_data.json')

# In-memory store, initialized from disk
message_history = []

# Ensure flight data is saved to a file
def save_flight_data(flight_data):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(FLIGHT_HISTORY_FILE):
        with open(FLIGHT_HISTORY_FILE, 'w') as f:
            json.dump([], f)

    with open(FLIGHT_HISTORY_FILE, 'r') as f:
        flight_history = json.load(f)

    flight_history.append(flight_data)

    with open(FLIGHT_HISTORY_FILE, 'w') as f:
        json.dump(flight_history, f)

# Load flight history from disk at startup
def load_flight_history():
    if not os.path.exists(FLIGHT_HISTORY_FILE):
        return []
    with open(FLIGHT_HISTORY_FILE, 'r') as f:
        return json.load(f)

# Initialize message_history at startup
message_history = load_flight_history()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/rockblock', methods=['POST'])
def handle_rockblock():
    data_json = request.get_json()
    imei = data_json.get('imei')
    data = data_json.get('data')

    print(f"Received POST /rockblock - IMEI: {imei}, Data: {data}")

    if imei != "301434060195570":
        print("Invalid credentials")
        return "FAILED,10,Invalid login credentials", 400

    if not data:
        print("No data provided")
        return "FAILED,16,No data provided", 400

    try:
        # Decode hex to bytes and then to text
        byte_data = bytearray.fromhex(data)
        message_text = byte_data.decode('utf-8', errors='ignore').strip()

        # Parse the text message into a dictionary
        message_data = {}
        pairs = [pair.strip() for pair in message_text.split(',') if ':' in pair]
        for pair in pairs:
            try:
                key, value = [p.strip().strip('"') for p in pair.split(':', 1)]
                if value.endswith('}'):
                    value = value.rstrip('}')  # Remove trailing '}' if present
                if value:
                    if value.isdigit():
                        message_data[key] = int(value)
                    elif value.replace('.', '').replace('-', '').isdigit():
                        message_data[key] = float(value)
                    else:
                        message_data[key] = value
            except ValueError as e:
                print(f"⚠️ Parse error for {key}: {e}")
                continue

        # Construct the full message_data without zero fallbacks
        sent_time_utc = datetime.datetime.fromtimestamp(message_data["unix_epoch"], datetime.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
        extra_message = message_data["message"]

        # Use raw values without fallbacks, raising KeyError if missing
        message_data = {
            "received_time": datetime.datetime.utcnow().isoformat() + "Z",
            "sent_time": sent_time_utc,
            "unix_epoch": message_data["unix_epoch"],
            "siv": message_data["siv"],
            "latitude": float(str(message_data["latitude"]).rstrip('}')),
            "longitude": float(str(message_data["longitude"]).rstrip('}')),
            "altitude": message_data["altitude"],
            "pressure_mbar": message_data["pressure_mbar"],
            "temperature_pht_c": message_data["temperature_pht_c"],
            "temperature_cj_c": message_data["temperature_cj_c"],
            "temperature_tctip_c": message_data["temperature_tctip_c"],
            "roll_deg": message_data["roll_deg"],
            "pitch_deg": message_data["pitch_deg"],
            "yaw_deg": message_data["yaw_deg"],
            "vavg_1_mps": message_data["vavg_1_mps"],
            "vavg_2_mps": message_data["vavg_2_mps"],
            "vavg_3_mps": message_data["vavg_3_mps"],
            "vstd_1_mps": message_data["vstd_1_mps"],
            "vstd_2_mps": message_data["vstd_2_mps"],
            "vstd_3_mps": message_data["vstd_3_mps"],
            "vpk_1_mps": message_data["vpk_1_mps"],
            "vpk_2_mps": message_data["vpk_2_mps"],
            "vpk_3_mps": message_data["vpk_3_mps"],
            "message": extra_message
        }

        message_history.append(message_data)
        save_flight_data(message_data)

        print(f"Processed and stored message: {message_data}")
        return "OK,0"

    except Exception as e:
        print("Error processing data:", e)
        return "FAILED,15,Error processing message data", 400

        # Construct the full message_data with raw values, no scaling
        sent_time_utc = datetime.datetime.fromtimestamp(message_data.get("unix_epoch", 0), datetime.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
        extra_message = message_data.get("message", "No extra message")

        message_data = {
            "received_time": datetime.datetime.utcnow().isoformat() + "Z",
            "sent_time": sent_time_utc,
            "unix_epoch": message_data.get("unix_epoch"),
            "siv": message_data.get("siv", ),
            "latitude": message_data.get("latitude"),
            "longitude": message_data.get("longitude"),
            "altitude": message_data.get("altitude"),
            "pressure_mbar": message_data.get("pressure_mbar"),
            "temperature_pht_c": message_data.get("temperature_pht_c"),
            "temperature_cj_c": message_data.get("temperature_cj_c"),
            "temperature_tctip_c": message_data.get("temperature_tctip_c"),
            "roll_deg": message_data.get("roll_deg"),
            "pitch_deg": message_data.get("pitch_deg"),
            "yaw_deg": message_data.get("yaw_deg"),
            "vavg_1_mps": message_data.get("vavg_1_mps"),
            "vavg_2_mps": message_data.get("vavg_2_mps"),
            "vavg_3_mps": message_data.get("vavg_3_mps"),
            "vstd_1_mps": message_data.get("vstd_1_mps"),
            "vstd_2_mps": message_data.get("vstd_2_mps"),
            "vstd_3_mps": message_data.get("vstd_3_mps"),
            "vpk_1_mps": message_data.get("vpk_1_mps"),
            "vpk_2_mps": message_data.get("vpk_2_mps"),
            "vpk_3_mps": message_data.get("vpk_3_mps"),
            "message": extra_message
        }

        message_history.append(message_data)
        save_flight_data(message_data)

        print(f"Processed and stored message: {message_data}")
        return "OK,0"

    except Exception as e:
        print("Error processing data:", e)
        return "FAILED,15,Error processing message data", 400

@app.route('/live-data', methods=['GET'])
def get_live_data():
    return jsonify(message_history[-1] if message_history else {"message": "No data received yet"})

@app.route('/flight-data', methods=['GET'])
def live_data():
    data = {
        "latitude": message_history[-1]["latitude"] if message_history else "No data",
        "longitude": message_history[-1]["longitude"] if message_history else "No data",
        "timestamps": message_history[-1]["sent_time"] if message_history else "No data",
        "altitudes": message_history[-1]["altitude"] if message_history else "No data"
    }
    return jsonify(data)

@app.route('/history', methods=['GET'])
def history():
    return jsonify(message_history)

@app.route('/download-history', methods=['GET'])
def download_history():
    if not message_history:
        return "No data available", 404
    def generate_csv():
        fieldnames = message_history[0].keys()
        yield ','.join(fieldnames) + '\n'
        for row in message_history:
            yield ','.join(str(row[field]) for field in fieldnames) + '\n'
    return Response(generate_csv(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment; filename=flight_history.csv"})

@app.route('/message-history', methods=['GET'])
def message_history_endpoint():
    return jsonify(message_history) if message_history else jsonify([])

@app.route("/animation-data", methods=['GET'])
def animation_data():
    if not message_history:
        return jsonify({
            "rotation": 0,
            "position": {"x": 0, "y": 0, "z": 0},
            "force": {"x": 0, "y": 0, "z": 0}
        })
    latest_message = message_history[-1]
    telemetry_data = {
        "rotation": latest_message["yaw_deg"],  # Use yaw for rotation (degrees)
        "position": {
            "x": 0,  # Keep centered; could use roll/pitch if desired
            "y": 0,
            "z": 0
        },
        "force": {
            "x": latest_message["vavg_1_mps"],  # Wind velocity X
            "y": latest_message["vavg_2_mps"],  # Wind velocity Y
            "z": latest_message["vavg_3_mps"]   # Wind velocity Z
        }
    }
    return jsonify(telemetry_data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
