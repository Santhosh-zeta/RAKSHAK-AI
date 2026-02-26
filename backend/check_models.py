import joblib
import os
import sys

models = [
    r"c:\Users\santh\OneDrive - vit.ac.in\Desktop\XXX\RAKSHAK-AI\backend\surveillance\ai_models\behavior_model.pkl",
    r"c:\Users\santh\OneDrive - vit.ac.in\Desktop\XXX\RAKSHAK-AI\backend\surveillance\ai_models\risk_model.pkl",
    r"c:\Users\santh\OneDrive - vit.ac.in\Desktop\XXX\RAKSHAK-AI\backend\surveillance\ai_models\route_model.pkl"
]

with open('results.txt', 'w', encoding='utf-8') as f:
    for m in models:
        f.write(f"\n--- Checking {os.path.basename(m)} ---\n")
        if not os.path.exists(m):
            f.write("File does not exist.\n")
            continue
        try:
            model = joblib.load(m)
            f.write("Successfully loaded using joblib.\n")
            f.write(f"Type: {type(model).__name__}\n")
            if hasattr(model, 'get_params'):
                f.write(f"Params keys: {list(model.get_params().keys())}\n")
        except Exception as e:
            f.write(f"Failed to load: {e}\n")
