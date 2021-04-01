"""
The entry point of LaTeX Bot.
"""

import json
import logging
import os
import sys
from . import latexbot


__version__ = "v0.10.1-dev"

DATA_DIR = os.environ["LATEXBOT_DATA_DIR"]
if not DATA_DIR.endswith("/"):
    DATA_DIR += "/"
CONFIG_FILE = DATA_DIR + "config.json"
ROLES_FILE = DATA_DIR + "roles.json"
TRIVIA_FILE = DATA_DIR + "trivia.json"
ANALY_FILE = DATA_DIR + "analytics.json"
WATCH_FILE = DATA_DIR + "keyword_watches.json"


logger = logging.getLogger("latexbot")


async def main_coro():
    """
    Main LaTeX Bot coroutine.
    """
    logger.info("-------- Starting LaTeX Bot --------")
    debug = os.environ.get("LATEXBOT_DEBUG") == "1"
    if debug:
        logger.info("Debug mode is on")
    if os.environ.get("LATEXBOT_ORG") and os.environ.get("LATEXBOT_USER") and os.environ.get("LATEXBOT_PASSWORD"):
        org, user, password = os.environ["LATEXBOT_ORG"], os.environ["LATEXBOT_USER"], os.environ["LATEXBOT_PASSWORD"]
    else:
        if not os.environ.get("LATEXBOT_CREDENTIALS_JSON"):
            logger.error("No credentials! Set either LATEXBOT_CREDENTIALS_JSON to the path of a json containing the credentials, or LATEXBOT_ORG, LATEXBOT_USER and LATEXBOT_PASSWORD!")
            sys.exit(1)
        try:
            with open(os.environ["LATEXBOT_CREDENTIALS_JSON"], "r") as f:
                data = json.load(f)
            org, user, password = data["organization"], data["username"], data["password"]
        except (IOError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Cannot read credentials: {type(e).__name__}: {e}")
            sys.exit(1)
    bot = latexbot.LatexBot(__version__, debug=debug)
    await bot.init(org, user, password, DATA_DIR, "latexbot-")
    await bot.load_files(CONFIG_FILE, ROLES_FILE, TRIVIA_FILE, ANALY_FILE, WATCH_FILE)
    logger.info("Basic setup complete. Entering main loop...")
    await bot.run()
    logger.info("LaTeX Bot has been shut down. Goodbye.")
