from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import os
import time
from datetime import datetime

app = Flask(__name__, static_url_path='/static')
CORS(app)

LOCK_FILE = "/tmp/camera.lock"

@app.route('/capture_image', methods=['POST'])
def capture_image():
    try:
        data = request.get_json()
        device_id = data.get('device_id', 'unknown')
        print(f"Capture request from device: {device_id}")

        # Lock camera
        with open(LOCK_FILE, "w") as f:
            f.write("locked")
        print("[FLASK] Camera lock acquired.")
        time.sleep(2)  # Give time for main_system to pause

        capture_dir = os.path.join('static', 'captures')
        os.makedirs(capture_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_filename = f"{device_id}_{timestamp}.jpg"
        image_path = os.path.join(capture_dir, image_filename)

        subprocess.run(['libcamera-still', '-o', image_path, '-t', '1000'], check=True)

        # Unlock camera
        os.remove(LOCK_FILE)
        print("[FLASK] Camera lock released.")

        image_url = f"/static/captures/{image_filename}"
        return jsonify({'success': True, 'image_url': image_url})

    except subprocess.CalledProcessError as e:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        return jsonify({'success': False, 'error': 'Camera capture failed', 'details': str(e)}), 500

    except Exception as e:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)