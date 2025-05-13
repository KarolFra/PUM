import cv2
import cv2.aruco as aruco
import numpy as np
import os

# Define the ArUco dictionary
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

# Define the input photos and output directory
input_photos = [
    "aruco/aruco_1.png",  # Replace with your actual photo paths
    "aruco/aruco_2.png",
    "aruco/aruco_3.png",
    "aruco/aruco_4.png",
    "aruco/aruco_5.png",
    "aruco/aruco_6.png"
]
output_dir = "markers"

# Create the output directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Initialize the detector parameters and ArUco detector
parameters = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, parameters)

# Process each photo
for i, photo_path in enumerate(input_photos, 1):
    # Load the image
    image = cv2.imread(photo_path)
    if image is None:
        print(f"Error: Could not load {photo_path}")
        continue

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Detect markers
    corners, ids, rejected = detector.detectMarkers(gray)

    if ids is not None and len(ids) > 0:
        # Assume one marker per photo; take the first detected marker
        marker_corners = corners[0][0]  # Corners of the first marker
        marker_id = ids[0][0]
        print(f"Detected marker ID {marker_id} in {photo_path}")

        # Get the bounding box of the marker (min and max coordinates)
        x_min = int(np.min(marker_corners[:, 0]))
        x_max = int(np.max(marker_corners[:, 0]))
        y_min = int(np.min(marker_corners[:, 1]))
        y_max = int(np.max(marker_corners[:, 1]))

        # Add a small padding to ensure the entire marker is captured
        padding = 10
        x_min = max(0, x_min - padding)
        x_max = min(image.shape[1], x_max + padding)
        y_min = max(0, y_min - padding)
        y_max = min(image.shape[0], y_max + padding)

        # Crop the marker region
        cropped_marker = image[y_min:y_max, x_min:x_max]

        # Save the cropped marker
        output_path = os.path.join(output_dir, f"aruco_{i}.jpg")
        cv2.imwrite(output_path, cropped_marker)
        print(f"Saved cropped marker to {output_path}")
    else:
        print(f"No ArUco markers detected in {photo_path}")

print("Processing complete.")
