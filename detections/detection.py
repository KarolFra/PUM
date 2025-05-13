import cv2
import cv2.aruco as aruco
import numpy as np
import os

# Define the ArUco dictionary
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

# Define the input photos and output directory
marker_dir = "aruco"
input_files = [f"aruco_{i}.png" for i in range(1, 7)]
output_dir = "markers_view"

# Create the output directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Initialize the detector parameters and ArUco detector
parameters = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, parameters)

# Process each marker image
for i, filename in enumerate(input_files, 1):
    # Load the image
    image_path = os.path.join(marker_dir, filename)
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load {image_path}")
        continue

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Detect markers
    corners, ids, rejected = detector.detectMarkers(gray)

    if ids is not None:
        print(f"Detected {len(ids)} ArUco markers in {image_path}")
        for j in range(len(ids)):
            print(f"Marker ID: {ids[j][0]}")
            print(f"Corners: {corners[j][0]}")

        # Draw detected markers on the image
        aruco.drawDetectedMarkers(image, corners, ids)
    else:
        print(f"No ArUco markers detected in {image_path}")

    # Save the output image
    output_path = os.path.join(output_dir, f"output_aruco_{i}.png")
    cv2.imwrite(output_path, image)
    print(f"Saved output to {output_path}")

print("Detection complete.")
