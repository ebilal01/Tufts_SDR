import datetime
from flask_cors import CORS
import logging
import binascii
from ast import literal_eval

# Configure logging for Render
@@ -94,26 +93,13 @@ def handle_rockblock():
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
            "vstd_1_mps": message_data.get("vstd_1_mps", 0),
            "message": extra_message
        }

@@ -137,7 +123,8 @@ def live_data():
        "latitude": message_history[-1]["latitude"] if message_history else "No data",
        "longitude": message_history[-1]["longitude"] if message_history else "No data",
        "timestamps": message_history[-1]["sent_time"] if message_history else "No data",
        "altitudes": message_history[-1]["altitude"] if message_history else "No data"
        "altitudes": message_history[-1]["altitude"] if message_history else "No data",
        "pressure_mbar": message_history[-1]["pressure_mbar"] if message_history else "No data"
    }
    return jsonify(data)

@@ -175,12 +162,12 @@ def animation_data():
        })
    latest_message = message_history[-1]
    telemetry_data = {
        "rotation": latest_message["yaw_deg"],
        "position": {"x": 0, "y": 0, "z": 0},
        "rotation": 0,  # No yaw_deg, using 0 as default
        "position": {"x": 0, "y": 0, "z": latest_message["altitude"] or 0},
        "force": {
            "x": latest_message["vavg_1_mps"],
            "y": latest_message["vavg_2_mps"],
            "z": latest_message["vavg_3_mps"]
            "x": latest_message["vpk_1_mps"] or 0,
            "y": 0,  # No vavg_2_mps, using 0
            "z": 0   # No vavg_3_mps, using 0
        }
    }
    return jsonify(telemetry_data)
