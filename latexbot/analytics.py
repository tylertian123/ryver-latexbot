import atexit
import json
import pyryver
import time


class Analytics:
    """
    A class to help with analytics.
    """

    def __init__(self, file: str):
        self.file = file
        self.command_usage = {} # typing.Dict[int, typing.Dict[str, str]]
        self.shutdowns = [] # typing.List[int]
        try:
            with open(file, "r") as f:
                data = json.load(f)
            self.command_usage = data["commandUsage"]
            self.shutdowns = data["shutdowns"]
        except (IOError, json.JSONDecodeError, KeyError):
            pass
        atexit.register(self.save, True)
    
    def command(self, cmd: str, args: str, user: pyryver.User, chat: pyryver.Chat) -> None: # pylint: disable=unused-argument
        """
        Record a command.
        """
        if cmd not in self.command_usage:
            self.command_usage[cmd] = {}
        uid = str(user.get_id())
        if uid in self.command_usage[cmd]:
            self.command_usage[cmd][uid] += 1
        else:
            self.command_usage[cmd][uid] = 1
    
    def save(self, shutdown: bool = False) -> None:
        """
        Save data to the file.
        """
        if shutdown:
            # Get rid of all shutdowns that are 30 days old or more
            now = int(time.time())
            self.shutdowns = [t for t in self.shutdowns if now - t < 2592000]
            self.shutdowns.append(now)
        data = {
            "commandUsage": self.command_usage,
            "shutdowns": self.shutdowns,
        }
        with open(self.file, "w") as f:
            json.dump(data, f)
