import aiohttp
import aiohttp.web
import config
import functools
import github
import hashlib
import hmac
import json
import os
import pyryver
import typing
import util


def basicauth(realm: str = None):
    """
    Use this decorator on web handlers to require basic auth.
    """
    def _basicauth_decor(func: typing.Callable[[aiohttp.web.Request], typing.Awaitable]):
        @functools.wraps(func)
        async def _basicauth(self, req: aiohttp.web.Request):
            if not os.environ.get("LATEXBOT_SERVER_AUTH"):
                return await func(self, req)
            
            if "authorization" not in req.headers or not verify_auth(req.headers["authorization"]):
                auth = "Basic"
                if realm is not None:
                    auth += f" realm=\"{realm}\""
                return aiohttp.web.Response(body="Invalid credentials", status=401, headers={
                    "WWW-Authenticate": auth
                })
            return await func(self, req)
        return _basicauth
    return _basicauth_decor


def verify_auth(auth: str) -> bool:
    """
    Verify basic auth.
    """
    try:
        basic_auth = aiohttp.BasicAuth.decode(auth)
        return basic_auth.login == "latexbot" and basic_auth.password == os.environ["LATEXBOT_SERVER_AUTH"]
    except ValueError:
        return False


class Server:
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
        self.app.router.add_get("/", self._homepage_handler)
        self.app.router.add_get("/config", self._config_handler)
        self.app.router.add_get("/roles", self._roles_handler)
        self.app.router.add_get("/trivia", self._trivia_handler)
        self.app.router.add_post("/github", self._github_handler)
        self.app.router.add_post("/message", self._message_handler_post)
        self.app.router.add_get("/message", self._message_handler_get)
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
        text = await req.text()
        if os.environ.get("LATEXBOT_GH_HOOK_SECRET"):
            if "X-Hub-Signature" not in req.headers:
                return aiohttp.web.Response(status=401, body="Missing signature")
            secret = os.environ["LATEXBOT_GH_HOOK_SECRET"]
            if not self.verify_signature(secret, req.headers["X-Hub-Signature"], text):
                return aiohttp.web.Response(status=401, body="Bad signature")
        data = json.loads(text)
        event = req.headers["X-GitHub-Event"]
        msg = github.format_gh_json(event, data)
        if msg and self.bot.gh_updates_chat is not None:
            await self.bot.gh_updates_chat.send_message(msg, self.bot.msg_creator)
        elif self.bot.gh_updates_chat is not None:
            util.log(f"Unhandled GitHub event: {event}")
        
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
                body = obj["body"] + f"\n\n*This {obj_type} is from [GitHub]({obj['html_url']}).*"
                return (title, body)
            
            def format_comment() -> str:
                """
                Format an issue or PR comment into a task comment body.
                """
                body = f"({data['comment']['id']}) {github.format_author(data['comment']['user'])} commented:\n\n"
                body += f"{data['comment']['body']}\n\n*This comment is from [GitHub]({data['comment']['html_url']}).*"
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
                    user = self.bot.ryver.get_user(username=config.gh_users_map.get(data["assignee"]["login"], ""))
                    if not user:
                        util.log(f"{obj_type} assignment could not be updated: Ryver user for {data['assignee']['login']} not found.")
                    else:
                        assignees = await task.get_assignees()
                        if user not in assignees:
                            assignees.append(user)
                            await task.edit(assignees=assignees)
                elif data["action"] == "unassigned":
                    user = self.bot.ryver.get_user(username=config.gh_users_map.get(data["assignee"]["login"], ""))
                    if not user:
                        util.log(f"{obj_type} assignment could not be updated: Ryver user for {data['assignee']['login']} not found.")
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
                        util.log(f"Cannot handle {event}: Comment not found: {data['comment']['id']}")
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
                body = f"*{github.format_author(data['sender'])} "
                if data["action"] == "submitted":
                    body += f"submitted [a review]({data['review']['html_url']}) "
                    body += f"**{state}***:\n\n{data['review']['body']}"
                    await task.comment(body)
                elif data["action"] == "edited":
                    body += f"edited [their review]({data['review']['html_url']}) "
                    body += f"**{state}***:\n\n{data['review']['body']}"
                    await task.comment(body)
                elif data["action"] == "dismissed":
                    body += f"dismissed {github.format_author(data['review']['user'])}'s [review]({data['review']['html_url']}).*"
                    await task.comment(body)
        return aiohttp.web.Response(status=204)
    
    async def _homepage_handler(self, req: aiohttp.web.Request): # pylint: disable=unused-argument
        """
        Handle a GET request to /.
        """
        GREEN_DOT = "\U0001F7E2"
        RED_DOT = "\U0001F534"
        msg = self.format_page(f"""
<h1>LaTeX Bot {self.bot.version}</h1>
<p>
    Server: {GREEN_DOT} OK<br/>
    Daily Message: {f"{RED_DOT} NOT SCHEDULED" if self.bot.daily_msg_task.done() else f"{GREEN_DOT} OK"}<br/>
    Started On: {self.bot.start_time.strftime(util.DATE_FORMAT)}<br/>
    Uptime: {util.current_time() - self.bot.start_time}<br/>
</p>
<p>
    <a href="/config">View Config</a><br/>
    <a href="/roles">View Roles</a><br/>
    <a href="/trivia">View Trivia</a><br/>
    <a href="https://github.com/tylertian123/ryver-latexbot/blob/master/usage_guide.md">Usage Guide</a><br/>
    <a href="/message">Send a message</a><br/>
</p>
        """)
        return aiohttp.web.Response(text=msg, status=200, content_type="text/html")
    
    @basicauth("Configuration")
    async def _config_handler(self, req: aiohttp.web.Request): # pylint: disable=unused-argument
        """
        Handle a GET request to /config.
        """
        return aiohttp.web.json_response(config.dump()[0])
    
    @basicauth("Roles")
    async def _roles_handler(self, req: aiohttp.web.Request): # pylint: disable=unused-argument
        """
        Handle a GET request to /roles.
        """
        with open(self.bot.roles_file, "r") as f:
            return aiohttp.web.Response(text=f.read(), status=200, content_type="application/json")
    
    @basicauth("Custom Trivia Questions")
    async def _trivia_handler(self, req: aiohttp.web.Request): # pylint: disable=unused-argument
        """
        Handle a GET request to /trivia.
        """
        with open(self.bot.trivia_file, "r") as f:
            return aiohttp.web.Response(text=f.read(), status=200, content_type="application/json")
    
    @basicauth("Message Sending")
    async def _message_handler_post(self, req: aiohttp.web.Request):
        """
        Handle a POST request to /message.
        """
        args = await req.post()
        if "chat" not in args or "message" not in args:
            return aiohttp.web.Response(body="Missing param", status=400)
        try:
            chat = util.parse_chat_name(self.bot.ryver, args["chat"])
        except ValueError as e:
            return aiohttp.web.Response(body=str(e), status=400)
        
        if not chat:
            return aiohttp.web.Response(body="Chat not found", status=404)
        
        msg_id = await chat.send_message(args["message"])
        return aiohttp.web.Response(body=msg_id, status=200)
    
    @basicauth("Message Sending")
    async def _message_handler_get(self, req: aiohttp.web.Request): # pylint: disable=unused-argument
        """
        Handle a GET request to /message.
        """
        msg = self.format_page(f"""
<h1>Send a message</h1>
<form action="/message" method="POST" target="result_frame">
    <label for="chat">To Chat:</label><br/>
    <input type="text" id="chat" name="chat" placeholder="name=Test"/><br/>
    <label for="message">Message:</label><br/>
    <input type="text" id="message" name="message"/><br/>
    <input type="submit" value="Send"/>
</form>
<p>
    Message ID:<br/>
    <iframe name="result_frame"/>
</p>
        """)
        return aiohttp.web.Response(text=msg, status=200, content_type="text/html")
    
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
        return f"""
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8"/>
        <title>{title or f"LaTeX Bot {self.bot.version}"}</title>
        <link rel="icon" type="image/png" href="{self.bot.user_avatars.get(self.bot.user.get_id(), "")}"/>
    </head>
    <body>
        {body}
    </body>
</html>
        """


import latexbot # nopep8 # pylint: disable=unused-import
