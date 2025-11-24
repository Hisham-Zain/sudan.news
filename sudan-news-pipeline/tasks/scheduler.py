#!/usr/bin/env python3
"""
Sudan News Pipeline Scheduler

Uses APScheduler to run the pipeline at regular intervals.
This is suitable for development and testing. For production,
consider using cron jobs or a proper job scheduler.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

import config

# Setup logging
import platform
log_file_path = '/var/www/sudanese_news/shared/logs/scheduler.log' if platform.system() != 'Windows' else '../scheduler.log'
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_pipeline_job():
    """Job function to run the pipeline"""
    logger.info("Starting scheduled pipeline run")

    try:
        # Import here to avoid circular imports
        from src.run_pipeline import run_full_pipeline
        run_full_pipeline()
        logger.info("Scheduled pipeline run completed successfully")
    except Exception as e:
        logger.error(f"Scheduled pipeline run failed: {e}")

def main():
    """Main scheduler function"""
    logger.info("Starting Sudan News Pipeline Scheduler")
    logger.info(f"Pipeline will run every {config.SCHEDULER_INTERVAL_HOURS} hours")

    # Create scheduler
    scheduler = BlockingScheduler()

    # Add pipeline job
    scheduler.add_job(
        func=run_pipeline_job,
        trigger=IntervalTrigger(hours=config.SCHEDULER_INTERVAL_HOURS),
        id='pipeline_job',
        name='Run news aggregation and clustering pipeline',
        replace_existing=True
    )

    logger.info("Scheduler started. Press Ctrl+C to exit.")

    try:
        # Start the scheduler
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
        scheduler.shutdown()
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        scheduler.shutdown()
        sys.exit(1)

if __name__ == '__main__':
    main()

# Production cron job alternative:
#
# Add this to crontab (crontab -e):
#
# # Run pipeline every 6 hours
# 0 */6 * * * cd /path/to/sudan-news-pipeline && python src/run_pipeline.py run-once >> pipeline.log 2>&1
#
# Or use a process manager like systemd with a timer unit.
