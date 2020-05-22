"""
The entry point of LaTeX Bot.

Having a separate main.py to start running the application allows the latexbot
module to be fully loaded, which avoids some problems with circular dependencies.
"""

import asyncio
import latexbot

asyncio.get_event_loop().run_until_complete(latexbot.main())
