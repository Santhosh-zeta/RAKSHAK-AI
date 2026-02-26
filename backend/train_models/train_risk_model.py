import pandas as pd
import numpy as np
import joblib
import os
from pgmpy.models import DiscreteBayesianNetwork
from pgmpy.estimators import MaximumLikelihoodEstimator

def main():
    csv_path = "/Users/pranav1718/RAKSHAK-AI/backend/train_models/AI-models/CSV-data/driver_behavior_route_anomaly_dataset_with_derived_features.csv"
    model_out_path = "/Users/pranav1718/RAKSHAK-AI/backend/surveillance/ai_models/risk_model.pkl"

    print("Loading data from:", csv_path)
    df = pd.read_csv(csv_path)

    print("Deriving mapping features for Bayesian Network...")
    
    # 1. TimeOfDay -> extracted from timestamp hour
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    night_hours = set(list(range(22, 24)) + list(range(0, 6)))
    df['TimeOfDay'] = df['hour'].apply(lambda h: 'night' if h in night_hours else 'day')

    # 2. RouteCompliance -> synthesized from route_deviation_score and geofencing_violation
    def map_route(row):
        # We assume geofencing_violation > 0 is major_off
        if row['geofencing_violation'] > 0 or row['route_deviation_score'] >= 0.7:
            return 'major_off'
        elif row['route_deviation_score'] >= 0.3 or row['route_anomaly'] > 0:
            return 'minor_off'
        else:
            return 'on_route'
    df['RouteCompliance'] = df.apply(map_route, axis=1)

    # 3. BehaviourRisk -> synthesized from anomalous_event and behavioral_consistency_index
    def map_behaviour(row):
        # Lower consistency is worse
        if row['anomalous_event'] > 0 and row['behavioral_consistency_index'] < 0.3:
            return 'critical'
        elif row['anomalous_event'] > 0 or row['behavioral_consistency_index'] < 0.6:
            return 'suspicious'
        else:
            return 'normal'
    df['BehaviourRisk'] = df.apply(map_behaviour, axis=1)

    # 4. TwinDeviation -> Synthesizing this from rpm and fuel consumption, as there is no true IoT data in this dataset
    def map_twin(row):
        if row['rpm'] > 6000 and row['fuel_consumption'] > 20:
            return 'critical'
        elif row['rpm'] > 4000 or (row['fuel_consumption'] > 15 and row['brake_usage'] > 8):
            return 'degraded'
        else:
            return 'nominal'
    df['TwinDeviation'] = df.apply(map_twin, axis=1)

    # 5. TheftRisk (Target) -> Synthesizing logical ground truth from the independent variables
    def assign_risk(row):
        score = 0
        if row['BehaviourRisk'] == 'critical': score += 3
        elif row['BehaviourRisk'] == 'suspicious': score += 1
        
        if row['TwinDeviation'] == 'critical': score += 3
        elif row['TwinDeviation'] == 'degraded': score += 1
        
        if row['RouteCompliance'] == 'major_off': score += 3
        elif row['RouteCompliance'] == 'minor_off': score += 1
        
        if row['TimeOfDay'] == 'night': score += 2
        
        if score >= 6: return 'critical'
        elif score >= 4: return 'high'
        elif score >= 2: return 'medium'
        else: return 'low'
    
    df['TheftRisk'] = df.apply(assign_risk, axis=1)

    # Keep only the columns the bayesian network needs
    training_data = df[['BehaviourRisk', 'TwinDeviation', 'RouteCompliance', 'TimeOfDay', 'TheftRisk']]

    print("\nDataset generated successfully mapping features to allowed categories:")
    print(training_data.head())
    
    print("\nTheftRisk Distribution:")
    print(training_data['TheftRisk'].value_counts())

    print("\nInitializing Bayesian Network...")
    model = DiscreteBayesianNetwork([
        ('BehaviourRisk', 'TheftRisk'),
        ('TwinDeviation', 'TheftRisk'),
        ('RouteCompliance', 'TheftRisk'),
        ('TimeOfDay', 'TheftRisk')
    ])

    print("Fitting model using Maximum Likelihood Estimator on generated data...")
    # Learning conditional probability distributions from the data
    model.fit(training_data, estimator=MaximumLikelihoodEstimator)

    # Ensure target directory exists
    os.makedirs(os.path.dirname(model_out_path), exist_ok=True)
    
    # Save Model
    joblib.dump(model, model_out_path)
    print(f"\nModel successfully trained and saved to: {model_out_path}")

if __name__ == "__main__":
    main()
