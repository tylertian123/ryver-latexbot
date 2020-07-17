import atexit
import json
import pyryver
import signal
import time


class Analytics:
    """
    A class to help with analytics.
    """

    def __init__(self, file: str):
        self.file = file
        self.command_usage = {} # typing.Dict[int, typing.Dict[str, int]]
        self.shutdowns = [] # typing.List[int]
        try:
            with open(file, "r") as f:
                data = json.load(f)
            self.command_usage = data.get("commandUsage") or self.command_usage
            self.shutdowns = data.get("shutdowns") or self.shutdowns
        except (IOError, json.JSONDecodeError):
            pass
        self.shutdowns.append(int(time.time()) << 1 | 0x1)

        atexit.register(self.save)
        def sig_handler(num, frame): # pylint: disable=unused-argument
            self.save()
            exit()
        signal.signal(signal.SIGABRT, sig_handler)
        signal.signal(signal.SIGTERM, sig_handler)
    
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
    
    def save(self) -> None:
        """
        Save data to the file.
        """
        # Get rid of all shutdowns/reboots that are 10 days or older
        now = int(time.time())
        self.shutdowns = [t for t in self.shutdowns if now - (t >> 1) < 86400]

        data = {
            "commandUsage": self.command_usage,
            "shutdowns": self.shutdowns + [now << 1],
        }
        with open(self.file, "w") as f:
            json.dump(data, f)
