#!/usr/bin/env python3
"""
collect_training_data.py — Collect System Data for ML Model Training

Collects system snapshots over extended periods (hours/days) to build
a comprehensive dataset for training an improved anomaly detection model.

Usage:
  # Collect for 1 hour
  python3 collect_training_data.py --hours 1
  
  # Collect for 8 hours (overnight)
  python3 collect_training_data.py --hours 8
  
  # Collect with progress updates every 10 samples
  python3 collect_training_data.py --hours 4 --checkpoint 10

"""

import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml_engine.historical_collector import HistoricalDataCollector
from agent.monitor import collect_snapshot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def collect_data_for_duration(hours=1, checkpoint_interval=100):
    """Collect system snapshots for specified duration"""
    
    collector = HistoricalDataCollector()
    
    total_seconds = hours * 3600
    start_time = time.time()
    sample_count = 0
    
    end_time = datetime.now() + timedelta(hours=hours)
    
    logger.info(f"{'='*70}")
    logger.info(f"🚀 Starting ML Training Data Collection")
    logger.info(f"{'='*70}")
    logger.info(f"📊 Duration: {hours} hour(s) ({total_seconds} seconds)")
    logger.info(f"⏱️  Will collect until: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📁 Output directory: {collector.data_dir}")
    logger.info(f"💾 Checkpoint interval: every {checkpoint_interval} samples")
    logger.info(f"{'='*70}\n")
    
    try:
        while (time.time() - start_time) < total_seconds:
            try:
                # Collect system snapshot
                snapshot = collect_snapshot()
                feature_vector = snapshot.to_feature_vector()
                
                # Add to collector
                collector.add_sample(feature_vector)
                sample_count += 1
                
                # Show progress
                if sample_count % checkpoint_interval == 0:
                    elapsed_seconds = time.time() - start_time
                    elapsed_minutes = elapsed_seconds / 60
                    remaining_seconds = total_seconds - elapsed_seconds
                    remaining_minutes = remaining_seconds / 60
                    
                    logger.info(
                        f"✅ {sample_count} samples collected | "
                        f"Elapsed: {elapsed_minutes:.1f}m | "
                        f"Remaining: {remaining_minutes:.1f}m"
                    )
                    
                    # Save checkpoint
                    collector.save_checkpoint()
                
                # Wait 5 seconds before next snapshot (default monitoring interval)
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error collecting snapshot: {e}")
                time.sleep(5)
        
    except KeyboardInterrupt:
        logger.warning("\n⏹️  Collection interrupted by user")
    
    finally:
        # Final checkpoint
        collector.save_checkpoint()
        
        elapsed = time.time() - start_time
        samples_per_minute = sample_count / (elapsed / 60) if elapsed > 0 else 0
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ Data Collection Complete!")
        logger.info(f"{'='*70}")
        logger.info(f"📊 Total samples collected: {sample_count}")
        logger.info(f"⏱️  Total time: {elapsed/60:.1f} minutes")
        logger.info(f"📈 Collection rate: {samples_per_minute:.1f} samples/min")
        logger.info(f"💾 Saved to: {collector.data_dir}")
        logger.info(f"\n🎯 Next step: python3 train_on_historical.py")
        logger.info(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Collect system data for ML model training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect for 1 hour
  python3 collect_training_data.py --hours 1
  
  # Collect overnight (8 hours)
  python3 collect_training_data.py --hours 8
  
  # Collect with frequent checkpoints
  python3 collect_training_data.py --hours 4 --checkpoint 50
        """
    )
    
    parser.add_argument(
        "--hours", 
        type=float, 
        default=1,
        help="Duration to collect data (hours). Default: 1"
    )
    
    parser.add_argument(
        "--checkpoint",
        type=int,
        default=100,
        help="Save checkpoint every N samples. Default: 100"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if args.hours <= 0:
        logger.error("❌ Hours must be positive")
        sys.exit(1)
    
    if args.checkpoint <= 0:
        logger.error("❌ Checkpoint interval must be positive")
        sys.exit(1)
    
    # Run collection
    try:
        collect_data_for_duration(hours=args.hours, checkpoint_interval=args.checkpoint)
    except Exception as e:
        logger.error(f"❌ Collection failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
