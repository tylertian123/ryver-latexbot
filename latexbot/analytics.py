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
        self.command_usage = {} # typing.Dict[int, typing.Dict[int, int]]
        self.message_activity = {} # typing.Dict[int, int]
        self.shutdowns = [] # typing.List[int]
        try:
            with open(file, "r") as f:
                data = json.load(f)
            self.command_usage = data.get("commandUsage") or self.command_usage
            # String keys to int keys
            self.command_usage = {k: {int(l): w for l, w in v.items()} for k, v in self.command_usage.items()}
            self.shutdowns = data.get("shutdowns") or self.shutdowns
            self.message_activity = data.get("messageActivity") or self.message_activity
            self.message_activity = {int(k): v for k, v in self.message_activity.items()}
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
    
    def save(self) -> None:
        """
        Save data to the file.
        """
        # Get rid of all shutdowns/reboots that are 10 days or older
        now = int(time.time())
        self.shutdowns = [t for t in self.shutdowns if now - (t >> 1) < 864000]

        data = {
            "commandUsage": self.command_usage,
            "shutdowns": self.shutdowns + [now << 1],
            "messageActivity": self.message_activity,
        }
        with open(self.file, "w") as f:
            json.dump(data, f)
