import pyryver
import schemas
import time
import typing


class Analytics:
    """
    A class to help with analytics.
    """

    def __init__(self, command_usage: typing.Dict[str, typing.Dict[int, int]], message_activity: typing.Dict[int, int],
                 shutdowns: typing.List[int]):
        self.command_usage = command_usage
        self.message_activity = message_activity
        self.shutdowns = shutdowns
        self.shutdowns.append(int(time.time()) << 1 | 0x1)

    def command(self, cmd: str, args: str, user: pyryver.User, chat: pyryver.Chat) -> None: # pylint: disable=unused-argument
        """
        Record a command.
        """
        if cmd not in self.command_usage:
            self.command_usage[cmd] = {}
        if user.get_id() in self.command_usage[cmd]:
            self.command_usage[cmd][user.get_id()] += 1
        else:
            self.command_usage[cmd][user.get_id()] = 1

    def message(self, body: str, user: pyryver.User) -> None:
        """
        Record a message.
        """
        if len(body) < 750:
            if user.get_id() in self.message_activity:
                self.message_activity[user.get_id()] += len(body)
            else:
                self.message_activity[user.get_id()] = len(body)

    def dumps(self) -> str:
        """
        Serialize into a JSON string that can be written to a file.
        """
        # Get rid of all shutdowns/reboots that are 10 days or older
        now = int(time.time())
        self.shutdowns = [t for t in self.shutdowns if now - (t >> 1) < 864000]
        # Temporarily add a shutdown
        self.shutdowns.append(now << 1)
        s = schemas.analytics.dumps(self)
        self.shutdowns.pop()
        return s
