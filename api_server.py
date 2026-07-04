from dotenv import load_dotenv
from flask import Flask, request, jsonify
import os

load_dotenv()

app = Flask(__name__)

def _serialize_result(obj):
    try:
        import karrio.lib as lib

        return lib.to_dict(obj)
    except Exception:
        try:
            import json

            return json.loads(json.dumps(obj, default=str))
        except Exception:
            return str(obj)


@app.route("/track", methods=["GET", "POST"]) 
def track():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        tracking_number = data.get("tracking_number") or data.get("trackingNumber")
        carrier = data.get("carrier") or data.get("carrier_name")
    else:
        tracking_number = request.args.get("tracking_number") or request.args.get("trackingNumber")
        carrier = request.args.get("carrier") or request.args.get("carrier_name")

    if not tracking_number or not carrier:
        return jsonify({"ok": False, "error": "tracking_number and carrier are required"}), 400

    try:
        from carriers.tracking import track_shipment

        result = track_shipment(tracking_number, carrier)
        return jsonify({"ok": True, "result": _serialize_result(result)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
