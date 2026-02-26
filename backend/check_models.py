"""
check_models.py — Verify that all RAKSHAK AI .pkl model files load correctly.
Run from the backend/ directory:
    python check_models.py
"""
import joblib
import os
import sys
import numpy as np

# Locate models relative to this script (backend/surveillance/ai_models/)
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR  = os.path.join(BASE_DIR, 'surveillance', 'ai_models')

models = {
    'behavior_model': os.path.join(MODELS_DIR, 'behavior_model.pkl'),
    'risk_model':     os.path.join(MODELS_DIR, 'risk_model.pkl'),
    'route_model':    os.path.join(MODELS_DIR, 'route_model.pkl'),
}

lines = []

for name, path in models.items():
    lines.append(f'\n--- Checking {name} ({os.path.basename(path)}) ---')
    if not os.path.exists(path):
        msg = f'FILE MISSING: {path}'
        lines.append(msg)
        print(f'  ❌ {name}: {msg}')
        continue
    try:
        obj = joblib.load(path)
        t   = type(obj).__name__
        lines.append(f'Loaded OK  — type: {t}')
        print(f'  ✅ {name}: {t}')

        if isinstance(obj, dict):
            lines.append(f'Dict keys: {list(obj.keys())}')
            # Extra check for behavior model: extract and probe pipeline
            if 'pipeline' in obj:
                pipeline = obj['pipeline']
                n_feat   = obj.get('n_features', '?')
                lines.append(f'  pipeline: {type(pipeline).__name__}, n_features={n_feat}')
                print(f'     pipeline={type(pipeline).__name__}, n_features={n_feat}')
                # Quick smoke test with synthetic 11-feature array
                try:
                    test_x = np.zeros((1, int(n_feat) if isinstance(n_feat, int) else 11))
                    score  = pipeline.decision_function(test_x)[0]
                    lines.append(f'  pipeline smoke-test OK: score={score:.4f}')
                    print(f'     smoke-test OK: IF score={score:.4f}')
                except Exception as e:
                    lines.append(f'  pipeline smoke-test FAILED: {e}')
                    print(f'     smoke-test FAILED: {e}')
            if 'safe_corridors' in obj:
                lines.append(f'  safe_corridors: {len(obj["safe_corridors"])}')
                lines.append(f'  risk_zones:     {len(obj["risk_zones"])}')
                print(f'     safe_corridors={len(obj["safe_corridors"])}, risk_zones={len(obj["risk_zones"])}')
        elif hasattr(obj, 'nodes'):
            # pgmpy BayesianNetwork
            nodes = list(obj.nodes())
            lines.append(f'BN nodes: {nodes}')
            print(f'     pgmpy BN nodes: {nodes}')
    except Exception as e:
        lines.append(f'LOAD FAILED: {e}')
        print(f'  ❌ {name}: LOAD FAILED — {e}')

output = '\n'.join(lines)
results_path = os.path.join(BASE_DIR, 'results.txt')
with open(results_path, 'w', encoding='utf-8') as f:
    f.write(output)

print(f'\nResults written to {results_path}')
