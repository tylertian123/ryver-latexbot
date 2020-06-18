import asyncio
import commands
import config
import json
import pyryver
import trivia
import typing
import util
from caseinsensitivedict import CaseInsensitiveDict
from command import Command, CommandSet
from datetime import datetime, timedelta
from gcalendar import Calendar
from traceback import format_exc


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
        self.user_avatars = None # type: typing.Dict[str, str]

        self.config_file = None # type: str
        self.calendar = None # type: Calendar
        self.home_chat = None # type: pyryver.GroupChat
        self.announcements_chat = None # type: pyryver.GroupChat
        self.messages_chat = None # type: pyryver.GroupChat

        self.roles_file = None # type: str
        self.roles = CaseInsensitiveDict()

        self.trivia_file = None # type: str
        self.trivia_games = {} # type: typing.Dict[int, trivia.LatexBotTriviaGame]

        self.daily_msg_task = None # type: typing.Awaitable

        self.commands = None # type: CommandSet
        self.help = None # type: str
        self.command_help = {} # type: typing.Dict[str, str]
       
        self.msg_creator = pyryver.Creator("LaTeX Bot " + self.version)
    
    def init_commands(self) -> None:
        """
        Initialize the command set.
        """
        self.commands = CommandSet()
        self.commands.add_command(Command("render", commands.command_render, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("chem", commands.command_chem, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("help", commands.command_help, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("ping", commands.command_ping, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("whatDoYouThink", commands.command_whatDoYouThink, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("xkcd", commands.command_xkcd, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("checkiday", commands.command_checkiday, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("trivia", commands.command_trivia, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("trivia importCustomQuestions", None, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("trivia exportCustomQuestions", None, Command.ACCESS_LEVEL_ORG_ADMIN))
        self.commands.add_command(Command("trivia end", None, Command.ACCESS_LEVEL_FORUM_ADMIN))
        
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

        self.init_commands()
    
    def reload_config(self) -> None:
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

    async def load_files(self, config_file: str, roles_file: str, trivia_file: str) -> None:
        """
        Load all configuration files, including the config, roles and custom trivia.
        """
        self.config_file = config_file
        self.roles_file = roles_file
        self.trivia_file = trivia_file

        # Load config
        try:
            with open(config_file, "r") as f:
                config_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            util.log(f"Error reading config: {e}. Falling back to empty config...")
            config_data = []
        
        err = config.load(config_data, True)
        self.reload_config()
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
    
    def update_help(self) -> None:
        """
        Re-generate the help text.
        """
        self.help, self.command_help = self.commands.generate_help_text(self.ryver)
    
    async def _daily_msg(self, init_delay: float = 0):
        """
        A task that sends the daily message after a delay and repeats every 24h.
        """
        try:
            await asyncio.sleep(init_delay)
            while True:
                util.log("Executing daily message routine...")
                await commands.command_dailyMessage(self, None, None, None, None)
                util.log("Daily message was sent.")
                # Sleep for an entire day
                await asyncio.sleep(60 * 60 * 24)
        except asyncio.CancelledError:
            pass
    
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
    
    def preprocess_command(self, command: str, is_dm: bool):
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
        util.log(f"LaTeX Bot {self.version} has been started. Initializing...")
        self.update_help()
        self.schedule_daily_message()
        # Start live session
        async with self.ryver.get_live_session() as session: # type: pyryver.RyverWS
            self.session = session
            @session.on_connection_loss
            async def _on_conn_loss():
                util.log("Error: Connection lost!")
                await session.close()
            
            @session.on_error
            async def _on_error(err: typing.Union[TypeError, ValueError]):
                util.log(f"pyryver realtime error: {err}")
                await session.close()
            
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
                
                # Check if this is a DM
                to = self.ryver.get_chat(jid=msg.to_jid)
                if isinstance(to, pyryver.User):
                    # For DMs special processing is required
                    # Since we don't want to reply to ourselves, reply to the sender directly instead
                    to = from_user
                    is_dm = True
                else:
                    is_dm = False

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
                            # Get the message object
                            to = self.ryver.get_chat(jid=msg.to_jid)
                            util.log(f"Role mention received from {from_user.get_name()} to {to.get_name()}: {msg.text}")
                            async with session.typing(to):
                                # Pretend to be the creator
                                msg_creator = pyryver.Creator(from_user.get_name(), self.user_avatars.get(from_user.get_id(), ""))
                                await to.send_message(new_text, msg_creator)
                            # Can't delete the other person's messages in DMs, so skip
                            if not is_dm:
                                await (await pyryver.retry_until_available(to.get_message, msg.message_id)).delete()
            
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

            util.log("LaTeX Bot is running!")
            if not self.debug and self.home_chat is not None:
                await self.home_chat.send_message(f"LaTeX Bot {self.version} is online! **I now respond to messages in real time!**\n\n{self.help}", self.msg_creator)

            await session.run_forever()
