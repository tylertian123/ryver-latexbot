import asyncio
import logging
import latexbot

LOGGING_LEVEL = logging.INFO

if __name__ == "__main__":
    handler = logging.StreamHandler()
    handler.setLevel(LOGGING_LEVEL)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))

    logger = logging.getLogger("latexbot")
    logger.setLevel(LOGGING_LEVEL)
    logger.addHandler(handler)

    # aiohttp access gets separate handler for different format since it already has enough info
    ah_handler = logging.StreamHandler()
    ah_handler.setLevel(LOGGING_LEVEL)
    ah_logger = logging.getLogger("aiohttp.access")
    ah_logger.setLevel(LOGGING_LEVEL)
    ah_logger.addHandler(ah_handler)

    asyncio.get_event_loop().run_until_complete(latexbot.main_coro())

