import cv2
import cv2.aruco as aruco

# Inicjalizacja słownika i parametrów detektora
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, parameters)

# Inicjalizacja kamery — VideoCapture 0 lub 'libcamerasrc' z GStreamer
cap = cv2.VideoCapture("/dev/video10")  # wirtualna kamera z libcamera

if not cap.isOpened():
    print("❌ Nie można otworzyć kamery.")
    exit()

print("✅ Kamera uruchomiona. Wciśnij 'q', aby zakończyć.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Nie udało się odczytać klatki.")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Wykryj markery
    corners, ids, rejected = detector.detectMarkers(gray)

    if ids is not None:
        aruco.drawDetectedMarkers(frame, corners, ids)
        for i in range(len(ids)):
            cv2.putText(frame, f"ID: {ids[i][0]}", 
                        tuple(corners[i][0][0].astype(int)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("ArUco Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Zwolnij zasoby
cap.release()
cv2.destroyAllWindows()
