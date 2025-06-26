# === IMPORTS ===
import os, sys, time, cv2, requests, threading, subprocess
import numpy as np, tensorflow as tf, lgpio, serial, math, socket
from queue import Queue
from tensorflow.keras.applications import VGG16
from tensorflow.keras.applications.vgg16 import preprocess_input

# === CONFIGURATION ===
AT_PORT = "/dev/ttyUSB3"
BAUD_RATE = 115200
POWER_KEY = 6
model_path = '/home/Jana/multi_class_model.h5'
output_dir = "/home/Jana/captured_frames"
CAMERA_LOCK_FILE = "/tmp/camera.lock"
class_labels = ['Condizioni Normali', 'Graffiti', 'Rifiuti']
prediction_api = 'http://192.168.59.1:8000/api/predictions/'
location_api = 'http://192.168.59.1:8000/api/locations/'
ip_api = 'http://192.168.59.1:8000/api/device_ip/'

device_id = "device-001"
shutdown_event = threading.Event()
frame_queue = Queue()

# === IP Address ===
def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "0.0.0.0"
    finally:
        s.close()
    return ip

ip_address = get_ip_address()

# === Setup ===
os.makedirs(output_dir, exist_ok=True)
print("[INIT] Loading model...")
model = tf.keras.models.load_model(model_path)
vgg16 = VGG16(include_top=False, input_shape=(224, 224, 3))
print("[INIT] Model loaded.")

ser = serial.Serial(AT_PORT, BAUD_RATE, timeout=1)
chip = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(chip, POWER_KEY)
latest_gps = {"lat": None, "lon": None}
last_sent_prediction = {"label": None, "lat": None, "lon": None}
last_sent_location = {"lat": None, "lon": None}

# === Haversine Distance ===
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def power_on():
    print("🔋 Powering ON SIM7000X...")
    lgpio.gpio_write(chip, POWER_KEY, 1)
    time.sleep(2)
    lgpio.gpio_write(chip, POWER_KEY, 0)
    time.sleep(20)
    ser.flushInput()
    print("✅ SIM7000X Ready.")

def send_at(command, expected="OK", timeout=2):
    ser.write((command + '\r\n').encode())
    time.sleep(timeout)
    reply = ser.read(ser.inWaiting()).decode(errors='ignore')
    print(f"📡 Sent: {command}\n🧾 Response: {reply.strip()}")
    return expected in reply, reply

def wait_for_fixed_gps():
    print("📍 Enabling GPS...")
    send_at("AT+CGNSPWR=1", "OK", 1)
    time.sleep(2)
    print("📡 Waiting for GPS fix...")
    for _ in range(60):
        success, response = send_at("AT+CGNSINF", "+CGNSINF:", 1)
        if success:
            lat, lon = parse_gps_coordinates(response)
            if lat and lon:
                print(f"✅ GPS Fix: Latitude={lat}, Longitude={lon}")
                return lat, lon
        time.sleep(2)
    print("❌ GPS fix failed.")
    return None, None

def parse_gps_coordinates(response):
    try:
        parts = response.split(',')
        if len(parts) >= 5:
            lat = float(parts[3])
            lon = float(parts[4])
            if abs(lat) > 0 and abs(lon) > 0:
                return lat, lon
    except Exception as e:
        print(f"[GPS] Parse error: {e}")
    return None, None

# === Preprocess image ===
def preprocess_image(frame, target_size=(224, 224)):
    img_resized = cv2.resize(frame, target_size)
    img_array = tf.keras.preprocessing.image.img_to_array(img_resized)
    img_array = preprocess_input(img_array)
    return np.expand_dims(img_array, axis=0), img_resized

# === Check if camera lock is held ===
def wait_for_camera_unlock():
    while os.path.exists(CAMERA_LOCK_FILE):
        print("[WAIT] Camera locked by Flask API...")
        time.sleep(1)

# === Capture frames ===
def capture_frames():
    frame_count = 0
    while not shutdown_event.is_set():
        wait_for_camera_unlock()
        subprocess.run("libcamera-still -o frame.jpg --width 640 --height 480 -t 1000", shell=True)
        frame = cv2.imread("frame.jpg")
        if frame is not None:
            print(f"[CAMERA] Captured frame {frame_count}")
            frame_queue.put((frame_count, frame))
            raw_path = os.path.join(output_dir, f"frame_{frame_count}.jpg")
            cv2.imwrite(raw_path, frame)
            frame_count += 1
        else:
            print("[CAMERA] Capture failed")
        time.sleep(0.1)

# === Prediction processing ===
def process_frames():
    while not shutdown_event.is_set():
        if not frame_queue.empty():
            frame_count, frame = frame_queue.get()
            img_tensor, original_img = preprocess_image(frame)
            features = vgg16.predict(img_tensor)
            flattened = features.flatten().reshape(1, -1)
            prediction = model.predict(flattened)
            predicted_label = class_labels[np.argmax(prediction)]

            lat, lon = latest_gps["lat"], latest_gps["lon"]
            if (
                last_sent_prediction["label"] == predicted_label and
                last_sent_prediction["lat"] and
                haversine(lat, lon, last_sent_prediction["lat"], last_sent_prediction["lon"]) < 2
            ):
                print("[SKIPPED] Same prediction & location.")
                continue

            last_sent_prediction.update({"label": predicted_label, "lat": lat, "lon": lon})
            payload = {
                "device_id": device_id,
                "label": predicted_label,
                "latitude": lat,
                "longitude": lon,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }

            try:
                response = requests.post(prediction_api, json=payload)
                print("[API] Prediction sent." if response.status_code == 201 else f"[API] Failed: {response.status_code}")
            except Exception as e:
                print(f"[API] Error: {e}")

            info = f"{predicted_label} | ({lat:.6f}, {lon:.6f})"
            cv2.putText(original_img, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
            labeled_path = os.path.join(output_dir, f"frame_{frame_count}_classified.jpg")
            cv2.imwrite(labeled_path, original_img)
        else:
            time.sleep(0.05)

# === Location + IP ===
def send_location_loop():
    while not shutdown_event.is_set():
        lat, lon = latest_gps["lat"], latest_gps["lon"]
        if lat and lon:
            if (
                last_sent_location["lat"] is None or
                haversine(lat, lon, last_sent_location["lat"], last_sent_location["lon"]) >= 2
            ):
                payload = {
                    "device_id": device_id,
                    "latitude": lat,
                    "longitude": lon,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
                try:
                    response = requests.post(location_api, json=payload)
                    print("[LOCATION] Sent." if response.status_code == 201 else f"[LOCATION] Failed: {response.status_code}")
                    last_sent_location.update({"lat": lat, "lon": lon})
                except Exception as e:
                    print(f"[LOCATION] Error: {e}")
        time.sleep(60)

def send_ip_loop():
    while not shutdown_event.is_set():
        payload = {
            "device_id": device_id,
            "ip_address": ip_address,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        try:
            response = requests.post(ip_api, json=payload)
            print("[IP] Sent." if response.status_code in (200, 201) else f"[IP] Failed: {response.status_code}")
        except Exception as e:
            print(f"[IP] Error: {e}")
        time.sleep(60)

# === MAIN ===
if __name__ == "__main__":
    try:
        power_on()
        lat, lon = wait_for_fixed_gps()
        if not lat or not lon:
            sys.exit("[ERROR] No GPS fix. Exiting.")
        latest_gps.update({"lat": lat, "lon": lon})

        threads = [
            threading.Thread(target=capture_frames),
            threading.Thread(target=process_frames),
            threading.Thread(target=send_location_loop),
            threading.Thread(target=send_ip_loop)
        ]
        for t in threads: t.start()
        for t in threads: t.join()

    except KeyboardInterrupt:
        print("🛑 Interrupted.")
        shutdown_event.set()

    finally:
        if ser: ser.close()
        lgpio.gpiochip_close(chip)