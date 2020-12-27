import aiohttp
import functools
import hashlib
import hmac
import logging
import json
import os
import pyryver
import time
import typing
from aiohttp import web
from markdownify import markdownify
from . import github, schemas, trivia, util


logger = logging.getLogger("latexbot")


def basicauth(level: str, realm: str = None):
    """
    Use this decorator on web handlers to require basic auth.

    Level can be either "read", "write" or "admin".
    """
    def _basicauth_decor(func: typing.Callable[[web.Request], typing.Awaitable]):
        @functools.wraps(func)
        async def _basicauth(self, req: web.Request):
            authorized = False
            authenticated = False
            if "authorization" in req.headers:
                try:
                    auth = aiohttp.BasicAuth.decode(req.headers["authorization"])
                    if auth.password:
                        if auth.login == "admin":
                            if auth.password == os.environ.get("LATEXBOT_SERVER_AUTH_ADMIN"):
                                authorized = True
                        elif auth.login == "write":
                            if auth.password == os.environ.get("LATEXBOT_SERVER_AUTH_WRITE"):
                                authenticated = True
                                if level == "write" or level == "read":
                                    authorized = True
                        elif auth.login == "read":
                            if auth.password == os.environ.get("LATEXBOT_SERVER_AUTH_READ"):
                                authenticated = True
                                if level == "read":
                                    authorized = True
                except ValueError:
                    pass

            if not authorized:
                if authenticated:
                    return web.Response(body="You need a higher access level for this resource.", status=403)
                else:
                    auth = "Basic"
                    if realm is not None:
                        auth += f" realm=\"{realm}\""
                    return web.Response(body="Invalid credentials", status=401, headers={
                        "WWW-Authenticate": auth
                    })
            return await func(self, req)
        return _basicauth
    return _basicauth_decor


RESOURCE_DIR = os.path.join(os.path.dirname(__file__), "static")


class Server:
    """
    A class that starts a web server and processes webhooks.
    """

    def __init__(self, bot: "latexbot.LatexBot"):
        self.bot = bot
        self.app = None # type: web.Application()
        self.runner = None # type: web.AppRunner
        self.site = None # type: web.TCPSite
        if self.bot.user.get_id() in self.bot.user_info:
            self.icon_href = self.bot.user_info[self.bot.user.get_id()].avatar or ""
        else:
            self.icon_href = ""

    async def start(self, port: int = 80):
        """
        Start the server.
        """
        self.app = web.Application()
        router = self.app.router
        router.add_get("/", self._homepage_handler)
        router.add_get("/config", self._config_handler)
        router.add_get("/roles", self._roles_handler)
        router.add_get("/trivia", self._trivia_handler)
        router.add_get("/keyword_watches", self._keyword_watches_handler)
        router.add_get("/analytics", self._analytics_handler)
        router.add_get("/analytics-ui", self._analytics_ui_handler)
        router.add_post("/github", self._github_handler)
        router.add_post("/message", self._message_handler_post)
        router.add_get("/message", self._message_handler_get)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "0.0.0.0", port)
        await self.site.start()
        logger.info(f"Started web server on port {port}.")

    async def stop(self):
        """
        Stop the server.
        """
        await self.runner.cleanup()

    async def _github_handler(self, req: web.Request):
        """
        Handle a POST request coming from GitHub.
        """
        text = await req.text()
        if os.environ.get("LATEXBOT_GH_HOOK_SECRET"):
            if "X-Hub-Signature" not in req.headers:
                return web.Response(status=401, body="Missing signature")
            secret = os.environ["LATEXBOT_GH_HOOK_SECRET"]
            if not self.verify_signature(secret, req.headers["X-Hub-Signature"], text):
                return web.Response(status=401, body="Bad signature")
        data = json.loads(text)
        event = req.headers["X-GitHub-Event"]
        msg = github.format_gh_json(event, data)
        if msg and self.bot.config.gh_updates_chat is not None:
            await self.bot.config.gh_updates_chat.send_message(msg, self.bot.msg_creator)
        elif self.bot.config.gh_updates_chat is not None:
            logger.info(f"Unhandled GitHub event: {event}")

        # Process issues
        if self.bot.gh_issues_board:
            def format_task() -> typing.Tuple[str, str]:
                """
                Format an issue or PR into a task.

                Returns a tuple of (subject, body).
                """
                if "issue" in data:
                    obj = data["issue"]
                    obj_type = "Issue"
                else:
                    obj = data["pull_request"]
                    obj_type = "Pull Request"
                title = f"(#{obj['number']}) {obj['title']}"
                body = markdownify(obj["body"]) + f"\n\n*This {obj_type} is from [GitHub]({obj['html_url']}).*"
                return (title, body)

            def format_comment() -> str:
                """
                Format an issue or PR comment into a task comment body.
                """
                body = f"({data['comment']['id']}) {github.format_author(data['comment']['user'])} commented:\n\n"
                body += f"{markdownify(data['comment']['body'])}\n\n*This comment is from [GitHub]({data['comment']['html_url']}).*"
                return body

            async def find_or_create_category() -> pyryver.TaskCategory:
                """
                Find or create the category for the repository related to this event.
                """
                async for category in self.bot.gh_issues_board.get_categories():
                    if category.get_name() == data["repository"]["name"]:
                        return category

                # Create the category
                return await self.bot.gh_issues_board.create_category(data["repository"]["name"])

            async def find_or_create_task(category: pyryver.TaskCategory) -> pyryver.Task:
                """
                Find or create the task for this issue.
                """
                number = (data.get("issue") or data["pull_request"])["number"]
                async for task in category.get_tasks():
                    if "latexbot-github" in task.get_tags() and task.get_subject().startswith(f"(#{number})"):
                        return task

                # Create the task if it doesn't already exist
                title, body = format_task()
                tag = "issue" if "issue" in data else "pull-request"
                return await self.bot.gh_issues_board.create_task(title, body, category, tags=["latexbot-github", tag])

            if (event == "issues" and data["action"] not in ("pinned", "unpinned", "milestoned", "demilestoned")
                or event == "pull_request" and data["action"] != "synchronize"):
                category = await find_or_create_category()
                if "issue" in data:
                    obj_type = "Issue"
                else:
                    obj_type = "Pull Request"

                # This will create the task if it doesn't already exist
                # so no need to handle the "created" action
                task = await find_or_create_task(category)
                if data["action"] == "edited":
                    title, body = format_task()
                    await task.edit(title, body)
                elif data["action"] == "deleted" or data["action"] == "transferred":
                    await task.delete()
                elif data["action"] == "closed":
                    if "issue" in data:
                        await task.comment(f"*Issue closed by {github.format_author(data['sender'])}.*")
                    else:
                        if data["pull_request"]["merged"]:
                            await task.comment(f"*Pull Request merged by {github.format_author(data['sender'])}.*")
                        else:
                            await task.comment(f"*Pull Request closed with unmerged commits by {github.format_author(data['sender'])}.*")
                    await task.complete()
                    await task.archive()
                elif data["action"] == "reopened":
                    await task.comment(f"*{obj_type} reopened by {github.format_author(data['sender'])}.*")
                    await task.uncomplete()
                    await task.unarchive()
                elif data["action"] == "assigned":
                    user = self.bot.ryver.get_user(username=self.bot.config.gh_users_map.get(data["assignee"]["login"], ""))
                    if not user:
                        logger.warning(f"{obj_type} assignment could not be updated: Ryver user for {data['assignee']['login']} not found.")
                    else:
                        assignees = await task.get_assignees()
                        if user not in assignees:
                            assignees.append(user)
                            await task.edit(assignees=assignees)
                elif data["action"] == "unassigned":
                    user = self.bot.ryver.get_user(username=self.bot.config.gh_users_map.get(data["assignee"]["login"], ""))
                    if not user:
                        logger.warning(f"{obj_type} assignment could not be updated: Ryver user for {data['assignee']['login']} not found.")
                    else:
                        assignees = await task.get_assignees()
                        if user in assignees:
                            assignees.remove(user)
                            await task.edit(assignees=assignees)
                elif data["action"] == "labeled":
                    # Ryver task labels cannot contain spaces
                    label = data["label"]["name"].replace(" ", "-")
                    labels = task.get_tags()
                    if label not in labels:
                        labels.append(label)
                        await task.edit(tags=labels)
                elif data["action"] == "unlabeled":
                    # Ryver task labels cannot contain spaces
                    label = data["label"]["name"].replace(" ", "-")
                    labels = task.get_tags()
                    if label in labels:
                        labels.remove(label)
                        await task.edit(tags=labels)
                elif data["action"] == "locked" or data["action"] == "unlocked":
                    await task.comment(f"*Conversation {data['action']} by {github.format_author(data['sender'])}.*")
                elif data["action"] == "review_requested":
                    await task.comment(f"*{github.format_author(data['sender'])} requested a review from {github.format_author(data['requested_reviewer'])}.*")
                elif data["action"] == "review_request_removed":
                    await task.comment(f"*{github.format_author(data['sender'])} is no longer requesting reviews from {github.format_author(data['requested_reviewer'])}.*")
                elif data["action"] == "ready_for_review":
                    await task.comment(f"*Marked as ready for review by {github.format_author(data['sender'])}.*")
            elif event == "issue_comment" or event == "pull_request_review_comment":
                task = await find_or_create_task(await find_or_create_category())
                if data["action"] == "created":
                    await task.comment(format_comment())
                else:
                    # Find the comment
                    comment = None
                    async for cmt in task.get_comments():
                        if cmt.get_body().startswith(f"({data['comment']['id']})"):
                            comment = cmt
                            break
                    else:
                        logger.error(f"Cannot handle {event}: Comment not found: {data['comment']['id']}")
                    if comment:
                        if data["action"] == "deleted":
                            await comment.delete()
                        if data["action"] == "edited":
                            await comment.edit(format_comment())
            elif event == "pull_request_review":
                task = await find_or_create_task(await find_or_create_category())
                if data["review"]["state"] == "commented":
                    state = "commenting"
                elif data["review"]["state"] == "approved":
                    state = "approving these changes"
                elif data["review"]["state"] == "changes_requested":
                    state = "requesting changes"
                else:
                    state = "unknown action"
                body = f"*{github.format_author(data['sender'])} "
                if data["action"] == "submitted":
                    body += f"submitted [a review]({data['review']['html_url']}) "
                    body += f"**{state}***:\n\n{markdownify(data['review']['body'])}"
                    await task.comment(body)
                elif data["action"] == "edited":
                    body += f"edited [their review]({data['review']['html_url']}) "
                    body += f"**{state}***:\n\n{markdownify(data['review']['body'])}"
                    await task.comment(body)
                elif data["action"] == "dismissed":
                    body += f"dismissed {github.format_author(data['review']['user'])}'s [review]({data['review']['html_url']}).*"
                    await task.comment(body)
        return web.Response(status=204)

    async def _homepage_handler(self, req: web.Request): # pylint: disable=unused-argument
        """
        Handle a GET request to /.
        """
        daily_msg_status = "\U0001F534 NOT SCHEDULED" if self.bot.daily_msg_task.done() else "\U0001F7E2 OK"
        start_time = self.bot.start_time.strftime(util.DATE_FORMAT)
        uptime = self.bot.current_time() - self.bot.start_time
        with open(os.path.join(RESOURCE_DIR, "home.html"), "r") as f:
            html = self.format_page(f.read().format(
                version=self.bot.version, server_status="\U0001F7E2 OK", daily_msg_status=daily_msg_status,
                start_time=start_time, uptime=uptime))
        return web.Response(text=html, status=200, content_type="text/html")

    @basicauth("read", "Configuration")
    async def _config_handler(self, req: web.Request): # pylint: disable=unused-argument
        """
        Handle a GET request to /config.
        """
        return web.json_response(schemas.config.dump(self.bot.config))

    @basicauth("read", "Roles")
    async def _roles_handler(self, req: web.Request): # pylint: disable=unused-argument
        """
        Handle a GET request to /roles.
        """
        try:
            with open(self.bot.roles_file, "r") as f:
                data = f.read()
        except FileNotFoundError:
            data = json.dumps(self.bot.roles.to_dict())
        # TODO: Use web.json_response()
        return web.Response(text=data, status=200, content_type="application/json")

    @basicauth("read", "Custom Trivia Questions")
    async def _trivia_handler(self, req: web.Request): # pylint: disable=unused-argument
        """
        Handle a GET request to /trivia.
        """
        try:
            with open(self.bot.trivia_file, "r") as f:
                data = f.read()
        except FileNotFoundError:
            data = json.dumps(trivia.CUSTOM_TRIVIA_QUESTIONS)
        return web.Response(text=data, status=200, content_type="application/json")

    @basicauth("read", "Keyword Watches")
    async def _keyword_watches_handler(self, req: web.Request): # pylint: disable=unused-argument
        """
        Handle a GET request to /keyword_watches.
        """
        try:
            with open(self.bot.watch_file, "r") as f:
                data = f.read()
        except FileNotFoundError:
            data = json.dumps(self.bot.keyword_watches)
        return web.Response(text=data, status=200, content_type="application/json")

    @basicauth("read", "Analytics")
    async def _analytics_handler(self, req: web.Request): # pylint: disable=unused-argument
        """
        Handle a GET request to /analytics.
        """
        if self.bot.analytics is None:
            return web.Response(text="Analytics are not enabled.", status=404)
        return web.Response(text=self.bot.analytics.dumps(), status=200, content_type="application/json")

    @basicauth("write", "Message Sending")
    async def _message_handler_post(self, req: web.Request):
        """
        Handle a POST request to /message.
        """
        args = await req.post()
        if "chat" not in args or "message" not in args:
            return web.Response(body="Missing param", status=400)
        try:
            chat = util.parse_chat_name(self.bot.ryver, args["chat"])
        except ValueError as e:
            return web.Response(body=str(e), status=400)

        if not chat:
            return web.Response(body="Chat not found", status=404)

        msg_id = await chat.send_message(args["message"])
        return web.Response(body=msg_id, status=200)

    @basicauth("write", "Message Sending")
    async def _message_handler_get(self, req: web.Request): # pylint: disable=unused-argument
        """
        Handle a GET request to /message.
        """
        with open(os.path.join(RESOURCE_DIR, "message.html"), "r") as f:
            html = self.format_page(f.read(), "Send a message")
        return web.Response(text=html, status=200, content_type="text/html")

    @basicauth("read", "Analytics UI")
    async def _analytics_ui_handler(self, req: web.Request): # pylint: disable=unused-argument
        """
        Handle a GET request to /analytics-ui.
        """
        if self.bot.analytics is None:
            return web.Response(text="Analytics are not enabled.", status=404)
        cmd_usage = {
            cmd: {
                self.bot.ryver.get_user(id=user).get_username(): count
                for user, count in usage.items()}
            for cmd, usage in self.bot.analytics.command_usage.items()}
        msg_activity = {self.bot.ryver.get_user(id=user).get_username(): size
            for user, size in self.bot.analytics.message_activity.items()}
        with open(os.path.join(RESOURCE_DIR, "analytics-ui.html"), "r") as f, open(os.path.join(RESOURCE_DIR, "analytics-ui.js")) as s:
            html = self.format_page(f.read().format(data={
                "commandUsage": cmd_usage,
                "shutdowns": self.bot.analytics.shutdowns,
                "messageActivity": msg_activity,
                "timestamp": int(time.time())
            }, script=s.read()), "Analytics")
        return web.Response(text=html, status=200, content_type="text/html")

    @classmethod
    def verify_signature(cls, secret: str, signature: str, data: str) -> bool:
        """
        Verify a GitHub webhook signature.
        """
        if signature.startswith("sha1="):
            signature = signature[5:]
        digest = hmac.HMAC(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha1).hexdigest()
        return hmac.compare_digest(digest, signature)

    def format_page(self, body: str, title: str = None):
        """
        Format the HTML for a page.
        """
        if title is not None:
            title = title + " | LaTeX Bot " + self.bot.version
        else:
            title = "LaTeX Bot " + self.bot.version
        with open(os.path.join(RESOURCE_DIR, "template.html"), "r") as f:
            return f.read().format(title=title, icon_href=self.icon_href, body=body)


import latexbot # nopep8 # pylint: disable=unused-import
