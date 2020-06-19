import aiohttp
import aiohttp.web
import github
import util


class Webhooks:
    """
    A class that starts a web server and processes webhooks.
    """

    def __init__(self, bot: "latexbot.LatexBot"):
        self.bot = bot
        self.app = None # type: aiohttp.web.Application()
        self.runner = None # type: aiohttp.web.AppRunner
        self.site = None # type: aiohttp.web.TCPSite
    
    async def start(self, port: int = 80):
        """
        Start the server.
        """
        self.app = aiohttp.web.Application()
        self.app.router.add_post("/github", self._github_handler)
        self.runner = aiohttp.web.AppRunner(self.app)
        await self.runner.setup()
        self.site = aiohttp.web.TCPSite(self.runner, "0.0.0.0", port)
        await self.site.start()
        util.log(f"Started web server on port {port}.")
    
    async def stop(self):
        """
        Stop the server.
        """
        await self.runner.cleanup()
    
    async def _github_handler(self, req: aiohttp.web.Request):
        """
        Handle a POST request coming from GitHub.
        """
        data = await req.json()
        event = req.headers["X-GitHub-Event"]
        msg = github.format_gh_json(event, data)
        if msg and self.bot.gh_updates_chat is not None:
            await self.bot.gh_updates_chat.send_message(msg, self.bot.msg_creator)
        else:
            util.log(f"Unhandled GitHub event: {event}")
        
        return aiohttp.web.Response(status=204)


import latexbot # nopep8 # pylint: disable=unused-import
