import subprocess
import os
import cv2
import numpy as np

# Ścieżka do folderu na zdjęcia
image_dir_path = "calib_images"
MAX_IMAGES = 30  # Maksymalna liczba zdjęć

# Tworzenie folderu, jeśli nie istnieje
if not os.path.isdir(image_dir_path):
    os.makedirs(image_dir_path)
    print(f'Created directory: {image_dir_path}')
else:
    print(f'Directory already exists: {image_dir_path}')

# Sprawdzenie uprawnień do zapisu
try:
    with open(os.path.join(image_dir_path, 'test_write.txt'), 'w') as f:
        f.write('test')
    os.remove(os.path.join(image_dir_path, 'test_write.txt'))
    print(f'Write permissions verified for {image_dir_path}')
except PermissionError:
    print(f'Error: No write permissions for {image_dir_path}. Please adjust permissions.')
    exit(1)

# Licznik istniejących zdjęć
existing_images = len([f for f in os.listdir(image_dir_path) if f.endswith('.jpg')])
print(f'Found {existing_images} existing images in {image_dir_path}')

# Sprawdzenie dostępności kamery
try:
    subprocess.run(['libcamera-still', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print('Camera is accessible.')
except subprocess.CalledProcessError:
    print('Error: Camera is not accessible. Check connection and libcamera installation.')
    exit(1)

# Inicjalizacja podglądu na żywo z libcamera-vid
command = [
    "libcamera-vid",
    "--inline",
    "--timeout", "0",
    "--framerate", "20",
    "--width", "1920",
    "--height", "1080",
    "--codec", "mjpeg",
    "--output", "-"
]

process = subprocess.Popen(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    bufsize=0
)

bytes_buffer = b""
image_count = existing_images
print("Live preview started. Adjust the chessboard in the frame.")
print("Press Space to capture an image, 'q' to quit.")

# Podgląd na żywo
while image_count < MAX_IMAGES:
    chunk = process.stdout.read(1024)
    if not chunk:
        print("Camera process stopped.")
        break

    bytes_buffer += chunk
    start_idx = bytes_buffer.find(b'\xff\xd8')  # Początek ramki JPEG
    end_idx = bytes_buffer.find(b'\xff\xd9')    # Koniec ramki JPEG

    if start_idx == -1 or end_idx == -1:
        continue

    jpg = bytes_buffer[start_idx:end_idx + 2]
    bytes_buffer = bytes_buffer[end_idx + 2:]

    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        continue

    # Pomniejsz ramkę do wyświetlenia (np. 960x540)
    preview_frame = cv2.resize(frame, (960, 540))

    # Wyświetl instrukcje i licznik zdjęć na obrazie
    cv2.putText(
        preview_frame,
        f"Images: {image_count}/{MAX_IMAGES} | Press Space to capture, 'q' to quit",
        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
    )
    cv2.imshow('Live Preview', preview_frame)

    # Sprawdź klawisze
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):  # Wyjdź na 'q'
        print("Exiting...")
        break
    elif key == 32:  # Spacja (kod ASCII 32)
        image_filename = f"{image_dir_path}/image_{image_count:02d}.jpg"
        
        # Zakończ podgląd na chwilę, aby zwolnić kamerę
        process.terminate()
        
        # Użyj libcamera-still do zrobienia zdjęcia
        capture_command = [
            "libcamera-still",
            "--width", "1920",
            "--height", "1080",
            "--output", image_filename,
            "--timeout", "1000",
            "--encoding", "jpg"
        ]
        
        print(f'Capturing image {image_count + 1}/{MAX_IMAGES}: {image_filename}')
        try:
            result = subprocess.run(capture_command, check=True, stderr=subprocess.PIPE, text=True)
            # Wczytaj i wyświetl zdjęcie
            img = cv2.imread(image_filename)
            if img is None:
                print(f'Warning: Failed to load {image_filename}. Skipping...')
                os.remove(image_filename)
                continue
            
            # Pomniejsz zdjęcie do wyświetlenia
            preview_img = cv2.resize(img, (960, 540))
            cv2.imshow('Captured Image', preview_img)
            cv2.waitKey(500)
            
            image_count += 1
        except subprocess.CalledProcessError as e:
            print(f'Error capturing image: Command {capture_command} failed with exit status {e.returncode}.')
            print(f'Error output: {e.stderr}')
            print('Try again or check camera settings...')
        
        # Wznów podgląd
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0
        )

cv2.destroyAllWindows()
process.terminate()  # Zakończ proces libcamera-vid
print(f'Captured {image_count - existing_images} new images. Total images: {image_count}')
