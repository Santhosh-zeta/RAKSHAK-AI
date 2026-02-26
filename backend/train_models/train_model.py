import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import os

def train():
    # 1. Load the generated synthetic dataset
    dataset_path = 'behaviour_dataset.csv'
    print(f"Loading dataset from {dataset_path}...")
    
    try:
        df = pd.read_csv(dataset_path)
    except FileNotFoundError:
        print(f"Error: Could not find {dataset_path}. Please run generate_dataset.py first.")
        return
        
    # The BehaviourAgent expects these exact 5 features in this order:
    # [dwell_seconds, velocity_magnitude, confidence, is_near_door, time_of_day_hour]
    feature_cols = ['dwell_seconds', 'velocity_magnitude', 'confidence', 'is_near_door', 'time_of_day_hour']
    
    # We only train on "normal" data for an Isolation Forest in a real-world scenario,
    # but since Isolation Forest is unsupervised and handles contamination, we can 
    # just feed it the whole dataset and tell it that roughly ~5% are anomalies.
    X_train = df[feature_cols].values
    
    print(f"Dataset loaded. Total samples: {len(X_train)}")
    
    # 2. Initialize the Isolation Forest Model
    # contamination=0.05 because we generated ~5% anomalies in the synthetic data
    model = IsolationForest(
        n_estimators=100, 
        contamination=0.05, 
        random_state=42
    )

    # 3. Train the model
    print("Training Isolation Forest on 5 features...")
    model.fit(X_train)

    # 4. Save the model to the expected path
    os.makedirs("AI-models", exist_ok=True)
    model_path = "AI-models/behaviour_model.pkl"
    joblib.dump(model, model_path)
    print(f"Model saved successfully to {model_path}")
    print("The BehaviourAgent is now ready to use this model!")

if __name__ == "__main__":
    train()
