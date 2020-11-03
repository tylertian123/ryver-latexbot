"""
This module contains the Command class and helpers.
"""

import functools
import latexbot
import os
import pyryver
import random
import typing
import util


class CommandError(Exception):
    """
    An exception raised by commands when an error occurs.
    """


class Command:
    """
    A LaTeX Bot command.
    """

    MAINTAINER_ID = int(os.environ.get("LATEXBOT_MAINTAINER_ID", 0))

    ACCESS_LEVEL_EVERYONE = 0
    ACCESS_LEVEL_FORUM_ADMIN = 1
    ACCESS_LEVEL_ORG_ADMIN = 2
    ACCESS_LEVEL_BOT_ADMIN = 3
    ACCESS_LEVEL_MAINTAINER = 4

    ACCESS_LEVEL_STRS = {
        ACCESS_LEVEL_EVERYONE: "",
        ACCESS_LEVEL_FORUM_ADMIN: "**Accessible to Forum, Org and Bot Admins only.**",
        ACCESS_LEVEL_ORG_ADMIN: "**Accessible to Org and Bot Admins only.**",
        ACCESS_LEVEL_BOT_ADMIN: "**Accessible to Bot Admins only.**",
        ACCESS_LEVEL_MAINTAINER: "**Accessible to my Maintainer only.**"
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
        if user.get_id() == cls.MAINTAINER_ID:
            return cls.ACCESS_LEVEL_MAINTAINER
        if user.get_id() in latexbot.bot.config.admins:
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
    
    def __init__(self, name: str, processor: typing.Callable[..., typing.Awaitable], access_level: int):
        self._name = name
        self._processor = processor
        self._level = access_level
    
    def __call__(self, *args, **kwargs):
        return self._processor(*args, **kwargs)
    
    def get_name(self) -> str:
        """
        Get the name of this command.
        """
        return self._name
    
    def get_processor(self) -> typing.Callable[..., typing.Awaitable]:
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
        rules = latexbot.bot.config.access_rules.get(self._name)
        if rules is None or rules.level is None:
            return self._level
        return rules.level
    
    async def is_authorized(self, bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, access_level: int = None) -> bool:
        """
        Test if a user is authorized to use this command.

        An optional access level of the user can be provided. If None, requests may be sent to
        determine the access level.
        """
        # Get access rules
        rules = latexbot.bot.config.access_rules.get(self._name)
        if rules is not None:
            # disallowUser has the highest precedence
            if util.contains_ignorecase(user.get_username(), rules.disallow_users or ()):
                return False
            # allowUser is second
            if util.contains_ignorecase(user.get_username(), rules.allow_users or ()):
                return True
            # And then disallowRole
            if any(user.get_id() in bot.roles.get(role, ()) for role in rules.disallow_roles or ()):
                return False
            # Finally allowRole
            if any(user.get_id() in bot.roles.get(role, ()) for role in rules.allow_roles or ()):
                return True
        # If none of those are true, check the access level normally
        user_level = access_level if access_level is not None else await Command.get_access_level(chat, user)
        required_level = self.get_level()
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
    
    def add_command(self, cmd: Command) -> None:
        """
        Add a command to the set.
        """
        self.commands[cmd.get_name()] = cmd
    
    async def process(self, name: str, args: str, bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str) -> bool:
        """
        Try to process a command.

        If a processor for this command does not exist, a ValueError will be raised.

        If the user is not authorized to run this command, returns False.

        If everything went well, return True.
        """
        if name not in self.commands:
            raise ValueError("Command not found")
        cmd = self.commands[name]
        if not await cmd.is_authorized(bot, chat, user):
            return False
        await cmd.execute(args, bot, chat, user, msg_id)
        return True
    
    def generate_help_text(self, ryver: pyryver.Ryver) -> typing.Tuple[typing.Dict[str, typing.List[typing.Tuple[str, str]]], typing.Dict[str, str]]: # pylint: disable=unused-argument
        """
        Generate help text and extended help text for each command.

        Returns a tuple of (help_text, extended_help_text).
        The help text is a mapping of command group names to lists of tuples of (command_name, command_description).
        The extended help text is a mapping of command names to their extended descriptions.
        """
        help_text = {}
        extended_help_text = {}
        prefix = latexbot.bot.config.command_prefixes[0]
        for name, cmd in self.commands.items():
            if cmd.get_processor() is None:
                # Don't generate a warning for commands with no processors
                continue

            if cmd.get_processor().__doc__ == "":
                util.log(f"Warning: Command {name} has no documentation, skipped")
                continue

            try:
                properties = util.parse_doc(cmd.get_processor().__doc__)
                if properties.get("hidden", False) == "true":
                    # skip hidden commands
                    continue

                # Generate syntax string
                syntax = f"`{prefix}{name} {properties['syntax']}`" if properties["syntax"] else f"`{prefix}{name}`"
                # Generate short description
                access_level = Command.ACCESS_LEVEL_STRS.get(cmd.get_level(), f"**Unknown Access Level: {cmd.get_level()}.**")
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


def command(name: str = None, access_level: int = Command.ACCESS_LEVEL_EVERYONE): # pylint: disable=unused-argument
    """
    Decorator for creating a command from a processor function.

    For functions with name command_x, the name can be automatically deduced.
    """
    def _command_decor(func):
        nonlocal name
        if name is None:
            if func.__name__.startswith("command_"):
                name = func.__name__[len("command_"):]
                words = name.split("_")
                name = words[0] + ''.join(s[0].upper() + s[1:] for s in words[1:])
            else:
                raise ValueError("Cannot deduce function name")
        return functools.wraps(func)(Command(name, func, access_level))
    return _command_decor
