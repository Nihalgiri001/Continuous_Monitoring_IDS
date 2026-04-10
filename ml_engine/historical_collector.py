"""
ml_engine/historical_collector.py — Historical Data Collection for ML Training

Collects system snapshots over extended periods and enables batch training
on large, diverse datasets for improved anomaly detection.
"""

import logging
import numpy as np
import joblib
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class HistoricalDataCollector:
    """Collects and manages system snapshots for ML model training"""
    
    def __init__(self, data_dir="ml_engine/data"):
        """Initialize the data collector"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped file for this collection session
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.samples_file = self.data_dir / f"samples_{timestamp}.npy"
        self.samples = []
        self.checkpoint_interval = 100  # Save every N samples
        
        logger.info(f"✅ Historical data collector initialized: {self.data_dir}")
    
    def add_sample(self, feature_vector: list[float]) -> None:
        """Add a single system snapshot to historical data"""
        self.samples.append(feature_vector)
    
    def get_sample_count(self) -> int:
        """Get number of samples collected"""
        return len(self.samples)
    
    def save_checkpoint(self) -> None:
        """Save collected samples to disk"""
        if self.samples:
            data = np.array(self.samples)
            np.save(self.samples_file, data)
            logger.info(f"💾 Saved {len(self.samples)} samples to {self.samples_file.name}")
    
    def load_all_samples(self) -> np.ndarray:
        """Load all historical sample files for training"""
        all_samples = []
        
        npy_files = sorted(self.data_dir.glob("*.npy"))
        
        if not npy_files:
            logger.warning(f"No sample files found in {self.data_dir}")
            return np.array([])
        
        for npy_file in npy_files:
            try:
                data = np.load(npy_file)
                all_samples.append(data)
                logger.info(f"📂 Loaded {len(data)} samples from {npy_file.name}")
            except Exception as e:
                logger.error(f"Failed to load {npy_file}: {e}")
        
        if all_samples:
            combined = np.vstack(all_samples)
            logger.info(f"📊 Total historical samples loaded: {len(combined)}")
            return combined
        
        return np.array([])
    
    def train_on_historical(self, contamination=0.01, n_estimators=100):
        """Train IsolationForest on all accumulated historical data"""
        from sklearn.ensemble import IsolationForest
        
        X = self.load_all_samples()
        
        if len(X) < 50:
            logger.error(f"❌ Insufficient samples ({len(X)}). Need at least 50 for training.")
            return None
        
        logger.info(f"🧠 Training IsolationForest on {len(X)} historical samples...")
        logger.info(f"   Features per sample: {X.shape[1]}")
        logger.info(f"   Expected anomaly rate: {contamination*100:.1f}%")
        
        try:
            model = IsolationForest(
                contamination=contamination,
                n_estimators=n_estimators,
                random_state=42,
                n_jobs=-1,
                verbose=0
            )
            
            model.fit(X)
            
            # Save model
            model_dir = self.data_dir.parent / "models"
            model_dir.mkdir(parents=True, exist_ok=True)
            model_path = model_dir / "historical_baseline.pkl"
            
            joblib.dump(model, model_path)
            
            logger.info(f"✅ Model trained & saved → {model_path}")
            logger.info(f"📈 Training statistics:")
            logger.info(f"   - Samples: {len(X)}")
            logger.info(f"   - Features: {X.shape[1]}")
            logger.info(f"   - Estimators: {n_estimators}")
            logger.info(f"   - Contamination: {contamination*100:.1f}%")
            
            return model
            
        except Exception as e:
            logger.error(f"❌ Model training failed: {e}", exc_info=True)
            return None
    
    def get_statistics(self) -> dict:
        """Get statistics about collected data"""
        X = self.load_all_samples()
        
        if len(X) == 0:
            return {"status": "no_data"}
        
        return {
            "total_samples": len(X),
            "features": X.shape[1],
            "mean": X.mean(axis=0).tolist(),
            "std": X.std(axis=0).tolist(),
            "min": X.min(axis=0).tolist(),
            "max": X.max(axis=0).tolist(),
        }


__all__ = ["HistoricalDataCollector"]
