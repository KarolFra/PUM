import subprocess
import cv2
import cv2.aruco as aruco
import numpy as np
import time
import threading
from flask import Blueprint, Response

from distance import calculate_marker_distance_from_camera

video_bp = Blueprint('video_bp', __name__)

# Global variables
latest_frame = None
frame_lock = threading.Lock() #lock for parrarel tasks
measurement_callback = None # will be used for detecting distances from markers

# Initialize ArUco detector
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50) # aruco dictionary
parameters = aruco.DetectorParameters()                       # aruco thresholds, marker sizes, etc.. (read description)
detector = aruco.ArucoDetector(aruco_dict, parameters)        #

# Load calibration data
calib_data_path = "../calib_data/MultiMatrix.npz"
calib_data = np.load(calib_data_path)
cam_mat = calib_data["camMatrix"]
dist_coef = calib_data["distCoef"]
MARKER_SIZE = 2.5  # !! centimeters
current_distance = None  # Global variable to store the latest distance

def set_measurement_callback(cb): 
    global measurement_callback
    measurement_callback = cb
    ## ??
	# ...

def capture_measured_video():
    global latest_frame, current_distance

    command = [
        "libcamera-vid", "--inline", "--timeout", "0", "--framerate", "20",
        "--width", "1920", "--height", "1080", "--codec", "mjpeg", "--output", "-"
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0
    )

    bytes_buffer = b""
    frame_counter = 0

    while True:
        chunk = process.stdout.read(1024)
        if not chunk:
            print("Cam process stopped, no new chunks")
            break

        bytes_buffer += chunk
        start_idx = bytes_buffer.find(b'\xff\xd8')
        end_idx = bytes_buffer.find(b'\xff\xd9')

        if start_idx == -1 or end_idx == -1:
            continue

        jpg = bytes_buffer[start_idx:end_idx + 2]
        bytes_buffer = bytes_buffer[end_idx + 2:]

        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            continue

        frame_counter += 1
        if frame_counter % 2 != 0:
            continue

        # ArUco marker detection
        gray_full = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = detector.detectMarkers(gray_full)

        if ids is not None and len(ids) > 0:  # chceking detection of marker
            aruco.drawDetectedMarkers(frame, corners, ids)
            # Estimate pose of markers
            rVec, tVec, _ = aruco.estimatePoseSingleMarkers(
                corners, MARKER_SIZE, cam_mat, dist_coef
            )
            for i in range(len(ids)):
                marker_id = ids[i][0]
                c = corners[i][0]
                center = tuple(np.mean(c, axis=0).astype(int))
                cv2.putText(
                    frame, f"ID:{marker_id}", center, cv2.FONT_HERSHEY_SIMPLEX,
                    3, (255, 0, 0), 4
                )

            # Calculate distance for the first marker only if tVec and ids are valid
            if tVec is not None and len(tVec) > 0:
                distance, display_text = calculate_marker_distance_from_camera(tVec[0], ids[0])
		# Update global distance variable
                current_distance = distance
                print(f"Calculated distance: {distance}")
 		# Send distance via callback (for MQTT)
                if measurement_callback and distance is not None:
                    measurement_callback(distance)
                # Display distance in bottom-right corner
                cv2.putText(
                    frame, display_text,
                    (frame.shape[1] - 300, frame.shape[0] - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2
                )

        # RE encode to JPEG for MJPEG streaming
        ret, encoded_frame = cv2.imencode(".jpg", frame)
        if ret:
           with frame_lock:
                latest_frame = encoded_frame.tobytes()

# MJPEG streaming
def generate_measured_stream():
    global latest_frame
    while True:
        frame_copy = None
        with frame_lock:
            if latest_frame is not None:
                frame_copy = latest_frame

        if frame_copy is not None:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" +
                   frame_copy +
                   b"\r\n")

        time.sleep(0.03)


@video_bp.route('/measured_video')
def measured_video():
    print("[video_meas] /measured_video: starting MJPEG stream")
    return Response(
        generate_measured_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@video_bp.route('/measured_view')
def measured_view():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Measured Video Stream</title>
    </head>
    <body>
      <h1>Measured Video Stream</h1>
      <p>Refresh this page any time – it won't restart the camera capture!</p>
      <img src="/measured_video" alt="Measured Video" style="width:640px; height:480px;">
    </body>
    </html>
    """
    return html_content
