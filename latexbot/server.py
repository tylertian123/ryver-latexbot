import aiohttp
import aiohttp.web
import config
import github
import hashlib
import hmac
import json
import os
import pyryver
import util


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
                async for task in category.get_tasks():
                    if "latexbot-github" in task.get_tags() and task.get_subject().startswith(f"(#{data['issue']['number']})"):
                        return task
                        
                # Create the task if it doesn't already exist
                title = f"(#{data['issue']['number']}) {data['issue']['title']}"
                body = data["issue"]["body"] + f"\n\n*This Task is from [GitHub]({data['issue']['html_url']}).*"
                return await self.bot.gh_issues_board.create_task(title, body, category, tags=["latexbot-github"])

            if event == "issues" and data["action"] not in ("pinned", "unpinned", "milestoned", "demilestoned"):
                category = await find_or_create_category()
                # Creating a new task
                if data["action"] == "opened":
                    title = f"(#{data['issue']['number']}) {data['issue']['title']}"
                    body = data["issue"]["body"] + f"\n\n*This Task is from [GitHub]({data['issue']['html_url']}).*"
                    await self.bot.gh_issues_board.create_task(title, body, category, tags=["latexbot-github"])
                else:
                    task = await find_or_create_task(category)
                    if data["action"] == "edited":
                        title = f"(#{data['issue']['number']}) {data['issue']['title']}"
                        body = data["issue"]["body"] + f"\n\n*This Task is from [GitHub]({data['issue']['html_url']}).*"
                        await task.edit(title, body)
                    elif data["action"] == "deleted" or data["action"] == "transferred":
                        await task.delete()
                    elif data["action"] == "closed":
                        await task.comment(f"*Issue closed by {github.format_author(data['sender'])}.*")
                        await task.complete()
                        await task.archive()
                    elif data["action"] == "reopened":
                        await task.comment(f"*Issue reopened by {github.format_author(data['sender'])}.*")
                        await task.uncomplete()
                        await task.unarchive()
                    elif data["action"] == "assigned":
                        user = self.bot.ryver.get_user(username=config.gh_users_map.get(data["assignee"]["login"], ""))
                        if not user:
                            util.log(f"Issue assignment could not be updated: Ryver user for {data['assignee']['login']} not found.")
                        else:
                            assignees = await task.get_assignees()
                            if user not in assignees:
                                assignees.append(user)
                                await task.edit(assignees=assignees)
                    elif data["action"] == "unassigned":
                        user = self.bot.ryver.get_user(username=config.gh_users_map.get(data["assignee"]["login"], ""))
                        if not user:
                            util.log(f"Issue assignment could not be updated: Ryver user for {data['assignee']['login']} not found.")
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
            elif event == "issue_comment":
                task = await find_or_create_task(await find_or_create_category())
                if data["action"] == "created":
                    body = f"({data['comment']['id']}) {github.format_author(data['comment']['user'])} commented:\n\n"
                    body += f"{data['comment']['body']}\n\n*This comment is from [GitHub]({data['comment']['html_url']}).*"
                    await task.comment(body)
                else:
                    # Find the comment
                    comment = None
                    async for cmt in task.get_comments():
                        if cmt.get_body().startswith(f"({data['comment']['id']})"):
                            comment = cmt
                            break
                    else:
                        util.log(f"Cannot handle issue_comment: Comment not found: {data['comment']['body']}")
                    
                    if comment:
                        if data["action"] == "deleted":
                            await comment.delete()
                        if data["action"] == "edited":
                            body = f"({data['comment']['id']}) {github.format_author(data['comment']['user'])} commented:\n\n"
                            body += f"{data['comment']['body']}\n\n*This comment is from [GitHub]({data['comment']['html_url']}).*"
                            await comment.edit(body)
        return aiohttp.web.Response(status=204)
    
    @classmethod
    def verify_signature(cls, secret: str, signature: str, data: str) -> bool:
        """
        Verify a GitHub webhook signature.
        """
        if signature.startswith("sha1="):
            signature = signature[5:]
        digest = hmac.HMAC(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha1).hexdigest()
        return hmac.compare_digest(digest, signature)


import latexbot # nopep8 # pylint: disable=unused-import
