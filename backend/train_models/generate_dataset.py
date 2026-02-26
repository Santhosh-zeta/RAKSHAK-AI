import pandas as pd
import numpy as np
import random
import os

def generate_synthetic_data(num_samples=10000, anomaly_ratio=0.05):
    """
    Generates synthetic tracking data for training the BehaviourAgent Isolation Forest model.
    Features: dwell_seconds, velocity_magnitude, confidence, is_near_door, time_of_day_hour
    """
    data = []
    
    num_anomalies = int(num_samples * anomaly_ratio)
    num_normal = num_samples - num_anomalies
    
    # 1. Generate NORMAL behavior
    for _ in range(num_normal):
        # Normal walking: low dwell time (0-15s), normal speed (0.5-2.0), high confidence
        dwell_seconds = np.random.exponential(scale=5.0) 
        dwell_seconds = min(dwell_seconds, 20.0) # Cap at 20s for normal
        
        velocity_magnitude = np.random.normal(loc=1.2, scale=0.3)
        velocity_magnitude = max(0.1, velocity_magnitude) # Must be positive
        
        confidence = np.random.uniform(0.7, 1.0)
        
        # Rarely near door if walking past
        is_near_door = 0.0
        
        # Day time mostly (e.g., 6 AM to 10 PM)
        time_of_day_hour = float(random.choice([h for h in range(6, 23)]))
        
        data.append({
            'label': 'normal',
            'dwell_seconds': round(dwell_seconds, 2),
            'velocity_magnitude': round(velocity_magnitude, 2),
            'confidence': round(confidence, 2),
            'is_near_door': is_near_door,
            'time_of_day_hour': time_of_day_hour
        })
        
    # 2. Generate ANOMALOUS behavior
    for _ in range(num_anomalies):
        anomaly_type = random.choice(['loitering', 'night_activity', 'loitering_near_door'])
        
        if anomaly_type == 'loitering':
            # High dwell time, low speed
            dwell_seconds = np.random.uniform(30.0, 120.0)
            velocity_magnitude = np.random.uniform(0.0, 0.3)
            confidence = np.random.uniform(0.6, 1.0)
            is_near_door = 0.0
            time_of_day_hour = float(random.choice(range(0, 24)))
            
        elif anomaly_type == 'night_activity':
            # Normal movement but at 2 AM
            dwell_seconds = np.random.uniform(0.0, 10.0)
            velocity_magnitude = np.random.uniform(0.8, 1.5)
            confidence = np.random.uniform(0.6, 1.0)
            is_near_door = 0.0
            time_of_day_hour = float(random.choice([23, 0, 1, 2, 3, 4, 5]))
            
        else: # loitering_near_door
            # Very high dwell time, near door
            dwell_seconds = np.random.uniform(25.0, 300.0)
            velocity_magnitude = np.random.uniform(0.0, 0.2)
            confidence = np.random.uniform(0.8, 1.0)
            is_near_door = 1.0
            time_of_day_hour = float(random.choice(range(0, 24)))
            
        data.append({
            'label': 'anomaly',
            'dwell_seconds': round(dwell_seconds, 2),
            'velocity_magnitude': round(velocity_magnitude, 2),
            'confidence': round(confidence, 2),
            'is_near_door': is_near_door,
            'time_of_day_hour': time_of_day_hour
        })
        
    # Shuffle the dataset
    random.shuffle(data)
    
    # Create DataFrame and save
    df = pd.DataFrame(data)
    output_path = 'behaviour_dataset.csv'
    df.to_csv(output_path, index=False)
    print(f"Dataset successfully generated and saved to {output_path}")
    print(f"Total samples: {len(df)} (Normal: {num_normal}, Anomalies: {num_anomalies})")
    
    return df

if __name__ == "__main__":
    generate_synthetic_data(num_samples=10000, anomaly_ratio=0.05)
