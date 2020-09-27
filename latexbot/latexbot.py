import analytics
import asyncio
import commands
import config
import server
import json
import os
import pyryver
import time
import trivia
import typing # pylint: disable=unused-import
import util
from aho_corasick import Automaton
from caseinsensitivedict import CaseInsensitiveDict
from command import Command, CommandSet
from datetime import datetime, timedelta
from gcalendar import Calendar
from tba import TheBlueAlliance
from traceback import format_exc


class LatexBot:
    """
    An instance of LaTeX Bot.
    """

    MACROS = {
        ".shrug": "\u00af\\\\_(\u30c4)\\_/\u00af",
        ".tableflip": "(\u256f\xb0\u25a1\xb0)\u256f\ufe35 \u253b\u2501\u253b",
        ".unflip": "\u252c\u2500\u252c\u30ce( \xba _ \xba\u30ce)",
        ".lenny": "( \u0361\xb0 \u035c\u0296 \u0361\xb0)",
        ".disapproval": "\u0ca0_\u0ca0",
        "/shrug": "\u00af\\\\_(\u30c4)\\_/\u00af",
        "/tableflip": "(\u256f\xb0\u25a1\xb0)\u256f\ufe35 \u253b\u2501\u253b",
        "/unflip": "\u252c\u2500\u252c\u30ce( \xba _ \xba\u30ce)",
        "/lenny": "( \u0361\xb0 \u035c\u0296 \u0361\xb0)",
        "/disapproval": "\u0ca0_\u0ca0",
    }

    def __init__(self, version: str, analytics_file: str = None, debug: bool = False):
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
        self.user_avatars = None # type: typing.Dict[str, str]
        self.user_presences = dict() # type: typing.Dict[int, str]
        self.user_last_activity = dict() # type: typing.Dict[int, float]

        self.config_file = None # type: str
        self.calendar = None # type: Calendar
        self.tba = None # type: TheBlueAlliance
        self.home_chat = None # type: pyryver.Chat
        self.announcements_chat = None # type: pyryver.Chat
        self.messages_chat = None # type: pyryver.Chat
        self.gh_updates_chat = None # type: pyryver.Chat
        self.gh_issues_board = None # type: pyryver.TaskBoard

        self.roles_file = None # type: str
        self.roles = CaseInsensitiveDict()

        self.trivia_file = None # type: str
        self.trivia_games = {} # type: typing.Dict[int, trivia.LatexBotTriviaGame]

        self.analytics = analytics.Analytics(analytics_file) if analytics_file is not None else None

        self.watch_file = None # type: str
        self.keyword_watches = None # type: typing.Dict[int, typing.Dict[str, typing.Union[typing.List[typing.Dict[str, typing.Any]], typing.Any]]]
        self.keyword_watches_automaton = None # type: Automaton

        self.daily_msg_task = None # type: typing.Awaitable

        self.commands = None # type: CommandSet
        self.help = None # type: str
        self.command_help = {} # type: typing.Dict[str, str]
       
        self.msg_creator = pyryver.Creator("LaTeX Bot " + self.version)

        self.webhook_server = None # type: server.Webhooks

        self.start_time = None # type: datetime
    
    def init_commands(self) -> None:
        """
        Initialize the command set.
        """
        self.commands = CommandSet()
        self.commands.add_command(Command("render", commands.command_render, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("chem", commands.command_chem, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("renderSimple", commands.command_renderSimple, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("help", commands.command_help, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("ping", commands.command_ping, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("whatDoYouThink", commands.command_whatDoYouThink, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("xkcd", commands.command_xkcd, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("checkiday", commands.command_checkiday, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("tba", commands.command_tba, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("trivia", commands.command_trivia, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("trivia importCustomQuestions", None, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("trivia exportCustomQuestions", None, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("trivia end", None, Command.ACCESS_LEVEL_FORUM_ADMIN))
        self.commands.add_command(Command("watch", commands.command_watch, Command.ACCESS_LEVEL_EVERYONE))
        
        self.commands.add_command(Command("deleteMessages", commands.command_deleteMessages, Command.ACCESS_LEVEL_FORUM_ADMIN))
        self.commands.add_command(Command("moveMessages", commands.command_moveMessages, Command.ACCESS_LEVEL_FORUM_ADMIN))
        self.commands.add_command(Command("countMessagesSince", commands.command_countMessagesSince, Command.ACCESS_LEVEL_FORUM_ADMIN))

        self.commands.add_command(Command("roles", commands.command_roles, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("addToRole", commands.command_addToRole, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("removeFromRole", commands.command_removeFromRole, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("deleteRole", commands.command_deleteRole, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("exportRoles", commands.command_exportRoles, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("importRoles", commands.command_importRoles, Command.ACCESS_LEVEL_ORG_ADMIN))

        self.commands.add_command(Command("events", commands.command_events, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("addEvent", commands.command_addEvent, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("quickAddEvent", commands.command_quickAddEvent, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("deleteEvent", commands.command_deleteEvent, Command.ACCESS_LEVEL_ORG_ADMIN))

        self.commands.add_command(Command("setEnabled", commands.command_setEnabled, Command.ACCESS_LEVEL_BOT_ADMIN))
        self.commands.add_command(Command("kill", commands.command_kill, Command.ACCESS_LEVEL_BOT_ADMIN))
        self.commands.add_command(Command("sleep", commands.command_sleep, Command.ACCESS_LEVEL_BOT_ADMIN))
        self.commands.add_command(Command("execute", commands.command_execute, Command.ACCESS_LEVEL_BOT_ADMIN))
        self.commands.add_command(Command("updateChats", commands.command_updateChats, Command.ACCESS_LEVEL_FORUM_ADMIN))
        self.commands.add_command(Command("setEnabled", None, Command.ACCESS_LEVEL_BOT_ADMIN))
    
        self.commands.add_command(Command("alias", commands.command_alias, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("exportConfig", commands.command_exportConfig, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("importConfig", commands.command_importConfig, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("accessRule", commands.command_accessRule, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("setDailyMessageTime", commands.command_setDailyMessageTime, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("dailyMessage", commands.command_dailyMessage, Command.ACCESS_LEVEL_FORUM_ADMIN))

        self.commands.add_command(Command("message", commands.command_message, Command.ACCESS_LEVEL_ORG_ADMIN))

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

        # Get user avatar URLs
        # This information is not included in the regular user info
        info = await self.ryver.get_info()
        users_json = info["users"]
        self.user_avatars = {u["id"]: u["avatarUrl"] for u in users_json}

        if os.environ.get("LATEXBOT_TBA_KEY"):
            self.tba = TheBlueAlliance(os.environ.get("LATEXBOT_TBA_KEY"))

        self.init_commands()
    
    async def reload_config(self) -> None:
        """
        This function should be called whenever the config JSON is updated.
        """
        self.calendar = Calendar("calendar_credentials.json", config.calendar_id)
        try:
            self.home_chat = util.parse_chat_name(self.ryver, config.home_chat)
        except ValueError as e:
            util.log(f"Error looking up home chat: {e}")
        try:
            self.announcements_chat = util.parse_chat_name(self.ryver, config.announcements_chat)
        except ValueError as e:
            util.log(f"Error looking up announcements chat: {e}")
        try:
            self.messages_chat = util.parse_chat_name(self.ryver, config.messages_chat)
        except ValueError as e:
            util.log(f"Error looking up messages chat: {e}")
        try:
            self.gh_updates_chat = util.parse_chat_name(self.ryver, config.gh_updates_chat)
        except ValueError as e:
            util.log(f"Error looking up GitHub updates chat: {e}")
        try:
            issues_chat = util.parse_chat_name(self.ryver, config.gh_issues_chat)
            self.gh_issues_board = await issues_chat.get_task_board()
            if not self.gh_issues_board:
                self.gh_issues_board = await issues_chat.create_task_board(pyryver.TaskBoard.BOARD_TYPE_BOARD)
            if self.gh_issues_board.get_board_type() != pyryver.TaskBoard.BOARD_TYPE_BOARD:
                self.gh_issues_board = None
                raise ValueError("Task board must have categories!")
        except ValueError as e:
            util.log(f"Error looking up GitHub issues chat: {e}")
        
    async def load_files(self, config_file: str, roles_file: str, trivia_file: str, watch_file: str) -> None:
        """
        Load all configuration files, including the config, roles and custom trivia.
        """
        self.config_file = config_file
        self.roles_file = roles_file
        self.trivia_file = trivia_file
        self.watch_file = watch_file

        # Load config
        try:
            with open(config_file, "r") as f:
                config_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            util.log(f"Error reading config: {e}. Falling back to empty config...")
            config_data = []
        
        err = config.load(config_data, True)
        await self.reload_config()
        if err:
            util.log(err)
            if self.home_chat is not None:
                await self.home_chat.send_message(err, self.msg_creator)

        # Load roles
        try:
            with open(roles_file, "r") as f:
                self.roles = CaseInsensitiveDict(json.load(f))
        except (json.JSONDecodeError, FileNotFoundError) as e:
            util.log(f"Error while loading roles: {e}. Defaulting to {{}}.")
            if self.home_chat is not None:
                await self.home_chat.send_message(f"Error while loading roles: {e}. Defaulting to {{}}.", self.msg_creator)
            self.roles = CaseInsensitiveDict()
        
        # Load trivia
        try:
            with open(trivia_file, "r") as f:
                trivia.set_custom_trivia_questions(json.load(f))
        except (json.JSONDecodeError, FileNotFoundError) as e:
            util.log(f"Error while loading custom trivia questions: {e}.")
            if self.home_chat is not None:
                await self.home_chat.send_message(f"Error while loading custom trivia questions: {e}.", self.msg_creator)

        # Load keyword watches
        try:
            with open(watch_file, "r") as f:
                self.keyword_watches = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            util.log(f"Error while loading keyword watches: {e}.")
            if self.home_chat is not None:
                await self.home_chat.send_message(f"Error while keyword watches: {e}. Defaulting to {{}}.", self.msg_creator)
            self.keyword_watches = dict()
        self.rebuild_automaton()

    def save_roles(self) -> None:
        """
        Save the current roles to the roles JSON.
        """
        with open(self.roles_file, "w") as f:
            json.dump(self.roles.to_dict(), f)
    
    def save_config(self) -> None:
        """
        Save the current config to the config JSON.
        """
        with open(self.config_file, "w") as f:
            json.dump(config.dump()[0], f)
    
    def save_watches(self) -> None:
        """
        Save the current keyword watches to the watches JSON.
        """
        with open(self.watch_file, "w") as f:
            json.dump(self.keyword_watches, f)
    
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
            util.log("Executing daily message routine...")
            await commands.command_dailyMessage(self, None, None, None, None)
            util.log("Daily message was sent.")
        except asyncio.CancelledError:
            cancelled = True
        except Exception as e: # pylint: disable=broad-except
            util.log(f"Error while executing daily message routine: {e}")
        finally:
            if not cancelled:
                self.schedule_daily_message()
    
    def schedule_daily_message(self):
        """
        Start the daily message task with the correct delay.
        """
        if self.daily_msg_task:
            self.daily_msg_task.cancel()
        
        if not config.daily_msg_time:
            util.log("Daily message not scheduled because time isn't defined.")
            return
        now = util.current_time()
        # Get that time, today
        t = datetime.combine(now, config.daily_msg_time.time(), tzinfo=config.timezone)
        # If already passed, get that time the next day
        if t < now:
            t += timedelta(days=1)
        init_delay = (t - now).total_seconds()
        self.daily_msg_task = asyncio.ensure_future(self._daily_msg(init_delay))
        util.log(f"Daily message re-scheduled, starting after {init_delay} seconds.")
    
    def rebuild_automaton(self) -> None:
        """
        Rebuild the DFA used for keyword searching in messages using Aho-Corasick.
        """
        dfa = Automaton()
        keywords = {}
        # Gather up all the keywords
        for user, watch_config in self.keyword_watches.items():
            if not watch_config["on"]:
                continue
            user = int(user)
            for watch in watch_config["keywords"]:
                if watch["keyword"] not in keywords:
                    keywords[watch["keyword"]] = []
                # Each keyword has a list of users and whether it should match case and whole words
                keywords[watch["keyword"]].append((user, watch["matchCase"], watch["wholeWord"]))
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
            msg_creator = pyryver.Creator(msg_author.get_name(), self.user_avatars.get(msg_author.get_id(), ""))
        return msg_creator

    def preprocess_command(self, command: str, is_dm: bool) -> typing.Tuple[str, str]:
        """
        Preprocess a command.

        Separate the command into the command name and args and resolve aliases 
        if it is a command. Otherwise return None.

        If it encouters a recursive alias, it raises ValueError.
        """
        for prefix in config.prefixes:
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
            for alias in config.aliases:
                if alias["from"] == cmd:
                    # Check for recursion
                    if alias["from"] in used_aliases:
                        raise ValueError(f"Recursive alias: '{alias['from']}'!")
                    used_aliases.add(alias["from"])
                    # Expand the alias
                    command = alias["to"] + space_char + args
                    break
            # No aliases were expanded - return
            if not command:
                return (cmd.strip(), args.strip())
            # Otherwise go again until no more expansion happens
    
    async def run(self) -> None:
        """
        Run LaTeX Bot.
        """
        self.start_time = util.current_time()
        util.log(f"LaTeX Bot {self.version} has been started. Initializing...")
        self.update_help()
        self.schedule_daily_message()
        # Start webhook server
        self.webhook_server = server.Server(self)
        port = os.environ.get("LATEXBOT_SERVER_PORT")
        try:
            if port:
                port = int(port)
        except ValueError as e:
            util.log(f"Error: Invalid port: {e}")
            port = None
        await self.webhook_server.start(port or 80)
        # Start live session
        async with self.ryver.get_live_session() as session: # type: pyryver.RyverWS
            self.session = session
            @session.on_connection_loss
            async def _on_conn_loss():
                util.log("Error: Connection lost!")
                await self.shutdown()
            
            @session.on_chat
            async def _on_chat(msg: pyryver.WSChatMessageData):
                # Ignore non-chat messages
                if msg.subtype != pyryver.ChatMessage.SUBTYPE_CHAT_MESSAGE:
                    return

                # Check the sender
                from_user = self.ryver.get_user(jid=msg.from_jid)
                # Ignore messages sent by us
                if from_user.get_username() == self.username:
                    return
                
                # Record activity
                self.user_last_activity[from_user.get_id()] = time.time()
                
                # Check if this is a DM
                to = self.ryver.get_chat(jid=msg.to_jid)
                if isinstance(to, pyryver.User):
                    # For DMs special processing is required
                    # Since we don't want to reply to ourselves, reply to the sender directly instead
                    to = from_user
                    is_dm = True
                else:
                    is_dm = False
                
                if self.analytics is not None:
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
                            await to.send_message(Command.get_access_denied_message(), self.msg_creator)
                            return
                        if self.analytics:
                            self.analytics.command(command, args, from_user, to)
                        # Send the presence change anyways in case it gets messed up
                        await session.send_presence_change(pyryver.RyverWS.PRESENCE_AVAILABLE)
                        if not self.enabled:
                            self.enabled = True
                            util.log(f"Re-enabled by user {from_user.get_name()}!")
                            await to.send_message("I have been re-enabled!", self.msg_creator)
                        else:
                            await to.send_message("I'm already enabled.", self.msg_creator)
                        return
                    elif command == "setEnabled" and args == "false" and self.enabled:
                        if not await self.commands.commands["setEnabled"].is_authorized(self, to, from_user):
                            await to.send_message(Command.get_access_denied_message(), self.msg_creator)
                            return
                        if self.analytics:
                            self.analytics.command(command, args, from_user, to)
                        self.enabled = False
                        util.log(f"Disabled by user {from_user.get_name()}.")
                        await to.send_message("I have been disabled.", self.msg_creator)
                        await session.send_presence_change(pyryver.RyverWS.PRESENCE_AWAY)
                        return

                    if not self.enabled:
                        return
                    if is_dm:
                        util.log(f"DM received from {from_user.get_name()}: {msg.text}")
                    else:
                        util.log(f"Command received from {from_user.get_name()} to {to.get_name()}: {msg.text}")

                    async with session.typing(to):
                        if command in self.commands.commands:
                            try:
                                if not await self.commands.process(command, args, self, to, from_user, msg.message_id):
                                    await to.send_message(Command.get_access_denied_message(), self.msg_creator)
                                    util.log("Access Denied")
                                else:
                                    if self.analytics:
                                        self.analytics.command(command, args, from_user, to)
                                    util.log("Command processed.")
                            except Exception as e: # pylint: disable=broad-except
                                util.log(f"Exception raised:\n{format_exc()}")
                                await to.send_message(f"An exception occurred while processing the command:\n```{format_exc()}\n```\n\nPlease try again.", self.msg_creator)
                        else:
                            util.log("Invalid command.")
                            await to.send_message(f"Sorry, I didn't understand what you were asking me to do.", self.msg_creator)
                # Not a command
                else:
                    # Check for roles
                    if util.MENTION_REGEX.search(msg.text):
                        # Replace roles and re-send
                        def replace_func(match):
                            group1 = match.group(1)
                            name = match.group(2)
                            if name in self.roles:
                                name = " @".join(self.roles[name])
                            return group1 + name
                        new_text = util.MENTION_REGEX.sub(replace_func, msg.text)
                        if new_text != msg.text:
                            util.log(f"Role mention received from {from_user.get_name()} to {to.get_name()}: {msg.text}")
                            async with session.typing(to):
                                # Get the message object
                                msg_obj = (await pyryver.retry_until_available(to.get_message, msg.message_id))
                                # Pretend to be the creator
                                msg_creator = await self.get_replace_message_creator(msg_obj)
                                await to.send_message(new_text, msg_creator)
                            # Can't delete the other person's messages in DMs, so skip
                            if not is_dm:
                                await msg_obj.delete()
                    # Check for macros
                    if msg.text in self.MACROS:
                        async with session.typing(to):
                            msg_obj = (await pyryver.retry_until_available(to.get_message, msg.message_id))
                            await to.send_message(self.MACROS[msg.text], await self.get_replace_message_creator(msg_obj))
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
                            # Check user presence
                            if self.user_presences.get(uid) == pyryver.RyverWS.PRESENCE_AVAILABLE:
                                continue
                            # Check user last activity
                            if t - self.user_last_activity.get(uid) < self.keyword_watches[str(uid)]["activityTimeout"]:
                                continue
                            # Verify that the user is a member of this chat
                            if isinstance(to, pyryver.GroupChat):
                                if to.get_member(from_user) is None:
                                    continue
                            user = self.ryver.get_user(id=uid)
                            resp = "The following message matched your watches for the keyword(s) " + ", ".join(f"\"**{w}**\"""" for w in keywords) + ":"
                            await user.send_message(resp + "\n" + quoted_msg, self.msg_creator)
            
            @session.on_chat_updated
            async def _on_chat_updated(msg: pyryver.WSChatUpdatedData):
                # Sometimes updates are sent for things other than message edits
                if msg.text is None:
                    return
                await _on_chat(msg)
            
            @session.on_event(pyryver.RyverWS.EVENT_REACTION_ADDED)
            async def _on_reaction_added(msg: pyryver.WSEventData):
                # Extra processing for interfacing trivia with reactions
                await commands.reaction_trivia(self, self.ryver, session, msg.event_data)
            
            @session.on_presence_changed
            async def _on_presence_changed(msg: pyryver.WSPresenceChangedData):
                # Keep track of user presences
                user = self.ryver.get_user(jid=msg.from_jid)
                self.user_presences[user.get_id()] = msg.presence

            util.log("LaTeX Bot is running!")
            if not self.debug and self.home_chat is not None:
                await session.send_presence_change(pyryver.RyverWS.PRESENCE_AVAILABLE)
                await self.home_chat.send_message(f"LaTeX Bot {self.version} is online! **I now respond to messages in real time!**\n\n{self.help}", self.msg_creator)

            await session.run_forever()
    
    async def shutdown(self):
        """
        Stop running LaTeX Bot.
        """
        await self.webhook_server.stop()
        await self.session.close()
