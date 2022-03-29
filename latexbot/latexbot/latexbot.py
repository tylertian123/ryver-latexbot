"""
This module contains the main LatexBot class.
"""

import aiohttp
import asyncio
import atexit
import datetime
import json
import logging
import marshmallow
import os
import pyryver
import random
import re
import signal
import time
import typing # pylint: disable=unused-import
from dataclasses import dataclass
from traceback import format_exc
from . import analytics, commands, schemas, server, trivia, util
from .aho_corasick import Automaton
from .cid import CaseInsensitiveDict
from .command import Command, CommandSet, CommandError
from .tba import TheBlueAlliance


logger = logging.getLogger("latexbot")


@dataclass(unsafe_hash=True, eq=False)
class UserInfo:
    """
    A class for storing additional runtime user info.
    """

    avatar: typing.Optional[str] = None
    presence: typing.Optional[str] = None
    last_activity: float = 0
    muted: typing.Optional[typing.Dict[int, asyncio.Task]] = None


# Global LatexBot instance
bot = None # type: LatexBot


class LatexBot:
    """
    An instance of LaTeX Bot.
    """

    def __init__(self, version: str, debug: bool = False):
        self.debug = debug
        if debug:
            self.version = version + f" (DEBUG: pyryver v{pyryver.__version__})"
        else:
            self.version = version
        self.enabled = True

        self.ryver = None # type: pyryver.Ryver
        self.session = None # type: pyryver.RyverWS
        self.username = None # type: str
        self.user = None # type: pyryver.User
        self.user_info = {} # type: typing.Dict[int, UserInfo]

        self.config_file = None # type: str
        self.config = None # type: schemas.Config
        self.gh_issues_board = None # type: pyryver.TaskBoard
        self.tba = None # type: TheBlueAlliance
        self.maintainer = None # type: pyryver.User

        self.roles_file = None # type: str
        self.roles = CaseInsensitiveDict()

        self.trivia_file = None # type: str
        self.trivia_games = {} # type: typing.Dict[int, trivia.LatexBotTriviaGame]

        self.analytics_file = None # type: str
        self.analytics = None # type: analytics.Analytics

        self.watch_file = None # type: str
        self.keyword_watches = None # type: typing.Dict[int, schemas.KeywordWatch]
        self.keyword_watches_automaton = None # type: Automaton

        self.daily_msg_task = None # type: typing.Awaitable

        self.commands = None # type: CommandSet
        self.help = None # typing.Dict[str, typing.List[typing.Tuple[str, str]]]
        self.command_help = {} # type: typing.Dict[str, str]

        self.msg_creator = pyryver.Creator("LaTeX Bot " + self.version)

        self.webhook_server = None # type: server.Webhooks

        self.start_time = None # type: datetime.datetime

        self.timeout_tasks = {} # type: typing.Dict[int, asyncio.Task]

        global bot # pylint: disable=global-statement
        bot = self

    def init_commands(self) -> None:
        """
        Initialize the command set.
        """
        self.commands = CommandSet()
        for name in dir(commands):
            obj = getattr(commands, name)
            if isinstance(obj, Command):
                self.commands.add_command(obj)
        # Set access levels for sub-commands
        self.commands.add_command(Command("trivia importCustomQuestions", None, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("trivia exportCustomQuestions", None, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("trivia end", None, Command.ACCESS_LEVEL_FORUM_ADMIN))
        self.commands.add_command(Command("setEnabled", None, Command.ACCESS_LEVEL_BOT_ADMIN))
        self.commands.add_command(Command("macro create", None, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("macro delete", None, Command.ACCESS_LEVEL_ORG_ADMIN))

    async def init(self, org: str, user: str, password: str, cache_dir: str, cache_prefix: str) -> None:
        """
        Initialize LaTeX Bot.

        Note: This does not load the configuration files.
        The files should be loaded with load_files() before run() is called.
        """
        self.username = user
        cache = pyryver.FileCacheStorage(cache_dir, cache_prefix)
        self.ryver = pyryver.Ryver(org=org, user=user, password=password, cache=cache)
        await self.ryver.load_missing_chats()
        self.user = self.ryver.get_user(username=self.username)
        self.maintainer = self.ryver.get_user(id=int(os.environ.get("LATEXBOT_MAINTAINER_ID", 0)))

        # Get user avatar URLs
        # This information is not included in the regular user info
        info = await self.ryver.get_info()
        for user in info["users"]:
            if user["id"] not in self.user_info:
                self.user_info[user["id"]] = UserInfo()
            self.user_info[user["id"]].avatar = user["avatarUrl"]

        if os.environ.get("LATEXBOT_TBA_KEY"):
            self.tba = TheBlueAlliance(os.environ.get("LATEXBOT_TBA_KEY"))

        self.init_commands()

    async def load_config(self, data: typing.Dict[str, typing.Any]) -> typing.Optional[str]:
        """
        Load the config from a dict.

        Returns an error message if there are errors, or None if no errors.
        """
        msg = ""
        try:
            self.config = schemas.config.load(data)
        except marshmallow.ValidationError as e:
            msg += "Encountered errors while loading the config JSON:\n"
            msg += util.format_validation_error(e)
            msg += "\n\nConfig will be loaded with those values set to their defaults.\n\n"
            try:
                # Ignore errors by loading only the valid data
                self.config = schemas.config.load(e.valid_data)
            except marshmallow.ValidationError:
                msg += "\n\nEncountered more errors trying to load the valid fields. Falling back to empty config."
                self.config = schemas.config.load({})
        # Extra step: Verify that the GitHub Issues chat has a task board with categories
        if self.config.gh_issues_chat is not None:
            self.gh_issues_board = await self.config.gh_issues_chat.get_task_board()
            # If it does not exist, then create it
            if self.gh_issues_board is None:
                self.gh_issues_board = await self.config.gh_issues_chat.create_task_board(pyryver.TaskBoard.BOARD_TYPE_BOARD)
            else:
                # If it exists then verify that it has categories
                if self.gh_issues_board.get_board_type() != pyryver.TaskBoard.BOARD_TYPE_BOARD:
                    self.gh_issues_board = None
                    msg += "Invalid GitHub task board: Task board have categories."
        return msg or None

    async def load_watches(self, data: typing.Dict[str, typing.Any]) -> typing.Optional[str]:
        """
        Load the keyword watches from a dict.

        Returns an error message if there are errors, or None if no errors.
        """
        self.keyword_watches = {}
        msg = ""
        for user, watches in data.items():
            try:
                self.keyword_watches[int(user)] = schemas.keyword_watch.load(watches)
            except marshmallow.ValidationError as e:
                msg += f"Encountered errors while loading keyword watches for user {user}:\n{util.format_validation_error(e)}"
        self.rebuild_automaton()
        return msg or None

    async def load_files(self, config_file: str, roles_file: str, trivia_file: str, analytics_file: str, watch_file: str) -> None:
        """
        Load all configuration files, including the config, roles and custom trivia.
        """
        self.config_file = config_file
        self.roles_file = roles_file
        self.trivia_file = trivia_file
        self.analytics_file = analytics_file
        self.watch_file = watch_file

        # Load config
        try:
            with open(config_file, "r") as f:
                err = await self.load_config(json.load(f))
            if err:
                logger.error(err)
                if self.maintainer is not None:
                    await self.maintainer.send_message(err, self.msg_creator)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            msg = f"Config does not exist or is not valid json: {e}. Falling back to empty config."
            logger.error(msg)
            if self.maintainer is not None:
                await self.maintainer.send_message(msg, self.msg_creator)
            await self.load_config({})

        # Load watches
        try:
            with open(watch_file, "r") as f:
                err = await self.load_watches(json.load(f))
            if err:
                logger.error(err)
                if self.maintainer is not None:
                    await self.maintainer.send_message(err, self.msg_creator)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            msg = f"Watches do not exist or is not valid json: {e}. Falling back to empty."
            logger.error(msg)
            if self.maintainer is not None:
                await self.maintainer.send_message(msg, self.msg_creator)
            await self.load_watches({})

        # Load roles
        try:
            with open(roles_file, "r") as f:
                self.roles = CaseInsensitiveDict(json.load(f))
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error while loading roles: {e}. Defaulting to {{}}.")
            if self.maintainer is not None:
                await self.maintainer.send_message(f"Error while loading roles: {e}. Defaulting to {{}}.", self.msg_creator)
            self.roles = CaseInsensitiveDict()

        # Load analytics
        if os.environ.get("LATEXBOT_ANALYTICS") == "1":
            try:
                with open(analytics_file, "r") as f:
                    self.analytics = schemas.analytics.load(json.load(f))
            except marshmallow.ValidationError as e:
                msg = f"Encountered errors while loading analytics:\n{util.format_validation_error(e)}"
                msg += "\n\nAnalytics data will be loaded with those values set to their defaults.\n\n"
                try:
                    self.analytics = schemas.analytics.load(e.valid_data)
                except marshmallow.ValidationError:
                    msg += "\n\nEncountered more errors trying to load the valid fields. Falling back to empty data."
                    self.analytics = schemas.analytics.load({})
                logger.error(msg)
                if self.maintainer is not None:
                    await self.maintainer.send_message(msg, self.msg_creator)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                msg = f"Analytics data does not exist or is not valid json: {e}. Falling back to empty."
                logger.error(msg)
                if self.maintainer is not None:
                    await self.maintainer.send_message(msg, self.msg_creator)
                self.analytics = analytics.Analytics({}, {}, [])
            # Register atexit and signal handlers for saving the analytics data
            # so no data loss occurs when latexbot is terminated unexpectedly
            atexit.register(self.save_analytics)
            def signal_handler(num, frame): # pylint: disable=unused-argument
                self.save_analytics()
                exit()
            signal.signal(signal.SIGABRT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

        # Load trivia
        try:
            with open(trivia_file, "r") as f:
                trivia.set_custom_trivia_questions(json.load(f))
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error while loading custom trivia questions: {e}.")
            if self.maintainer is not None:
                await self.maintainer.send_message(f"Error while loading custom trivia questions: {e}.", self.msg_creator)

    def save_config(self) -> None:
        """
        Save the current config to the config JSON.
        """
        with open(self.config_file, "w") as f:
            f.write(schemas.config.dumps(self.config))

    def save_roles(self) -> None:
        """
        Save the current roles to the roles JSON.
        """
        with open(self.roles_file, "w") as f:
            json.dump(self.roles.to_dict(), f)

    def save_analytics(self) -> None:
        """
        Save the analytics data to JSON.
        """
        with open(self.analytics_file, "w") as f:
            f.write(self.analytics.dumps())

    def save_watches(self) -> None:
        """
        Save the current keyword watches to the watches JSON.
        """
        data = {str(user): schemas.keyword_watch.dump(watches) for user, watches in self.keyword_watches.items()}
        with open(self.watch_file, "w") as f:
            json.dump(data, f)

    def update_help(self) -> None:
        """
        Re-generate the help text.
        """
        self.help, self.command_help = self.commands.generate_help_text(self.ryver)

    async def _daily_msg(self, init_delay: float = 0):
        """
        A task that sends the daily message after a delay.
        """
        cancelled = False
        try:
            await asyncio.sleep(init_delay)
            logger.info("Executing daily message routine...")
            await commands.command_daily_message(self, None, None, None, None)
            logger.info("Daily message was sent.")
        except asyncio.CancelledError:
            cancelled = True
        except Exception: # pylint: disable=broad-except
            exc = format_exc()
            logger.error(f"Daily message routine error: {exc}")
            if self.maintainer is not None:
                await self.maintainer.send_message(f"Exception while sending daily message:\n```\n{exc}\n```", self.msg_creator)
        finally:
            if not cancelled:
                self.schedule_daily_message()

    def schedule_daily_message(self):
        """
        Start the daily message task with the correct delay.
        """
        if self.daily_msg_task:
            self.daily_msg_task.cancel()

        if self.config.daily_message_time is None:
            logger.info("Daily message not scheduled because time isn't defined.")
            return
        now = self.current_time()
        # Get that time, today
        t = datetime.datetime.combine(now, self.config.daily_message_time, tzinfo=self.config.tzinfo)
        # If already passed, get that time the next day
        if t < now:
            t += datetime.timedelta(days=1)
        init_delay = (t - now).total_seconds()
        self.daily_msg_task = asyncio.create_task(self._daily_msg(init_delay))
        logger.info(f"Daily message re-scheduled, starting after {init_delay} seconds.")

    async def update_cache(self) -> None:
        """
        Update cached chat data.
        """
        old_users = set(user.get_id() for user in self.ryver.users)
        await self.ryver.load_chats()
        # Get user avatar URLs
        # This information is not included in the regular user info
        info = await self.ryver.get_info()
        for user in info["users"]:
            if user["id"] not in self.user_info:
                self.user_info[user["id"]] = UserInfo()
            self.user_info[user["id"]].avatar = user["avatarUrl"]
        # Send welcome message
        if self.config.welcome_message:
            new_users = [user for user in self.ryver.users if user.get_id() not in old_users]
            for new_user in new_users:
                msg = self.config.welcome_message.format(name=new_user.get_name(), username=new_user.get_username())
                await new_user.send_message(msg, self.msg_creator)

    def rebuild_automaton(self) -> None:
        """
        Rebuild the DFA used for keyword searching in messages using Aho-Corasick.
        """
        dfa = Automaton()
        keywords = {}
        # Gather up all the keywords
        for user, watches in self.keyword_watches.items():
            if not watches.on:
                continue
            for keyword in watches.keywords:
                if keyword.keyword not in keywords:
                    keywords[keyword.keyword] = []
                # Each keyword has a list of users and whether it should match case and whole words
                keywords[keyword.keyword].append((user, keyword.match_case, keyword.whole_word))
        for k, v in keywords.items():
            dfa.add_str(k.lower(), (k, v))
        dfa.build_automaton()
        self.keyword_watches_automaton = dfa

    async def get_replace_message_creator(self, msg: pyryver.Message) -> pyryver.Creator:
        """
        Get the Creator object that can be used for replacing a message.
        """
        # Get the creator
        msg_creator = msg.get_creator()
        # If no creator then get author
        if not msg_creator:
            # First attempt to search for the ID in the list
            # if that fails then get it directly using a request
            msg_author = self.ryver.get_user(id=msg.get_author_id()) or (await msg.get_author())
            info = self.user_info.get(msg_author.get_id())
            avatar = "" if info is None or info.avatar is None else info.avatar
            msg_creator = pyryver.Creator(msg_author.get_name(), avatar)
        return msg_creator

    def preprocess_command(self, command: str, is_dm: bool) -> typing.Optional[typing.Tuple[str, str]]:
        """
        Preprocess a command.

        Separate the command into the command name and args and resolve aliases
        if it is a command. Otherwise return None.

        If it encouters a recursive alias, it raises ValueError.
        """
        for prefix in self.config.command_prefixes:
            # Check for a valid command prefix
            if command.startswith(prefix) and len(command) > len(prefix):
                # Remove the prefix
                command = command[len(prefix):]
                break
        else:
            if command.startswith("@" + self.msg_creator.name + " "):
                command = command[len(self.msg_creator.name) + 2:]
            # DMs don't require command prefixes
            elif not is_dm:
                return None

        # Repeat until all aliases are expanded
        used_aliases = set()
        while True:
            # Separate command from args
            # Find the first whitespace
            command = command.strip()
            space = None
            # Keep track of this for alias expansion
            space_char = ""
            for i, c in enumerate(command):
                if c.isspace():
                    space = i
                    space_char = c
                    break

            if space:
                cmd = command[:space]
                args = command[space + 1:]
            else:
                cmd = command
                args = ""

            # Expand aliases
            command = None
            for alias in self.config.aliases:
                if alias.from_ == cmd:
                    # Check for recursion
                    if alias.from_ in used_aliases:
                        raise ValueError(f"Recursive alias: '{alias.from_}'!")
                    used_aliases.add(alias.from_)
                    # Expand the alias
                    command = alias.to + space_char + args
                    break
            # No aliases were expanded - return
            if not command:
                return (cmd.strip(), args.strip())
            # Otherwise go again until no more expansion happens

    def current_time(self) -> datetime.datetime:
        """
        Get the current time in the organization's timezone.
        """
        return datetime.datetime.now(datetime.timezone.utc).astimezone(self.config.tzinfo)

    async def run(self) -> None:
        """
        Run LaTeX Bot.
        """
        self.start_time = self.current_time()
        logger.info(f"LaTeX Bot {self.version} has been started. Initializing...")
        self.update_help()
        self.schedule_daily_message()
        # Start webhook server
        if os.environ.get("LATEXBOT_SERVER_PORT") or os.environ.get("LATEXBOT_SERVER") == "1":
            if os.environ.get("LATEXBOT_SERVER_PORT"):
                try:
                    port = int(os.environ["LATEXBOT_SERVER_PORT"])
                except ValueError as e:
                    logger.error(f"Invalid port specified: {e}. Defaulting to 80.")
                    port = 80
            else:
                port = 80
            logger.info(f"Starting server on port {port}")
            self.webhook_server = server.Server(self)
            await self.webhook_server.start(port or 80)
        # Start live session
        logger.info("Starting live session")
        async with self.ryver.get_live_session(auto_reconnect=True) as session: # type: pyryver.RyverWS
            logger.info("Initializing live session")
            self.session = session

            @session.on_connection_loss
            async def _on_conn_loss():
                logger.error(" Connection lost!")

            @session.on_reconnect
            async def _on_reconnect():
                logger.info("Reconnected!")

            @session.on_chat
            async def _on_chat(msg: pyryver.WSChatMessageData, is_edit: bool = False):
                # Ignore non-chat messages
                if msg.subtype != pyryver.ChatMessage.SUBTYPE_CHAT_MESSAGE:
                    return

                # Check the sender and destination
                to = self.ryver.get_chat(jid=msg.to_jid)
                from_user = self.ryver.get_user(jid=msg.from_jid)

                if to is None or from_user is None:
                    logger.warning("Received message from/to user/chat not in cache. Updating cache...")
                    await self.update_cache()
                    if to is None:
                        to = self.ryver.get_chat(jid=msg.to_jid)
                    if from_user is None:
                        from_user = self.ryver.get_user(jid=msg.from_jid)
                    if to is None or from_user is None:
                        logger.error("Still not found after cache update. Command skipped.")
                        return

                # Ignore messages sent by us
                if from_user.get_username() == self.username:
                    return

                # Record activity
                if from_user.get_id() not in self.user_info:
                    self.user_info[from_user.get_id()] = UserInfo()
                self.user_info[from_user.get_id()].last_activity = time.time()

                # Check if this is a DM
                if isinstance(to, pyryver.User):
                    # For DMs special processing is required
                    # Since we don't want to reply to ourselves, reply to the sender directly instead
                    to = from_user
                    is_dm = True
                else:
                    is_dm = False

                # See if user is muted
                if from_user.get_id() in self.user_info:
                    muted = self.user_info[from_user.get_id()].muted
                    if muted is not None and to.get_id() in muted:
                        try:
                            msg_obj = await pyryver.retry_until_available(to.get_message, msg.message_id, retry_delay=0.1, timeout=5.0)
                            await msg_obj.delete()
                        except TimeoutError:
                            pass
                        return
                # See if chat is read-only and check roles if it is
                if to in self.config.read_only_chats and not from_user.is_admin() \
                    and not any(from_user.get_id() in bot.roles.get(role, ())
                                for role in self.config.read_only_chats[to]):
                    try:
                        text = msg.text
                        msg_obj = await pyryver.retry_until_available(to.get_message, msg.message_id, retry_delay=0.1, timeout=5.0)
                        await msg_obj.delete()
                        await from_user.send_message(f"Sorry, your message to {to.get_name()} was deleted because {to.get_name()} is a read-only chat. Here is the removed message:", bot.msg_creator)
                        await from_user.send_message(text, bot.msg_creator)
                    except TimeoutError:
                        pass
                    return

                if not is_dm and self.analytics is not None and not is_edit:
                    self.analytics.message(msg.text, from_user)

                try:
                    preprocessed = self.preprocess_command(msg.text, is_dm)
                except ValueError as e:
                    # Skip if not self.
                    if self.enabled:
                        await to.send_message(f"Cannot process command: {e}", self.msg_creator)
                    return

                if preprocessed:
                    command, args = preprocessed
                    # Processing for re-enabling after disable
                    if (command == "setEnabled" and args == "true") or command == "wakeUp":
                        if not await self.commands.commands["setEnabled"].is_authorized(self, to, from_user):
                            message = random.choice(self.config.access_denied_messages) if self.config.access_denied_messages else "Access denied."
                            await to.send_message(message, self.msg_creator)
                            return
                        if self.analytics:
                            self.analytics.command(command, args, from_user, to)
                        # Send the presence change anyways in case it gets messed up
                        await session.send_presence_change(pyryver.RyverWS.PRESENCE_AVAILABLE)
                        if not self.enabled:
                            self.enabled = True
                            logger.info(f"Re-enabled by user {from_user.get_name()}!")
                            await to.send_message("I have been re-enabled!", self.msg_creator)
                        else:
                            await to.send_message("I'm already enabled.", self.msg_creator)
                        return
                    elif command == "setEnabled" and args == "false" and self.enabled:
                        if not await self.commands.commands["setEnabled"].is_authorized(self, to, from_user):
                            message = random.choice(self.config.access_denied_messages) if self.config.access_denied_messages else "Access denied."
                            await to.send_message(message, self.msg_creator)
                            return
                        if self.analytics:
                            self.analytics.command(command, args, from_user, to)
                        self.enabled = False
                        logger.info(f"Disabled by user {from_user.get_name()}.")
                        await to.send_message("I have been disabled.", self.msg_creator)
                        await session.send_presence_change(pyryver.RyverWS.PRESENCE_AWAY)
                        return

                    if not self.enabled:
                        return
                    if is_dm:
                        logger.info(f"DM {'edited' if is_edit else 'received'} from {from_user.get_name()}: {msg.text}")
                    else:
                        logger.info(f"Command {'edited' if is_edit else 'received'} from {from_user.get_name()} to {to.get_name()}: {msg.text}")

                    async with session.typing(to):
                        if command in self.commands.commands:
                            if is_dm and self.analytics is not None:
                                self.analytics.message(msg.text, from_user)
                            try:
                                if not await self.commands.process(command, args, self, to, from_user, msg.message_id):
                                    message = random.choice(self.config.access_denied_messages) if self.config.access_denied_messages else "Access denied."
                                    await to.send_message(message, self.msg_creator)
                                    logger.info("Access Denied")
                                else:
                                    if self.analytics:
                                        self.analytics.command(command, args, from_user, to)
                                    logger.info("Command processed.")
                            except CommandError as e:
                                logger.info(f"Command error: {e}")
                                await to.send_message(f"Error: {e}", bot.msg_creator)
                            except Exception as e: # pylint: disable=broad-except
                                exc = format_exc()
                                logger.error(f"Exception raised:\n{exc}")
                                await to.send_message(f"An exception occurred while processing the command:\n```{exc}\n```\n\nPlease try again.", self.msg_creator)
                                if self.maintainer is not None:
                                    await self.maintainer.send_message(f"An exception occurred while processing command `{msg.text}` in {to.get_name()}:\n```\n{exc}\n```", self.msg_creator)
                        else:
                            logger.info("Invalid command.")
                            await to.send_message("Sorry, I didn't understand what you were asking me to do.", self.msg_creator)
                # Not a command
                else:
                    # Replace roles + macros
                    def role_replace_func(match: re.Match):
                        # First capture group is character in front of @ and the @ itself
                        prefix = match.group(1)
                        name = match.group(2)
                        if name in self.roles:
                            name = " @".join(self.ryver.get_user(id=user).get_username() for user in self.roles[name])
                        return prefix + name
                    def macro_replace_func(match: re.Match):
                        prefix = match.group(1)
                        macro = match.group(2)
                        if macro in self.config.macros:
                            return prefix + self.config.macros[macro]
                        return prefix + "." + macro
                    new_text = util.MENTION_REGEX.sub(role_replace_func, msg.text)
                    new_text = util.MACRO_REGEX.sub(macro_replace_func, new_text)
                    # Replace the message if changed
                    if new_text != msg.text:
                        msg.text = new_text
                        async with session.typing(to):
                            try:
                                # Get the message object
                                msg_obj = (await pyryver.retry_until_available(to.get_message, msg.message_id, timeout=5.0))
                                # Pretend to be the creator
                                msg_creator = await self.get_replace_message_creator(msg_obj)
                                await to.send_message(msg.text, msg_creator)
                            except TimeoutError:
                                pass
                        # Can't delete the other person's messages in DMs, so skip
                        if not is_dm:
                            await msg_obj.delete()

                    # Search for keyword matches
                    notify_users = dict() # type: typing.Dict[int, typing.Set[str]]
                    for i, (keyword, users) in self.keyword_watches_automaton.find_all(msg.text.lower()):
                        for user, match_case, whole_word in users:
                            # Verify case matching
                            if match_case:
                                err = False
                                for j, c in enumerate(keyword):
                                    # Aho-Corasick returns rightmost char index
                                    if msg.text[i - len(keyword) + 1 + j] != c:
                                        err = True
                                        break
                                if err:
                                    continue
                            # Verify whole words
                            if whole_word:
                                # Check right boundary
                                if i != len(msg.text) - 1 and msg.text[i].isalnum() == msg.text[i + 1].isalnum():
                                    continue
                                # Check left boundary
                                l = i - len(keyword)
                                if l >= 0 and msg.text[l].isalnum() == msg.text[l + 1].isalnum():
                                    continue
                            # Record match
                            if user not in notify_users:
                                notify_users[user] = set()
                            notify_users[user].add(keyword)
                    # Notify the users
                    if notify_users:
                        quoted_msg = f"> *{from_user.get_name()}* said in *{to.get_name()}*:"
                        for line in msg.text.splitlines():
                            quoted_msg += "\n> " + line
                        t = time.time()
                        for uid, keywords in notify_users.items():
                            # Check if it's from the same user
                            if from_user.get_id() == uid:
                                continue
                            if uid in self.user_info:
                                # Check user presence
                                if self.user_info[uid].presence == pyryver.RyverWS.PRESENCE_AVAILABLE:
                                    continue
                                # Check user last activity
                                if t - self.user_info[uid].last_activity < self.keyword_watches[uid].activity_timeout:
                                    continue
                            # Check suppression
                            if (self.keyword_watches[uid].suppressed or 0) > t:
                                continue
                            # Verify that the user is a member of this chat
                            if isinstance(to, pyryver.GroupChat) and await to.get_member(uid) is None:
                                continue
                            user = self.ryver.get_user(id=uid)
                            resp = "The following message matched your watches for the keyword(s) " + ", ".join(f"\"**{w}**\"""" for w in keywords) + ":"
                            await user.send_message(resp + "\n" + quoted_msg, self.msg_creator)

            @session.on_chat_updated
            async def _on_chat_updated(msg: pyryver.WSChatUpdatedData):
                # Sometimes updates are sent for things other than message edits
                if msg.text is None:
                    return
                await _on_chat(msg, is_edit=True)

            @session.on_event(pyryver.RyverWS.EVENT_REACTION_ADDED)
            async def _on_reaction_added(msg: pyryver.WSEventData):
                # Extra processing for interfacing trivia with reactions
                await commands.reaction_trivia(self, self.ryver, session, msg.event_data)

            @session.on_presence_changed
            async def _on_presence_changed(msg: pyryver.WSPresenceChangedData):
                # Keep track of user presences
                user = self.ryver.get_user(jid=msg.from_jid)
                if user.get_id() not in self.user_info:
                    self.user_info[user.get_id()] = UserInfo()
                self.user_info[user.get_id()].presence = msg.presence

            if not self.debug and self.config.home_chat is not None:
                await asyncio.sleep(5)
                logger.info("Sending startup message...")
                try:
                    await session.send_presence_change(pyryver.RyverWS.PRESENCE_AVAILABLE)
                    logger.info("Presence change sent.")
                    await self.config.home_chat.send_message(f"LaTeX Bot {self.version} is online!", self.msg_creator)
                except (pyryver.WSConnectionError, aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.error(f"Exception during startup routine: {format_exc()}")

            logger.info("LaTeX Bot is running!")
            await session.run_forever()

    async def shutdown(self):
        """
        Stop running LaTeX Bot.
        """
        await self.webhook_server.stop()
        await self.session.terminate()
