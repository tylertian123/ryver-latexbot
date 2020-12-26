"""
The entry point of LaTeX Bot.
"""

import os
from . import latexbot, util


__version__ = "v0.10.0-dev"

DATA_DIR = os.environ["LATEXBOT_DATA_DIR"]
if not DATA_DIR.endswith("/"):
    DATA_DIR += "/"
CONFIG_FILE = DATA_DIR + "config.json"
ROLES_FILE = DATA_DIR + "roles.json"
TRIVIA_FILE = DATA_DIR + "trivia.json"
ANALY_FILE = DATA_DIR + "analytics.json"
WATCH_FILE = DATA_DIR + "keyword_watches.json"

async def main_coro():
    """
    Main LaTeX Bot coroutine.
    """
    debug = os.environ.get("LATEXBOT_DEBUG") == "1"
    bot = latexbot.LatexBot(__version__, debug=debug)
    await bot.init(os.environ["LATEXBOT_ORG"], os.environ["LATEXBOT_USER"], os.environ["LATEXBOT_PASS"],
                   DATA_DIR, "latexbot-")
    await bot.load_files(CONFIG_FILE, ROLES_FILE, TRIVIA_FILE, ANALY_FILE, WATCH_FILE)
    await bot.run()
    util.log("LaTeX Bot has been shut down. Goodbye.")
