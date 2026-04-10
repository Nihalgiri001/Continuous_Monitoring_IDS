#!/usr/bin/env python3
"""
train_on_historical.py — Train ML Model on Collected Historical Data

Trains an improved IsolationForest anomaly detection model using
accumulated system snapshots collected over extended periods.

Usage:
  # Train on all collected data with default settings
  python3 train_on_historical.py
  
  # Train with custom contamination rate
  python3 train_on_historical.py --contamination 0.01
  
  # Train with more estimators (better but slower)
  python3 train_on_historical.py --estimators 200
  
  # Train and save with custom name
  python3 train_on_historical.py --output my_model.pkl

"""

import sys
import time
import logging
import argparse
import joblib
from pathlib import Path
import numpy as np

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml_engine.historical_collector import HistoricalDataCollector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def train_model_on_historical(
    contamination=0.01,
    n_estimators=100,
    output_path="ml_engine/models/historical_baseline.pkl",
    data_dir="ml_engine/data"
):
    """Train IsolationForest model on historical data"""
    
    logger.info(f"{'='*70}")
    logger.info(f"🤖 Training ML Model on Historical Data")
    logger.info(f"{'='*70}")
    
    # Initialize collector
    collector = HistoricalDataCollector(data_dir=data_dir)
    
    # Load all historical samples
    logger.info(f"📂 Loading data from: {data_dir}")
    X = collector.load_all_samples()
    
    if X is None or len(X) == 0:
        logger.error("❌ No historical data found!")
        logger.info(f"💡 First collect data with: python3 collect_training_data.py --hours 1")
        return False
    
    logger.info(f"✅ Loaded {len(X)} samples")
    
    # Get statistics
    stats = collector.get_statistics()
    logger.info(f"\n📊 Data Statistics:")
    logger.info(f"  Feature names: {', '.join(stats.keys())}")
    for feature_name, feature_stats in stats.items():
        logger.info(
            f"  {feature_name:20s} | "
            f"mean: {feature_stats['mean']:8.2f} | "
            f"std: {feature_stats['std']:8.2f} | "
            f"min: {feature_stats['min']:8.2f} | "
            f"max: {feature_stats['max']:8.2f}"
        )
    
    # Train model
    logger.info(f"\n🔧 Training IsolationForest:")
    logger.info(f"  Contamination: {contamination}")
    logger.info(f"  Estimators: {n_estimators}")
    logger.info(f"  Samples: {len(X)}")
    logger.info(f"  Features: {X.shape[1]}")
    
    train_start = time.time()
    
    try:
        from sklearn.ensemble import IsolationForest
        
        model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42,
            n_jobs=-1  # Use all cores
        )
        
        logger.info(f"\n⏳ Training... (this may take a minute)")
        model.fit(X)
        
        train_time = time.time() - train_start
        logger.info(f"✅ Training complete in {train_time:.2f} seconds\n")
        
        # Save model
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        joblib.dump(model, output_path)
        logger.info(f"💾 Model saved to: {output_path}")
        
        # Test scoring
        logger.info(f"\n🧪 Testing model predictions:")
        scores = model.predict(X)
        anomalies = (scores == -1).sum()
        normal = (scores == 1).sum()
        
        logger.info(f"  Normal samples: {normal} ({100*normal/len(scores):.1f}%)")
        logger.info(f"  Anomalies: {anomalies} ({100*anomalies/len(scores):.1f}%)")
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ Training Successful!")
        logger.info(f"{'='*70}")
        logger.info(f"📊 Model Quality: {normal/len(scores)*100:.1f}% normal baseline")
        logger.info(f"🎯 Ready for deployment!")
        logger.info(f"\n📝 To use this model, update ml_engine/detector.py:")
        logger.info(f"   Replace: load from 'ml_engine/models/baseline.pkl'")
        logger.info(f"   With: load from '{output_path}'")
        logger.info(f"{'='*70}\n")
        
        return True
        
    except ImportError:
        logger.error("❌ scikit-learn not installed. Please run:")
        logger.error("   pip install scikit-learn")
        return False
    except Exception as e:
        logger.error(f"❌ Training failed: {e}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Train ML model on historical system data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train with default settings (contamination=0.01, estimators=100)
  python3 train_on_historical.py
  
  # Train with lower contamination (fewer false positives)
  python3 train_on_historical.py --contamination 0.005
  
  # Train with more estimators (better but slower)
  python3 train_on_historical.py --estimators 200
  
  # Save to custom location
  python3 train_on_historical.py --output models/my_baseline.pkl
        """
    )
    
    parser.add_argument(
        "--contamination",
        type=float,
        default=0.01,
        help="Expected fraction of anomalies in data. Default: 0.01 (1%)"
    )
    
    parser.add_argument(
        "--estimators",
        type=int,
        default=100,
        help="Number of isolation trees. More = better but slower. Default: 100"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="ml_engine/models/historical_baseline.pkl",
        help="Output path for trained model. Default: ml_engine/models/historical_baseline.pkl"
    )
    
    parser.add_argument(
        "--data-dir",
        type=str,
        default="ml_engine/data",
        help="Directory containing historical data files. Default: ml_engine/data"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if args.contamination <= 0 or args.contamination >= 1:
        logger.error("❌ Contamination must be between 0 and 1 (exclusive)")
        sys.exit(1)
    
    if args.estimators <= 0:
        logger.error("❌ Estimators must be positive")
        sys.exit(1)
    
    # Run training
    success = train_model_on_historical(
        contamination=args.contamination,
        n_estimators=args.estimators,
        output_path=args.output,
        data_dir=args.data_dir
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
