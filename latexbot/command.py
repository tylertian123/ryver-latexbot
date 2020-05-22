import asyncio
import org
import pyryver
import random
import typing

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

    all_commands = {} # type: typing.Dict[str, Command]

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
        if user.get_id() in org.admins:
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
    
    @classmethod
    async def process(cls, name: str, args: str, chat: pyryver.Chat, user: pyryver.User, msg_id: str) -> bool:
        """
        Try to process a command.

        If a processor for this command does not exist, a ValueError will be raised.

        If the user is not authorized to run this command, returns False.

        If everything went well, return True.
        """
        if name not in cls.all_commands:
            raise ValueError("Command not found")
        command = cls.all_commands[name]
        if not await command.is_authorized(chat, user):
            return False
        await command.execute(args, chat, user, msg_id)
        return True
        
    
    def __init__(self, name: str, processor: typing.Awaitable, access_level: int):
        self._name = name
        self._processor = processor
        self._level = access_level
        Command.all_commands[name] = self
    
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
        rules = org.access_rules.get(self._name, {})
        return rules["level"] if "level" in rules else self._level
    
    async def is_authorized(self, chat: pyryver.Chat, user: pyryver.User) -> bool:
        """
        Test if a user is authorized to use this command.
        """
        user_level = await Command.get_access_level(chat, user)
        # Get access rules
        rules = org.access_rules.get(self._name, {})
        # Overriding required level
        required_level = rules["level"] if "level" in rules else self._level
        # TODO: Add support for allowUser, disallowUser, allowRole and disallowRole
        return user_level >= required_level
    
    async def execute(self, args: str, chat: pyryver.Chat, user: pyryver.User, msg_id: str):
        """
        Execute the command (run its handler).

        Warning: This does NOT check for access levels.
        """
        await self._processor(chat, msg_id, args)
