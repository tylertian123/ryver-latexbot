"""
Text-based adventures.
"""

import json
import typing


ADVENTURES_FILE = "data/adventures/adventures.json"
ADVENTURES_LIST = None


class Player:
    """
    A player in the adventure.
    """
    def __init__(self):
        self.health = 100
        self.room = 0
        self.last_checkpoint = 0
        self.inventory = {}


class Adventure:
    """
    An epic adventure!
    """
    def __init__(self, num: int, player: Player = None):
        with open(ADVENTURES_LIST[num]["path"], "r") as f:
            self.data = json.load(f)
        self.player = player or Player()
    
    def current_room_message(self) -> typing.Tuple[str, typing.List[str]]:
        """
        Return a formatted message for the current room and the room's reactions.
        """
        room = self.data["rooms"][self.player.room]
        text = room["text"]
        if "checkpoint" in room and room["checkpoint"]:
            text += "\n\n***Checkpoint hit!***"
        if "items" in room:
            text += "\n\nYou found these items:\n"
            text += "\n".join(f"- **{self.data['items'][item]['name']}**: *{self.data['items'][item]['description']}*" for item in room["items"])
        if "end" in room and room["end"]:
            text += "\n\n# The End"
        reactions = []
        if "paths" in room:
            text += "\n"
            for reaction, path in room["paths"].items():
                reactions.append(reaction)
                text += f"\n:{reaction}:: {path['description']}"
                if "requirements" in path:
                    text += f" **(You need: {', '.join(self.data['items'][item]['name'] for item in path['requirements'])})**"
        return (text, reactions)



def list_adventures() -> typing.List[typing.Dict[str, str]]:
    """
    List all adventures.
    """
    global ADVENTURES_LIST
    if not ADVENTURES_LIST:
        with open(ADVENTURES_FILE, "r") as f:
            ADVENTURES_LIST = json.load(f)
    return ADVENTURES_LIST
