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
import logging

# Configure logging for Render
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)
# No byte limit for request size
app.config['MAX_CONTENT_LENGTH'] = None  # Accepts any size
app.config['MAX_CONTENT_LENGTH'] = None  # No byte limit
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
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)  # Use exist_ok to avoid race conditions
        if not os.path.exists(FLIGHT_HISTORY_FILE):
            with open(FLIGHT_HISTORY_FILE, 'w') as f:
                json.dump([], f)
        with open(FLIGHT_HISTORY_FILE, 'r') as f:
            flight_history = json.load(f)
        flight_history.append(flight_data)
        with open(FLIGHT_HISTORY_FILE, 'w') as f:
            json.dump([], f)

    with open(FLIGHT_HISTORY_FILE, 'r') as f:
        flight_history = json.load(f)

    flight_history.append(flight_data)

    with open(FLIGHT_HISTORY_FILE, 'w') as f:
        json.dump(flight_history, f)
            json.dump(flight_history, f)
    except Exception as e:
        logging.error(f"Error saving flight data: {e}")
        raise

# Load flight history from disk at startup
def load_flight_history():
    if not os.path.exists(FLIGHT_HISTORY_FILE):
    try:
        if not os.path.exists(FLIGHT_HISTORY_FILE):
            return []
        with open(FLIGHT_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading flight history: {e}")
        return []
    with open(FLIGHT_HISTORY_FILE, 'r') as f:
        return json.load(f)

# Initialize message_history at startup
message_history = load_flight_history()

@app.route('/')
@@ -59,36 +59,51 @@ def handle_rockblock():
    imei = data_json.get('imei')
    data = data_json.get('data')

    print(f"Received POST /rockblock - IMEI: {imei}, Raw Data: {data}, Length: {len(data) if data else 0} bytes")  # Log raw input
    logging.info(f"Received POST /rockblock - IMEI: {imei}, Raw Data: {data}, Length: {len(data) if data else 0} bytes")

    if imei != "301434060195570":
        print("Invalid credentials")
        logging.warning("Invalid credentials")
        return "FAILED,10,Invalid login credentials", 400

    if not data:
        print("No data provided")
        logging.warning("No data provided")
        return "FAILED,16,No data provided", 400

    try:
        # Decode hex to bytes and then to text
        byte_data = bytearray.fromhex(data)
        received_text = byte_data.decode('utf-8', errors='ignore').strip()
        print(f"Received text: {received_text}, Length: {len(received_text)} bytes")  # Log full received text
        logging.info(f"Received text (bytes): {list(byte_data)}, Received text (str): {received_text}, Length: {len(received_text)} bytes")

        # Remove padding and newline, ensuring JSON integrity
        # Remove padding and ensure JSON starts correctly
        if received_text.startswith("XXXXXX"):
            received_text = received_text[6:]  # Strip "XXXXXX" prefix
        if received_text.endswith("\n"):
            received_text = received_text[:-1]  # Remove newline
        print(f"Stripped received text: {received_text}, Length: {len(received_text)} bytes")  # Log stripped text

        # Parse as JSON
        received_text = received_text.lstrip()  # Remove leading whitespace or garbage
        json_start = received_text.find('{')
        if json_start >= 0:
            received_text = received_text[json_start:]  # Start from first {
        else:
            raise ValueError("No JSON object found in received text")
        if received_text.endswith("\n") or received_text.endswith("}"):
            received_text = received_text.rstrip("\n}")  # Remove newline or trailing }
        logging.info(f"Stripped received text: {received_text}, Length: {len(received_text)} bytes")

        # Validate and parse JSON
        try:
            message_data = json.loads(received_text)
            print(f"Parsed JSON data: {message_data}")  # Log parsed JSON
            # Validate required fields are present
            required_keys = ["altitude", "latitude", "longitude", "unix_epoch", "message"]
            missing_keys = [key for key in required_keys if key not in message_data]
            if missing_keys:
                logging.warning(f"Missing keys in JSON: {missing_keys}")
                raise ValueError(f"Missing required keys: {missing_keys}")
            logging.info(f"Parsed JSON data: {message_data}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}, Raw text: {received_text}")
            raise  # Re-raise to be caught by the outer except
            logging.error(f"JSON decode error: {e}, Raw text: {received_text}")
            raise
        except ValueError as e:
            logging.error(f"Validation error: {e}")
            raise

        # Construct the full message_data with raw values
        sent_time_utc = datetime.datetime.fromtimestamp(message_data.get("unix_epoch", 0), datetime.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
@@ -124,11 +139,11 @@ def handle_rockblock():
        message_history.append(message_data)
        save_flight_data(message_data)

        print(f"Processed and stored message: {message_data}")
        logging.info(f"Processed and stored message: {message_data}")
        return "OK,0"

    except Exception as e:
        print(f"Error processing data: {e}")  # Enhanced error log
        logging.error(f"Error processing data: {e}")
        return "FAILED,15,Error processing message data", 400

@app.route('/live-data', methods=['GET'])
@@ -171,20 +186,20 @@ def animation_data():
        return jsonify({
            "rotation": 0,
            "position": {"x": 0, "y": 0, "z": 0},
            "force": {"x": 0, "y": 0, "z": 0}
            "force": {
                "x": 0,
                "y": 0,
                "z": 0
            }
        })
    latest_message = message_history[-1]
    telemetry_data = {
        "rotation": latest_message["yaw_deg"],  # Use yaw for rotation (degrees)
        "position": {
            "x": 0,  # Keep centered; could use roll/pitch if desired
            "y": 0,
            "z": 0
        },
        "rotation": latest_message["yaw_deg"],
        "position": {"x": 0, "y": 0, "z": 0},
        "force": {
            "x": latest_message["vavg_1_mps"],  # Wind velocity X
            "y": latest_message["vavg_2_mps"],  # Wind velocity Y
            "z": latest_message["vavg_3_mps"]   # Wind velocity Z
            "x": latest_message["vavg_1_mps"],
            "y": latest_message["vavg_2_mps"],
            "z": latest_message["vavg_3_mps"]
        }
    }
    return jsonify(telemetry_data)
