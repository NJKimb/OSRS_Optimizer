"""
CLI script to sync all OSRS quests from the official OSRS Wiki API.
Usage:
    python -m app.scripts.sync_quests
"""
import sys
import time
import logging
from pathlib import Path

# Setup root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("sync_quests")

from app.services.quest_parser import sync_osrs_quests

def main():
    logger.info("Starting OSRS Wiki quest synchronization...")
    start_time = time.time()
    try:
        quests = sync_osrs_quests(save=True, reload_db=True)
        elapsed = time.time() - start_time
        logger.info(f"Successfully synchronized {len(quests)} quests in {elapsed:.2f} seconds!")
        
        # Display sample statistics
        with_reqs = sum(1 for q in quests if q.requirements.quests or q.requirements.skills)
        with_xp = sum(1 for q in quests if q.xp_rewards)
        logger.info(f"Quests with requirements: {with_reqs}/{len(quests)}")
        logger.info(f"Quests with XP rewards: {with_xp}/{len(quests)}")
    except Exception as e:
        logger.error(f"Failed to synchronize quests: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
