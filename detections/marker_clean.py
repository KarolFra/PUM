import cv2
import cv2.aruco as aruco
import numpy as np
import os

# Define the ArUco dictionary
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

# Define the input/output directory
marker_dir = ""
input_files = [f"aruco_{i}.png" for i in range(1, 7)]

# Initialize the detector parameters and ArUco detector
parameters = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, parameters)

# Process each marker image
for i, filename in enumerate(input_files, 1):
    # Load the marker image
    image_path = os.path.join(marker_dir, filename)
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load {image_path}")
        continue

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Detect the marker to confirm its ID
    corners, ids, rejected = detector.detectMarkers(gray)
    if ids is None or len(ids) == 0:
        print(f"No ArUco marker detected in {image_path}")
        continue

    marker_id = ids[0][0]
    print(f"Detected marker ID {marker_id} in {image_path}")

    # Apply adaptive thresholding to create a clean, binary image
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # Invert the threshold if necessary (ensure black markers on white background)
    if np.mean(thresh) < 180:  # If the image is mostly dark, invert it
        thresh = cv2.bitwise_not(thresh)

    # Resize to a standard size (e.g., 200x200 pixels) for consistency
    standard_size = 16
    thresh = cv2.resize(thresh, (standard_size, standard_size), interpolation=cv2.INTER_NEAREST)

    # Save the thresholded marker
    output_path = os.path.join(marker_dir, f"aruco_{i}.jpg")
    cv2.imwrite(output_path, thresh)
    print(f"Saved thresholded marker to {output_path}")

print("Thresholding complete.")
