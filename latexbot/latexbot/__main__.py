import asyncio
import logging
import latexbot
from . import loghandler

LOGGING_LEVEL = logging.INFO

if __name__ == "__main__":
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")

    handler = logging.StreamHandler()
    handler.setLevel(LOGGING_LEVEL)
    handler.setFormatter(fmt)

    queue_handler = loghandler.CircularLogHandler(loghandler.global_log_queue)
    queue_handler.setLevel(LOGGING_LEVEL)
    queue_handler.setFormatter(fmt)

    logger = logging.getLogger("latexbot")
    logger.setLevel(LOGGING_LEVEL)
    logger.addHandler(handler)
    logger.addHandler(queue_handler)

    # aiohttp access gets separate handler for different format since it already has enough info
    ah_handler = logging.StreamHandler()
    ah_handler.setLevel(LOGGING_LEVEL)
    ah_logger = logging.getLogger("aiohttp.access")
    ah_logger.setLevel(LOGGING_LEVEL)
    ah_logger.addHandler(ah_handler)

    asyncio.get_event_loop().run_until_complete(latexbot.main_coro())

