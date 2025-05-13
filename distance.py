import numpy as np

def calculate_marker_distance_from_camera(tVecs, marker_ids):
    """
    Calculate distance based on the translation vector (Euclidean distance).
    
    Args:
        tVecs: Translation vector for a single marker (from aruco.estimatePoseSingleMarkers).
        marker_ids: ID of the marker.
    
    Returns:
      (KROTKA PO POLSKU)  tuple: (distance, display_text) where distance is in centimeters.
    """
    # Sprawdzenie, czy argumenty nie są None
    if tVecs is None or marker_ids is None:
        return None, "Brak markera"

    # Oblicz dystans euklidesowy: sqrt(x^2 + y^2 + z^2)
    # tVecs jest już pojedynczym wektorem [x, y, z], ponieważ przekazano tVec[0]
    distance = np.sqrt(np.sum(tVecs ** 2)) / 10  # Zakładam, że tVecs jest w mm, konwersja na cm
    display_text = f"ID: {marker_ids[0]}, Dist: {distance:.2f} cm"
    
    return distance, display_text
