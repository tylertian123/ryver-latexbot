"""
The entry point of LaTeX Bot.

Having a separate main.py to start running the application allows the latexbot
module to be fully loaded, which avoids some problems with circular dependencies.
"""

import asyncio
import latexbot
import os
import util


__version__ = "v0.7.0"

DATA_DIR = "data/"
CONFIG_FILE = DATA_DIR + "config.json"
ROLES_FILE = DATA_DIR + "roles.json"
TRIVIA_FILE = DATA_DIR + "trivia.json"

async def main():
    debug = os.environ.get("LATEXBOT_DEBUG", "0") != "0"
    
    bot = latexbot.LatexBot(__version__, debug)
    await bot.init(os.environ["LATEXBOT_ORG"], os.environ["LATEXBOT_USER"], os.environ["LATEXBOT_PASS"], 
                   DATA_DIR, "latexbot-")
    await bot.load_files(CONFIG_FILE, ROLES_FILE, TRIVIA_FILE)
    await bot.run()
    util.log("LaTeX Bot has been shut down. Goodbye.")

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
