"""
CLI script to sync all OSRS quests from the official OSRS Wiki API.
Usage:
    python -m scripts.sync_quests
"""

import sys
import time
import logging
from pathlib import Path

# Setup root logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("sync_quests")

from app.services.wiki.sync import sync_osrs_quests


def main():
    logger.info("Starting OSRS Wiki quest synchronization...")
    start_time = time.time()
    try:
        quests = sync_osrs_quests(save=True, reload_db=True)
        elapsed_seconds = time.time() - start_time
        logger.info(
            f"Successfully synchronized {len(quests)} quests in {elapsed_seconds:.2f} seconds!"
        )

        # Display sample statistics
        quests_with_requirements = sum(
            1
            for quest in quests
            if quest.requirements.quests or quest.requirements.skills
        )
        quests_with_xp = sum(1 for quest in quests if quest.xp_rewards)
        logger.info(
            f"Quests with requirements: {quests_with_requirements}/{len(quests)}"
        )
        logger.info(f"Quests with XP rewards: {quests_with_xp}/{len(quests)}")
    except Exception as error:
        logger.error(f"Failed to synchronize quests: {error}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
