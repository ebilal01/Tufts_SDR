from flask import Flask, render_template, jsonify, request, Response
import json
import os
from flask_socketio import SocketIO
import datetime
from flask_cors import CORS
import logging
import binascii
from ast import literal_eval

# Configure logging for Render
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = None  # No byte limit
socketio = SocketIO(app, cors_allowed_origins="*")

# Persistent storage path for Render Disk
DATA_DIR = '/opt/render/data'
FLIGHT_HISTORY_FILE = os.path.join(DATA_DIR, 'flight_data.json')

message_history = []

def save_flight_data(flight_data):
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(FLIGHT_HISTORY_FILE):
            with open(FLIGHT_HISTORY_FILE, 'w') as f:
                json.dump([], f)
        with open(FLIGHT_HISTORY_FILE, 'r') as f:
            flight_history = json.load(f)
        flight_history.append(flight_data)
        with open(FLIGHT_HISTORY_FILE, 'w') as f:
            json.dump(flight_history, f)
    except Exception as e:
        logging.error(f"Error saving flight data: {e}")
        raise

def load_flight_history():
    try:
        if not os.path.exists(FLIGHT_HISTORY_FILE):
            return []
        with open(FLIGHT_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading flight history: {e}")
        return []

message_history = load_flight_history()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/rockblock', methods=['POST'])
def handle_rockblock():
    data_json = request.get_json()
    imei = data_json.get('imei')
    raw_data = data_json.get('data')  # Raw JSON-like string

    logging.info(f"Received POST /rockblock - IMEI: {imei}, Raw Data: {raw_data}, Length: {len(raw_data) if raw_data else 0} bytes")

    if imei != "301434060195570":
        logging.warning("Invalid credentials")
        return "FAILED,10,Invalid login credentials", 400

    if not raw_data:
        logging.warning("No data provided")
        return "FAILED,16,No data provided", 400

    try:
        # 🔍 Sanitize raw_data
        raw = raw_data.strip()
        if not raw.startswith("{"):
            raw = "{" + raw  # Fix missing leading brace

        logging.info(f"Sanitized raw message string: {raw}")

        # ✅ Try parsing with literal_eval (for Python-like dicts)
        try:
            message_data = literal_eval(raw)
        except Exception:
            logging.warning("literal_eval failed, trying json.loads")
            message_data = json.loads(raw)

        # Time conversion
        sent_time_utc = datetime.datetime.fromtimestamp(message_data.get("unix_epoch", 0), datetime.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
        extra_message = message_data.get("message", "No extra message")

        full_data = {
            "received_time": datetime.datetime.utcnow().isoformat() + "Z",
            "sent_time": sent_time_utc,
            "unix_epoch": message_data.get("unix_epoch", 0),
            "siv": message_data.get("siv", 0),
            "latitude": float(message_data.get("latitude", 0.0)),
            "longitude": float(message_data.get("longitude", 0.0)),
            "altitude": message_data.get("altitude", 0),
            "pressure_mbar": message_data.get("pressure_mbar", 0),
            "temperature_pht_c": message_data.get("temperature_pht_c", 0),
            "temperature_cj_c": message_data.get("temperature_cj_c", 0),
            "temperature_tctip_c": message_data.get("temperature_tctip_c", 0),
            "roll_deg": message_data.get("roll_deg", 0),
            "pitch_deg": message_data.get("pitch_deg", 0),
            "yaw_deg": message_data.get("yaw_deg", 0),
            "vavg_1_mps": message_data.get("vavg_1_mps", 0),
            "vavg_2_mps": message_data.get("vavg_2_mps", 0),
            "vavg_3_mps": message_data.get("vavg_3_mps", 0),
            "vstd_1_mps": message_data.get("vstd_1_mps", 0),
            "vstd_2_mps": message_data.get("vstd_2_mps", 0),
            "vstd_3_mps": message_data.get("vstd_3_mps", 0),
            "vpk_1_mps": message_data.get("vpk_1_mps", 0),
            "vpk_2_mps": message_data.get("vpk_2_mps", 0),
            "vpk_3_mps": message_data.get("vpk_3_mps", 0),
            "message": extra_message
        }

        message_history.append(full_data)
        save_flight_data(full_data)

        logging.info(f"Processed and stored message: {full_data}")
        return "OK,0"

    except Exception as e:
        logging.error(f"Error processing data: {e}")
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
            "force": {
                "x": 0,
                "y": 0,
                "z": 0
            }
        })
    latest_message = message_history[-1]
    telemetry_data = {
        "rotation": latest_message["yaw_deg"],
        "position": {"x": 0, "y": 0, "z": 0},
        "force": {
            "x": latest_message["vavg_1_mps"],
            "y": latest_message["vavg_2_mps"],
            "z": latest_message["vavg_3_mps"]
        }
    }
    return jsonify(telemetry_data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
