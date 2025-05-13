import signal #for sending messages after ^C to: /home/control/pwm & manualDC
import sys #provides functions and variables used by the interpreter; used e.g. 4 sys.exit.
import json #enables works with text formatted in json
import time
import threading #allows to create and manage threads - performing parallel tasks. 
from threading import Lock #lock ensures synchro between parrarel data used by threading
import subprocess #enable camera use
from flask import Flask, jsonify, Response, render_template, request #4 API
from flask import current_app
from flask_mqtt import Mqtt
from models import db, SensorData # to generate charts

import mqtt_config #adjust if needed
# 3 lines to start mqtt comunication from mqtt_config
from mqtt_config import configure_mqtt
app = Flask(__name__, static_folder='static') #in static is located .css file
configure_mqtt(app)  # Configure MQTT after app is defined

#  Import functions from viedo_meas.py
from video_meas import video_bp, capture_measured_video

app.register_blueprint(video_bp)  # REQUIRED for routes from video_meas
# if ^^ wouldn t be here, Flask will never know about your blueprints routes.

#!! here should be sets of certain distances to markers (for steering) !!#
# global measurement, updated whenever video_meas sees something
captured_measurement = None
captured_timestamp = 0
lock = threading.Lock()

# Database Setup
from flask_migrate import Migrate

#!!IF DEBUG MQTT COMMENT THIS BELOW!!
#Place this before you call app.run(...). This will stop printing the standard request logs, 
# but also hides all other default logs from the Flask server.
"""import logging
log = logging.getLogger('werkzeug')
log.disabled = True
app.logger.disabled = True
"""
# Configure the app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensor_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# create SQLAlchemy instance with the app
db.init_app(app)
# Initialize Flask-Migrate with the app and database
migrate = Migrate(app, db)

with app.app_context():
    print("Creating tables...")
    db.create_all()
    print("Tables created!")

# Global sensor data
sensor_data = {
    'distance_center': None,    # 1st hc-sr04 dist
    'distance_left': None,      # 2d HC-Sr04
    'distance_right': None,     # 3rd HC-SR04
    'cpu_temp': None            # Rpi CPU temperature
}
lock = Lock()
is_subscribed = False

#!! adjust for sure (later) !!#
# This function will be called whenever video_meas detects a measurement
def on_new_measurement(width_cm, height_cm):
    print(f"[APP] New measurement: {width_cm:.2f} x {height_cm:.2f}")
    
    global captured_measurement, captured_timestamp
    with lock:
        captured_measurement = (width_cm, height_cm)
        captured_timestamp = time.time()

# !!
#"esp32" ~= auto 
control_mode = "esp32"  # Default mode to control the process, ESP32 (bcs at beginning i wanted to make calculations in one of esp)

stop_time = 10  # Default value (in seconds)

@app.route('/set_stop_time/<int:seconds>', methods=['POST'])
def set_stop_time(seconds):
    global stop_time
    stop_time = seconds
    return jsonify({"status": "ok", "stop_time": seconds})

#temporary set pwm on conveyor for specified time, bcs distance sensor doesnt work correctly
""" def auto_send_conveyor_pwm():
    if control_mode != "esp32":
        return  # skip if in manual mode

    #import time
    global mqtt, captured_measurement, captured_timestamp

    # Immediately set conveyor PWM to 0
    mqtt.publish('/home/control/conveyorPWM', '0')

    now = time.time()
    # If no measurement or older than 15s -> default to 1x1
    if captured_measurement is None or (now - captured_timestamp) > 15:
        width, height = 1, 1
    else:
        width, height = captured_measurement

    # Clamp each dimension to [1 - 3]
    width = max(1, min(width, 3))
    height = max(1, min(height, 3))

    # Compute average dimension
    avg_dim = (width + height) / 2.0

    # map [1 - 3] -> [50 - 90]
    conveyor_pwm = int((avg_dim - 1) * (90 - 50) / (3 - 1) + 50)

    # wait 2 seconds before applying (optionally)
    time.sleep(2)

    # publish the final PWM
    mqtt.publish('/home/control/conveyorPWM', str(conveyor_pwm))
    print(f"[auto_send_conveyor_pwm] set to {conveyor_pwm} (width={width:.2f}, height={height:.2f}) ignoring distance")

    # hold that PWM for 10 seconds
    time.sleep(10)

    # reset to 0 after 20s, after that time u can put another item on conveyor
    mqtt.publish('/home/control/conveyorPWM', '0')
    print("[auto_send_conveyor_pwm] Held 10s, now reset to 0.")


def auto_send_fan_pwm():
    
    #Similar logic, ignoring distance, using only (width, height) for the fan PWM.
    #Mapping [1 - 3] -> [60 - 255]. Holding 20s, then reset to 0.
    
    if control_mode != "esp32":
        return  # skip if in manual mode

    #import time
    global mqtt, captured_measurement, captured_timestamp

    # at start set fan PWM to 0
    mqtt.publish('/home/control/fanPWM', '0')

    now = time.time()
    # if older captured measures than 15s or missing -> default to 1x1
    if captured_measurement is None or (now - captured_timestamp) > 15:
        width, height = 1, 1
    else:
        width, height = captured_measurement

    width = max(1, min(width, 3))
    height = max(1, min(height, 3))

    # average dimension
    avg_dim = (width + height) / 2.0

    # map [1 - 3] -> [60 - 255]
    fan_pwm = int((avg_dim - 1) * (255 - 60) / (3 - 1) + 60)

    # optional wait
    time.sleep(2)

    mqtt.publish('/home/control/fanPWM', str(fan_pwm))
    print(f"[auto_send_fan_pwm] set to {fan_pwm} (width={width:.2f}, height={height:.2f}) ignoring distance")

    # hold 20s
    time.sleep(20)

    mqtt.publish('/home/control/fanPWM', '0')
    print("[auto_send_fan_pwm] Held 15s, now reset to 0.")

#  BACKGROUND THREAD FOR PERIODIC UPDATES 
def pwm_update_loop():
    "    #Periodically call auto-send functions for hold pwm values
    
    while True:
        auto_send_conveyor_pwm()
        auto_send_fan_pwm()
        time.sleep(1)  # adjust as needed

def handle_sigint(signum, frame):
    print("CTRL+C pressed! Sending 'default' messages to revert ESP32 to automatic mode.")
    try:
        mqtt.publish('/home/control/pwm', 'default')     # Revert LED to sensor based logic in esp32
        mqtt.publish('/home/control/manualDC', '0')  # Revert DC motors to sensor based
    except Exception as e:
        print("Error publishing default messages on exit:", e)
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)
"""
mqtt = Mqtt(app) #mqtt app init

def send_distance(distance):
    """
    Publishes the provided distance value as a JSON payload to the MQTT topic /home/sensors/distance
    :paramaters distance: float, the distance value to send.
    """
    payload = json.dumps({"distance": distance})
    try:
        mqtt.publish("/home/sensors/distance", payload)
        print(f"Sent distance: {payload} to /home/sensors/distance")
    except Exception as e:
        print(f"Error publishing distance: {e}")

def publish_distance_periodically():
    while True:
        dist = sensor_data.get('distance', None)
        if dist is not None:
            send_distance(dist)
        time.sleep(1)  # Wait 1 second between publishes (adjust as needed)

@app.route('/set_fan_speed/<int:speed>', methods=['POST'])
def set_fan_speed(speed):
    if control_mode == "manual":
        print(f"Manual mode: Fan speed set to {speed}")
        time.sleep(0.3)  # 300 milliseconds delay before sending the message
        # Publish to an MQTT topic, e.g. /home/control/fanPWM
        mqtt.publish('/home/control/fanPWM', str(speed))
        time.sleep(0.6)  # 300 milliseconds delay before sending second message, for safety, because one of esp is in deepleep
        mqtt.publish('/home/control/fanPWM', str(speed))
    return jsonify({"status": "ok", "fan_speed": speed})

@app.route('/set_conveyor_speed/<int:speed>', methods=['POST'])
def set_conveyor_speed(speed):
    if control_mode == "manual":
        print(f"Manual mode: Conveyor speed set to {speed}")
        time.sleep(0.3)  # 300 milliseconds delay before sending the message
        # Publish to /home/control/conveyorPWM
        mqtt.publish('/home/control/conveyorPWM', str(speed))
        time.sleep(0.6)  # 300 milliseconds delay before sending second message, for safety, because one of esp is in deepleep
        mqtt.publish('/home/control/conveyorPWM', str(speed))
    return jsonify({"status": "ok", "conveyor_speed": speed})

@app.route('/set_control_mode/<mode>', methods=['POST'])
def set_control_mode(mode):
    global control_mode

    # Only allow "esp32" or "manual"
    if mode in ["esp32", "manual"]:
        control_mode = mode
        print(f"Control mode switched to: {mode}")

        # Publish the same raw string to the ESP32
        # so it matches your callback logic:
        mqtt.publish('/set_control_mode', mode)

        return jsonify({"status": "ok", "control_mode": control_mode})
    else:
        return jsonify({"error": "Invalid mode. Use 'esp32' or 'manual'."}), 400

# Thread to read RPi CPU Temp & store in DB
def read_rpi_temp_forever():
    while True:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_c = float(f.read()) / 1000.0
            with lock:
                sensor_data['cpu_temp'] = temp_c

            # Optionally store CPU temp in DB
            """with app.app_context():
                entry = SensorData(temperature=temp_c, humidity=None, sensor_source='cpu')
                db.session.add(entry)
                db.session.commit()
            """
        except Exception as e:
            print(f"Error reading RPi temp: {e}")

        time.sleep(5)

# MQTT Handlers
@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    global is_subscribed
    print("Connected to MQTT broker")
    if not is_subscribed:
        try:
            topics = ['/home/sensor_data', '/home/control/pwm', '/home/sensors/distance']
            for t in topics:
                mqtt.subscribe(t)
            is_subscribed = True
            print(f"Subscribed to topics: {topics}")
        except Exception as e:
            print(f"Error subscribing to topics: {e}")

@mqtt.on_disconnect()
def handle_disconnect():
    print("MQTT broker disconnected Ã¢â‚¬â€ resetting manual modes.")
    # Publish messages to inform ESP32 to return to sensor mode
    mqtt.publish('/home/control/pwm', 'default')
    mqtt.publish('/set_control_mode', '0')

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    global sensor_data
    try:
        payload = json.loads(message.payload.decode('utf-8'))
        print(f"MQTT received on {message.topic}: {payload}")

        if message.topic == '/home/sensor_data':
            t = float(payload.get('t', 0.0))
            h = float(payload.get('h', 0.0))
            sensor_data['temperature'] = t
            sensor_data['humidity'] = h
            # Store DHT sensor data with sensor_source ='dht'
            with app.app_context():
                entry = SensorData(temperature=t, humidity=h, sensor_source='dht')
                db.session.add(entry)
                db.session.commit()

        elif message.topic == '/home/sensors/distance':
            sensor_data['distance'] = float(payload.get('distance', 0.0))
        elif message.topic == '/home/control/pwm':
            print("PWM Control message:", payload)
        elif message.topic == '/set_control_mode':
            print("PWM Control message:", payload)
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

# Routes
#video routes in separate file video_meas.py

#!! how will we send distance??
# Return the distance as JSON
@app.route('/distance', methods=['GET'])
def get_distance():
    dist = sensor_data.get('distance', 'No data')
    return jsonify({'distance': dist})

# Return the DHT sensor data as JSON
@app.route('/sensor_data', methods=['GET'])
def get_sensor_data():
    t = sensor_data.get('temperature', 'No data')
    h = sensor_data.get('humidity', 'No data')
    return jsonify({'temperature': t, 'humidity': h})

# Return CPU temperature as JSON //(unchanged)
@app.route('/rpi_temperature', methods=['GET'])
def rpi_temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = float(f.read()) / 1000.0
        return jsonify({"temperature": f"{temp:.3f} \u00B0C"})
    except Exception as e:
        return jsonify({"error": "Could not fetch RPi temperature", "message": str(e)}), 500

# Set PWM route
@app.route('/set_pwm/<string:value>', methods=['POST'])
def set_pwm(value):
    try:
        if value.isdigit():
            pwm_val = int(value)
            if 0 <= pwm_val <= 255:
                mqtt.publish('/home/control/pwm', str(pwm_val))
                print(f"Sent PWM: {pwm_val} to /home/control/pwm")
                return jsonify({"status": "success", "pwm": pwm_val})
            else:
                return jsonify({"error": "Invalid PWM value, must be 0-255"}), 400
        elif value == "default":
            mqtt.publish('/home/control/pwm', "default")
            print("Sent 'default' to /home/control/pwm - PWM controlled by ESP32")
            return jsonify({"status": "success", "pwm": "default"})
        else:
            return jsonify({"error": "Invalid command"}), 400
    except Exception as e:
        print(f"Error setting PWM: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# Chart for 'temperature' or 'humidity'
#!! prolly will be unused
@app.route('/chart/<data_type>')
def chart(data_type):
    try:
        if data_type == 'temperature':
            data = SensorData.query.filter_by(sensor_source='dht').with_entities(
                SensorData.timestamp, SensorData.temperature).all()
        elif data_type == 'humidity':
            data = SensorData.query.with_entities(
                SensorData.timestamp, SensorData.humidity).all()
        else:
            return "Invalid data type", 400

        chart_data = {
            "timestamps": [
                record[0].strftime('%Y-%m-%d %H:%M:%S')
                for record in data if record[0] is not None
            ],
            "values": [record[1] for record in data if record[1] is not None]
        }

        print(f"Chart Data for {data_type}: {chart_data}")
        return render_template('chart.html', data_type=data_type, chart_data=chart_data)
    except Exception as e:
        print(f"Error generating chart: {e}")
        return f"Error generating chart: {e}", 500

# Combined Chart
@app.route('/chart/combined')
def combined_chart():
    """
    Returns a combined chart of DHT temperature and humidity,
    excluding CPU data (sensor_source='cpu').
    """
    try:
        # Only fetch rows where sensor_source='dht'
        data = (SensorData.query
                .filter(SensorData.sensor_source == 'dht')
                .with_entities(SensorData.timestamp,
                               SensorData.temperature,
                               SensorData.humidity)
                .all()) 
# Prepare data for the template
        chart_data = {
            "timestamps": [
                r[0].strftime('%Y-%m-%d %H:%M:%S') for r in data if r[0]
            ],
            "temperature_values": [r[1] for r in data if r[1] is not None],
            "humidity_values":    [r[2] for r in data if r[2] is not None]
        }

        print(f"Combined Chart Data: {chart_data}")
        return render_template('combined_chart.html', chart_data=chart_data)

    except Exception as e:
        print(f"Error generating combined chart: {e}")
        return f"Error generating combined chart: {e}", 500

@app.route('/chart/rpi_temp') # CHART for RPI Temp
def chart_rpi_temp():

    #Query sensor_source='cpu' from DB and pass data to a template for charting CPU temperature.
    
    try:
        data = SensorData.query.filter_by(sensor_source='cpu') \
                               .with_entities(SensorData.timestamp, SensorData.temperature).all()
        chart_data = {
            "timestamps": [record[0].strftime('%Y-%m-%d %H:%M:%S') for record in data if record[0]],
            "values":     [record[1] for record in data if record[1] is not None]
        }
        return render_template('chart_rpi_temp.html', chart_data=chart_data)
    except Exception as e:
        print(f"Error generating RPi temp chart: {e}")
        return f"Error generating chart: {e}", 500


# Home & index
@app.route('/')
def index():
    return render_template('index.html')

# Main
if __name__ == '__main__':
    # Start CPU temp reading in background
    threading.Thread(target=read_rpi_temp_forever, daemon=True).start()
    # START the capture thread to generate frames
    capture_thread = threading.Thread(target=capture_measured_video, daemon=True)
    capture_thread.start()
    #threading.Thread(target=pwm_update_loop, daemon=True).start()
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
