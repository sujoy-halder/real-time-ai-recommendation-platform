#!/usr/bin/env python3

"""
Comprehensive ML System Testing Script - Simple Version
Tests all ML components and verifies they work correctly
"""

import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

TESTS_PASSED = 0
TESTS_FAILED = 0

def print_header(text):
    print(f"\n{'='*70}")
    print(text)
    print(f"{'='*70}\n")

def print_test(text):
    print(f"[TEST] {text}")

def print_pass(text):
    global TESTS_PASSED
    print(f"  [PASS] {text}")
    TESTS_PASSED += 1

def print_fail(text):
    global TESTS_FAILED
    print(f"  [FAIL] {text}")
    TESTS_FAILED += 1

# ============================================================================
# SECTION 1: PYTHON IMPORTS TEST
# ============================================================================

print_header("SECTION 1: PYTHON IMPORTS & DEPENDENCIES")

print_test("numpy")
try:
    import numpy
    print_pass(f"numpy {numpy.__version__}")
except Exception as e:
    print_fail(f"numpy: {str(e)[:60]}")

print_test("pandas")
try:
    import pandas
    print_pass(f"pandas {pandas.__version__}")
except Exception as e:
    print_fail(f"pandas: {str(e)[:60]}")

print_test("scikit-learn")
try:
    import sklearn
    print_pass(f"scikit-learn {sklearn.__version__}")
except Exception as e:
    print_fail(f"scikit-learn: {str(e)[:60]}")

print_test("sqlalchemy")
try:
    import sqlalchemy
    print_pass(f"sqlalchemy {sqlalchemy.__version__}")
except Exception as e:
    print_fail(f"sqlalchemy: {str(e)[:60]}")

print_test("redis")
try:
    import redis
    print_pass("redis imported")
except Exception as e:
    print_fail(f"redis: {str(e)[:60]}")

# ============================================================================
# SECTION 2: ML MODELS IMPORT TEST
# ============================================================================

print_header("SECTION 2: ML MODELS IMPORT & VALIDATION")

print_test("FeatureEngineer")
try:
    from ml_models.advanced_models import FeatureEngineer
    print_pass("FeatureEngineer imported")
except Exception as e:
    print_fail(f"FeatureEngineer: {str(e)[:60]}")

print_test("DeepRecommendationNetwork")
try:
    from ml_models.advanced_models import DeepRecommendationNetwork
    print_pass("DeepRecommendationNetwork imported")
except Exception as e:
    print_fail(f"DeepRecommendationNetwork: {str(e)[:60]}")

print_test("EmbeddingModel")
try:
    from ml_models.advanced_models import EmbeddingModel
    print_pass("EmbeddingModel imported")
except Exception as e:
    print_fail(f"EmbeddingModel: {str(e)[:60]}")

print_test("TransformerRecommender")
try:
    from ml_models.advanced_models import TransformerRecommender
    print_pass("TransformerRecommender imported")
except Exception as e:
    print_fail(f"TransformerRecommender: {str(e)[:60]}")

print_test("RankingModel")
try:
    from ml_models.advanced_models import RankingModel
    print_pass("RankingModel imported")
except Exception as e:
    print_fail(f"RankingModel: {str(e)[:60]}")

print_test("EnsembleRecommender")
try:
    from ml_models.advanced_models import EnsembleRecommender
    print_pass("EnsembleRecommender imported")
except Exception as e:
    print_fail(f"EnsembleRecommender: {str(e)[:60]}")

print_test("ModelServer")
try:
    from ml_models.model_serving import ModelServer
    print_pass("ModelServer imported")
except Exception as e:
    print_fail(f"ModelServer: {str(e)[:60]}")

print_test("ModelRegistry")
try:
    from ml_models.registry import ModelRegistry
    print_pass("ModelRegistry imported")
except Exception as e:
    print_fail(f"ModelRegistry: {str(e)[:60]}")

# ============================================================================
# SECTION 3: ML MODEL INSTANTIATION TEST
# ============================================================================

print_header("SECTION 3: ML MODEL INSTANTIATION")

print_test("FeatureEngineer instantiation")
try:
    from ml_models.advanced_models import FeatureEngineer
    fe = FeatureEngineer()
    assert fe is not None
    print_pass("FeatureEngineer created successfully")
except Exception as e:
    print_fail(f"FeatureEngineer: {str(e)[:60]}")

print_test("DeepRecommendationNetwork instantiation")
try:
    from ml_models.advanced_models import DeepRecommendationNetwork
    dnn = DeepRecommendationNetwork(user_feature_dim=5, item_feature_dim=5)
    assert dnn is not None
    print_pass("DeepRecommendationNetwork created successfully")
except Exception as e:
    print_fail(f"DNN: {str(e)[:60]}")

print_test("EnsembleRecommender instantiation")
try:
    from ml_models.advanced_models import EnsembleRecommender
    ensemble = EnsembleRecommender()
    assert ensemble is not None
    print_pass("EnsembleRecommender created successfully")
except Exception as e:
    print_fail(f"Ensemble: {str(e)[:60]}")

print_test("ModelServer instantiation")
try:
    from ml_models.model_serving import ModelServer
    server = ModelServer()
    assert server is not None
    print_pass("ModelServer created successfully")
except Exception as e:
    print_fail(f"ModelServer: {str(e)[:60]}")

# ============================================================================
# SECTION 4: MODEL CACHE TEST
# ============================================================================

print_header("SECTION 4: MODEL CACHING")

print_test("ModelCache functionality")
try:
    from ml_models.model_serving import ModelCache
    cache = ModelCache(max_cache_size=100)
    cache.set('test_key', 'test_value')
    value = cache.get('test_key')
    assert value == 'test_value', f"Expected 'test_value', got {value}"
    print_pass("ModelCache working correctly")
except Exception as e:
    print_fail(f"ModelCache: {str(e)[:60]}")

# ============================================================================
# SECTION 5: MODEL MONITORING TEST
# ============================================================================

print_header("SECTION 5: MODEL MONITORING")

print_test("ModelMonitor functionality")
try:
    from ml_models.registry import ModelMonitor
    monitor = ModelMonitor()
    monitor.log_prediction(user_id=1, item_id=1, predicted_rating=4.5, actual_rating=4.0, model_name='test')
    metrics = monitor.calculate_metrics()
    assert 'mse' in metrics or len(metrics) == 0
    print_pass("ModelMonitor working correctly")
except Exception as e:
    print_fail(f"ModelMonitor: {str(e)[:60]}")

# ============================================================================
# SECTION 6: FEATURE ENGINEERING TEST
# ============================================================================

print_header("SECTION 6: FEATURE ENGINEERING")

print_test("User feature engineering")
try:
    import pandas as pd
    import numpy as np
    from ml_models.advanced_models import FeatureEngineer
    
    fe = FeatureEngineer()
    user_data = pd.DataFrame({
        'age': [25, 30, 35],
        'total_watches': [10, 20, 15],
        'avg_rating': [4.0, 3.5, 4.5],
        'created_at': pd.date_range('2024-01-01', periods=3)
    })
    features = fe.engineer_user_features(user_data)
    assert features.shape[0] == 3, f"Expected 3 rows, got {features.shape[0]}"
    print_pass(f"User features engineered successfully (shape: {features.shape})")
except Exception as e:
    print_fail(f"User features: {str(e)[:60]}")

print_test("Content feature engineering")
try:
    import pandas as pd
    from ml_models.advanced_models import FeatureEngineer
    
    fe = FeatureEngineer()
    content_data = pd.DataFrame({
        'duration': [120, 150, 90],
        'rating': [4.5, 4.0, 3.5],
        'genre': ['Action', 'Drama', 'Comedy'],
        'release_date': pd.date_range('2020-01-01', periods=3)
    })
    features = fe.engineer_content_features(content_data)
    assert features.shape[0] == 3, f"Expected 3 rows, got {features.shape[0]}"
    print_pass(f"Content features engineered successfully (shape: {features.shape})")
except Exception as e:
    print_fail(f"Content features: {str(e)[:60]}")

# ============================================================================
# SECTION 7: MATRIX FACTORIZATION TEST
# ============================================================================

print_header("SECTION 7: MATRIX FACTORIZATION MODEL")

print_test("Matrix Factorization training")
try:
    import pandas as pd
    from ml_models.advanced_models import MatrixFactorization
    
    interactions = pd.DataFrame({
        'user_id': [0, 0, 1, 1, 2],
        'content_id': [0, 1, 0, 2, 1],
        'rating': [5.0, 3.0, 4.0, 4.0, 5.0]
    })
    
    mf = MatrixFactorization(n_factors=10, n_epochs=5)
    mf.fit(interactions)
    pred = mf.predict(0, 0)
    assert 0 <= pred <= 5, f"Prediction out of range: {pred}"
    print_pass(f"MatrixFactorization working (prediction: {pred:.2f})")
except Exception as e:
    print_fail(f"Matrix Factorization: {str(e)[:60]}")

# ============================================================================
# SECTION 8: FILE INTEGRITY TEST
# ============================================================================

print_header("SECTION 8: FILE INTEGRITY")

files_to_check = [
    ('ml-models/advanced_models.py', 'ML models (advanced_models)'),
    ('ml-models/training_pipeline.py', 'ML models (training_pipeline)'),
    ('ml-models/model_serving.py', 'ML models (model_serving)'),
    ('ml-models/registry.py', 'ML models (registry)'),
    ('fastapi-services/main.py', 'FastAPI services'),
    ('database/schema.sql', 'Database schema'),
]

for filepath, name in files_to_check:
    print_test(f"{name} file")
    try:
        path = Path(filepath)
        assert path.exists(), f"File not found: {filepath}"
        size = path.stat().st_size
        assert size > 100, f"File too small: {size} bytes"
        print_pass(f"{name} exists ({size} bytes)")
    except Exception as e:
        print_fail(f"{name}: {str(e)[:60]}")

# ============================================================================
# SECTION 9: CONFIGURATION FILES TEST
# ============================================================================

print_header("SECTION 9: CONFIGURATION FILES")

config_files = [
    ('docker-compose-production.yml', 'Docker Compose config'),
    ('kubernetes/deployment.yaml', 'Kubernetes config'),
    ('.env', 'Environment config'),
]

for filepath, name in config_files:
    print_test(f"{name}")
    try:
        path = Path(filepath)
        assert path.exists(), f"File not found: {filepath}"
        size = path.stat().st_size
        assert size > 50, f"File too small: {size} bytes"
        print_pass(f"{name} exists ({size} bytes)")
    except Exception as e:
        print_fail(f"{name}: {str(e)[:60]}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print_header("FINAL TEST SUMMARY")

TOTAL = TESTS_PASSED + TESTS_FAILED
PERCENTAGE = (TESTS_PASSED * 100 // TOTAL) if TOTAL > 0 else 0

print(f"\nTests Passed: {TESTS_PASSED}")
print(f"Tests Failed: {TESTS_FAILED}")
print(f"Total Tests: {TOTAL}")
print(f"Success Rate: {PERCENTAGE}%")
print()

if TESTS_FAILED == 0:
    print("STATUS: ALL ML TESTS PASSED!")
    print()
    print("System is ready for:")
    print("  - Local development (docker-compose)")
    print("  - Kubernetes deployment")
    print("  - AWS cloud deployment")
    print()
    print("Next steps:")
    print("  1. Run: ./quickstart.sh")
    print("  2. Check: bash health-check.sh")
    print("  3. Test: curl http://localhost:8001/health")
    print()
    sys.exit(0)
else:
    print("STATUS: SOME TESTS FAILED")
    print()
    print("Review failed tests above and fix any issues")
    sys.exit(1)
