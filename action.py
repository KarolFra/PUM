import json

# Wczytaj mapę ID → akcja
with open("markers_map.json") as f:
    marker_actions = json.load(f)

# Przykładowa detekcja
if ids is not None:
    for i, marker_id in enumerate(ids.flatten()):
        print(f"Marker ID: {marker_id}")
        action = marker_actions.get(str(marker_id), "Brak przypisanej akcji")
        print(f"→ Akcja dla robota: {action}")
