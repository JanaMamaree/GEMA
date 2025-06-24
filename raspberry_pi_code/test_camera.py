from flask import Flask, request, jsonify
from flask_cors import CORS  # ✅ Add this
import subprocess
import os
from datetime import datetime

app = Flask(__name__, static_url_path='/static')
CORS(app)  # ✅ Enable CORS for all routes

@app.route('/capture_image', methods=['POST'])
def capture_image():
    try:
        data = request.get_json()
        device_id = data.get('device_id', 'unknown')
        print(f"Capture request from device: {device_id}")

        capture_dir = os.path.join('static', 'captures')
        os.makedirs(capture_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_filename = f"{device_id}_{timestamp}.jpg"
        image_path = os.path.join(capture_dir, image_filename)

        subprocess.run(['libcamera-still', '-o', image_path, '-t', '1000'], check=True)

        image_url = f"/static/captures/{image_filename}"
        return jsonify({'success': True, 'image_url': image_url})

    except subprocess.CalledProcessError as e:
        return jsonify({'success': False, 'error': 'Camera capture failed', 'details': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)