import commands
import config
import json
import pyryver
import util
from caseinsensitivedict import CaseInsensitiveDict
from command import Command, CommandSet
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
        self.username = None # type: str
        self.user_avatars = None # type: typing.Dict[str, str]

        self.config_file = None # type: str
        self.calendar = None # type: Calendar
        self.home_chat = None # type: pyryver.GroupChat
        self.announcements_chat = None # type: pyryver.GroupChat
        self.messages_chat = None # type: pyryver.GroupChat

        self.roles_file = None # type: str
        self.roles = CaseInsensitiveDict()

        self.trivia_file = None # type: str

        self.commands = None # type: CommandSet
        self.help = None # type: str
        self.command_help = {} # type: typing.Dict[str, str]
       
        self.msg_creator = pyryver.Creator("LaTeX Bot " + self.version)
    
    async def init(self, org: str, user: str, password: str, cache_dir: str, cache_prefix: str) -> None:
        """
        Initialize LaTeX Bot.
        """
        self.username = user
        cache = pyryver.FileCacheStorage(cache_dir, cache_prefix)
        self.ryver = pyryver.Ryver(org=org, user=user, password=password, cache=cache)
        await self.ryver.load_missing_chats()

        # Get user avatar URLs
        # This information is not included in the regular user info
        info = await self.ryver.get_info()
        users_json = info["users"]
        self.user_avatars = {u["id"]: u["avatarUrl"] for u in users_json}

        # Define commands
        self.commands = CommandSet()
        self.commands.add_command(Command("render", commands.command_render, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("chem", commands.command_chem, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("help", commands.command_help, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("ping", commands.command_ping, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("whatDoYouThink", commands.command_whatDoYouThink, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("xkcd", commands.command_xkcd, Command.ACCESS_LEVEL_EVERYONE))
        self.commands.add_command(Command("checkiday", commands.command_checkiday, Command.ACCESS_LEVEL_EVERYONE))
    
    async def load_config(self, config_file: str, roles_file: str, trivia_file: str) -> str:
        """
        Load the config.

        Returns an error message.
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
        
        err = config.load(config_data, True)
        self.calendar = Calendar("calendar_credentials.json", config.calendar_id)
        self.home_chat = self.ryver.get_groupchat(nickname=config.home_chat)
        self.announcements_chat = self.ryver.get_groupchat(nickname=config.announce_chat)
        self.messages_chat = self.ryver.get_groupchat(nickname=config.msgs_chat)
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
    
    async def run(self) -> None:
        """
        Run LaTeX Bot.
        """
        util.log(f"LaTeX Bot {self.version} has been started. Initializing...")
        self.help, self.command_help = self.commands.generate_help_text(self.ryver)
        # Start live session
        async with self.ryver.get_live_session() as session: # type: pyryver.RyverWS
            @session.on_connection_loss
            async def _on_conn_loss():
                util.log("Error: Connection lost!")
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
                    preprocessed = util.preprocess_command(config.prefixes, config.aliases, msg.text, is_dm)
                except ValueError as e:
                    # Skip if not self.
                    if self.enabled:
                        await to.send_message(f"Cannot process command: {e}", self.msg_creator)
                    return
                
                if preprocessed:
                    command, args = preprocessed
                    # Processing for re-enabling after disable
                    if command == "setEnabled" and args == "true":
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
                pass
                #await commands._trivia_on_reaction(self.ryver, session, msg.event_data)

            util.log("LaTeX Bot is running!")
            if not self.debug and self.home_chat is not None:
                await self.home_chat.send_message(f"LaTeX Bot {self.version} is online! **I now respond to messages in real time!**\n\n{self.help}", self.msg_creator)

            await session.run_forever()
