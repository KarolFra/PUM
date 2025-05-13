import cv2
import numpy as np
import os
import glob

# Parametry szachownicy
CHECKERBOARD = (6, 9)  # Liczba wewnętrznych narożników (szerokość, wysokość)
SQUARE_SIZE = 25  # milimetry (rozmiar kwadratu szachownicy, zmierz po wydruku)

# Kryteria zakończenia dla cornerSubPix
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# Ścieżka do folderu kalibracyjnego
calib_data_path = "../calib_data"
CHECK_DIR = os.path.isdir(calib_data_path)

# Tworzenie folderu, jeśli nie istnieje
if not CHECK_DIR:
    os.makedirs(calib_data_path)
    print(f'"{calib_data_path}" Directory is created')
else:
    print(f'"{calib_data_path}" Directory already Exists.')

# Przygotowanie punktów 3D (w świecie rzeczywistym)
objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)
objp *= SQUARE_SIZE  # Skalowanie punktów 3D do milimetrów

# Listy do przechowywania punktów 3D i 2D
objpoints = []  # Punkty 3D w świecie rzeczywistym
imgpoints = []  # Punkty 2D w płaszczyźnie obrazu

# Folder ze zdjęciami szachownicy
image_dir_path = "calib_images"
images = glob.glob(f'{image_dir_path}/*.jpg')

if not images:
    print(f"Error: No images found in {image_dir_path}. Please add calibration images.")
    exit(1)

print(f"Found {len(images)} images for calibration.")

for fname in images:
    print(f"Processing image: {fname}")
    img = cv2.imread(fname)
    if img is None:
        print(f"Warning: Could not load image {fname}. Skipping...")
        continue
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, None)
    if ret:
        objpoints.append(objp)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        imgpoints.append(corners2)
        # Opcjonalnie: wyświetl obraz z wykrytymi narożnikami
        cv2.drawChessboardCorners(img, CHECKERBOARD, corners2, ret)
        cv2.imshow('Chessboard', img)
        cv2.waitKey(500)  # Pokaż na 500 ms
    else:
        print(f"Warning: Chessboard not found in {fname}. Skipping...")

cv2.destroyAllWindows()

if not objpoints or not imgpoints:
    print("Error: No valid chessboard images processed. Calibration failed.")
    exit(1)

print(f"Processed {len(objpoints)} valid images for calibration.")

# Kalibracja kamery
ret, cam_mat, dist_coef, rvecs, tvecs = cv2.calibrateCamera(
    objpoints, imgpoints, gray.shape[::-1], None, None
)

if not ret:
    print("Error: Camera calibration failed.")
    exit(1)

print("Calibration successful!")

# Zapis danych kalibracyjnych
np.savez(
    f"{calib_data_path}/MultiMatrix.npz",
    camMatrix=cam_mat,
    distCoef=dist_coef,
    rVector=rvecs,
    tVector=tvecs
)
print(f"Calibration data saved to {calib_data_path}/MultiMatrix.npz")

# Weryfikacja danych
print("Verifying saved calibration data...")
data = np.load(f"{calib_data_path}/MultiMatrix.npz")
print("Loaded calibration data:")
print("Camera Matrix:\n", data["camMatrix"])
print("Distortion Coefficients:\n", data["distCoef"])
print("Rotation Vectors:\n", data["rVector"])
print("Translation Vectors:\n", data["tVector"])
print("Calibration data loaded successfully!")
