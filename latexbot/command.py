import config
import pyryver
import random
import typing
import util


class Command:
    """
    A LaTeX Bot command.
    """

    TYLER_ID = 1311906

    ACCESS_LEVEL_EVERYONE = 0
    ACCESS_LEVEL_FORUM_ADMIN = 1
    ACCESS_LEVEL_ORG_ADMIN = 2
    ACCESS_LEVEL_BOT_ADMIN = 3
    ACCESS_LEVEL_TYLER = 9001

    ACCESS_LEVEL_STRS = {
        ACCESS_LEVEL_EVERYONE: "",
        ACCESS_LEVEL_FORUM_ADMIN: "**Accessible to Forum, Org and Bot Admins only.**",
        ACCESS_LEVEL_ORG_ADMIN: "**Accessible to Org and Bot Admins only.**",
        ACCESS_LEVEL_BOT_ADMIN: "**Accessible to Bot Admins only.**",
        ACCESS_LEVEL_TYLER: "**Accessible to Tyler only.**"
    }

    ACCESS_DENIED_MESSAGES = [
        "I'm sorry Dave, I'm afraid I can't do that.",
        "ACCESS DENIED",
        "![NO](https://i.kym-cdn.com/photos/images/original/001/483/348/bdd.jpg)",
        "This operation requires a higher access level. Please ask an admin.",
        "Nice try.",
        "![Access Denied](https://cdn.windowsreport.com/wp-content/uploads/2018/08/fix-access-denied-error-windows-10.jpg)",
        "![No.](https://i.imgur.com/DKUR9Tk.png)",
        "![No](https://pics.me.me/thumb_no-no-meme-face-hot-102-7-49094780.png)",
    ]

    @classmethod
    def get_access_denied_message(cls) -> str:
        """
        Get an "access denied" message randomly chosen from ACCESS_DENIED_MESSAGES.
        """
        return cls.ACCESS_DENIED_MESSAGES[random.randrange(len(cls.ACCESS_DENIED_MESSAGES))]
    
    @classmethod
    async def get_access_level(cls, chat: pyryver.Chat, user: pyryver.User) -> int:
        """
        Get the access level of a user in a particular chat.

        The chat is used to determine whether the user is a forum or team admin.
        If the chat is not a pyryver.GroupChat, it will be ignored.
        """
        if user.get_id() == cls.TYLER_ID:
            return cls.ACCESS_LEVEL_TYLER
        if user.get_id() in config.admins:
            return cls.ACCESS_LEVEL_BOT_ADMIN
        if user.is_admin():
            return cls.ACCESS_LEVEL_ORG_ADMIN
        # Check if the user is a forum admin
        is_forum_admin = False
        # First make sure that the chat isn't a DM
        if isinstance(chat, pyryver.GroupChat):
            member = await chat.get_member(user.get_id()) # type: pyryver.GroupChatMember
            if member:
                is_forum_admin = member.is_admin()
        if is_forum_admin:
            return cls.ACCESS_LEVEL_FORUM_ADMIN
        return cls.ACCESS_LEVEL_EVERYONE
    
    def __init__(self, name: str, processor: typing.Awaitable, access_level: int):
        self._name = name
        self._processor = processor
        self._level = access_level
    
    def get_name(self) -> str:
        """
        Get the name of this command.
        """
        return self._name
    
    def get_processor(self) -> typing.Awaitable:
        """
        Get the command processor for this command.
        """
        return self._processor
    
    def get_level(self) -> int:
        """
        Get the access level of this command.

        Note: This access level may have been overridden in the config.
        """
        # Get access rules
        rules = config.access_rules.get(self._name, {})
        return rules["level"] if "level" in rules else self._level
    
    async def is_authorized(self, bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, access_level: int = None) -> bool:
        """
        Test if a user is authorized to use this command.

        An optional access level of the user can be provided. If None, requests may be sent to
        determine the access level.
        """
        # Get access rules
        rules = config.access_rules.get(self._name, {})
        # disallowUser has the highest precedence
        user_disallowed = user.get_username() in rules["disallowUser"] if "disallowUser" in rules else False
        if user_disallowed:
            return False
        # allowUser is second
        user_allowed = user.get_username() in rules["allowUser"] if "allowUser" in rules else False
        if user_allowed:
            return True
        # And then disallowRole
        role_disallowed = any(user.get_username() in bot.roles.get(role, []) for role in rules["disallowRole"]) if "disallowRole" in rules else False
        if role_disallowed:
            return False
        # Finally allowRole
        role_allowed = any(user.get_username() in bot.roles.get(role, []) for role in rules["allowRole"]) if "allowRole" in rules else False
        if role_allowed:
            return True
        # If none of those are true, check the access level normally
        user_level = access_level if access_level is not None else await Command.get_access_level(chat, user)
        required_level = rules["level"] if "level" in rules else self._level
        return user_level >= required_level
    
    async def execute(self, args: str, bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str):
        """
        Execute the command (run its handler).

        Warning: This does NOT check for access levels.
        """
        await self._processor(bot, chat, user, msg_id, args)


class CommandSet:
    """
    A set of commands.
    """

    def __init__(self):
        self.commands = {} # type: typing.Dict[str, Command]
    
    def add_command(self, command: Command) -> None:
        """
        Add a command to the set.
        """
        self.commands[command.get_name()] = command
    
    async def process(self, name: str, args: str, bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str) -> bool:
        """
        Try to process a command.

        If a processor for this command does not exist, a ValueError will be raised.

        If the user is not authorized to run this command, returns False.

        If everything went well, return True.
        """
        if name not in self.commands:
            raise ValueError("Command not found")
        command = self.commands[name]
        if not await command.is_authorized(bot, chat, user):
            return False
        await command.execute(args, bot, chat, user, msg_id)
        return True
    
    def generate_help_text(self, ryver: pyryver.Ryver) -> typing.Tuple[typing.Dict[str, typing.List[typing.Tuple[str, str]]], typing.Dict[str, str]]:
        """
        Generate help text and extended help text for each command.

        Returns a tuple of (help_text, extended_help_text).
        The help text is a mapping of command group names to lists of tuples of (command_name, command_description).
        The extended help text is a mapping of command names to their extended descriptions.
        """
        help_text = {}
        extended_help_text = {}
        prefix = config.prefixes[0]
        for name, command in self.commands.items():
            if command.get_processor() is None:
                # Don't generate a warning for commands with no processors
                continue

            if command.get_processor().__doc__ == "":
                util.log(f"Warning: Command {name} has no documentation, skipped")
                continue

            try:
                properties = util.parse_doc(command.get_processor().__doc__)
                if properties.get("hidden", False) == "true":
                    # skip hidden commands
                    continue

                # Generate syntax string
                syntax = f"`{prefix}{name} {properties['syntax']}`" if properties["syntax"] else f"`{prefix}{name}`"
                # Generate short description
                access_level = Command.ACCESS_LEVEL_STRS.get(command.get_level(), f"**Unknown Access Level: {command.get_level()}.**")
                description = f"{syntax} - {properties['short_desc']} {access_level}"

                # Group commands
                group = properties['group']
                if group in help_text:
                    help_text[group].append((name, description))
                else:
                    help_text[group] = [(name, description)]

                extended_description = properties["long_desc"] or "***No extended description provided.***"
                examples = "\n".join(
                    "* " + ex for ex in properties["examples"]) if properties["examples"] else "***No examples provided.***"

                description += f"\n\n{extended_description}\n\n**Examples:**\n{examples}"
                extended_help_text[name] = description
            except (ValueError, KeyError) as e:
                util.log(f"Error while parsing doc for {name}: {e}")
        return help_text, extended_help_text


import latexbot # nopep8 # pylint: disable=unused-import
