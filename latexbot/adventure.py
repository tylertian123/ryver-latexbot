"""
Text-based adventures.
"""

import json
import pyryver
import typing
from org import creator


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
    
    def inv_add(self, item: int, count: int = 1):
        """
        Add an item to the player's inventory.
        """
        if item in self.inventory:
            self.inventory[item] += count
        else:
            self.inventory[item] = count


class Adventure:
    """
    An epic adventure!
    """
    def __init__(self, chat: pyryver.Chat, num: int, player: Player = None):
        with open(ADVENTURES_LIST[num]["path"], "r") as f:
            self.data = json.load(f)
        self.player = player or Player()
        self.ryver_msg = None
        self.chat = chat
    
    def enter_room(self, room: str) -> typing.Tuple[str, typing.List[str]]:
        """
        Enter a room. 

        The argument should be the reaction name.
        To enter the first room, use an empty string.

        If the room was successfully entered, returns a tuple of (text, reactions),
        where text is the room's text and reactions is a list of reactions for paths.

        If the room was not successfully entered (e.g. because of missing requirements)
        this function returns a tuple of (message, None).
        """
        if room != "":
            current_room = self.data["rooms"][self.player.room]
            if "paths" not in current_room or room not in current_room["paths"]:
                raise ValueError("Invalid room")
            path = current_room["paths"][room]
            if "requirements" in path:
                for req in path["requirements"]:
                    if self.player.inventory.get(req["item"], 0) < req["count"]:
                        return (f"You need **{req['count']}x {self.data['items'][req['item']]['name']}**!", None)
            room_id = path["room"]
        else:
            room_id = 0

        self.player.room = room_id
        room = self.data["rooms"][room_id]
        # Process and generate text
        text = room["text"]
        room_visited = "visited" in room and room["visited"]
        room["visited"] = True

        if "checkpoint" in room and room["checkpoint"]:
            text += "\n\n***Checkpoint hit!***"
            self.player.last_checkpoint = room_id
        if "items" in room and not room_visited:
            text += "\n\nYou found these items:\n"
            for item in room["items"]:
                item_obj = self.data["items"][item["item"]]
                text += f"\n- **{item_obj['name']}**: *{item_obj['description']}*"
                self.player.inv_add(item["item"], item["count"])
        if "end" in room and room["end"]:
            text += "\n\n# The End"
        
        reactions = []
        if "paths" in room:
            text += "\n"
            for reaction, path in room["paths"].items():
                reactions.append(reaction)
                text += f"\n:{reaction}:: {path['description']}"
                if "requirements" in path:
                    required = ", ".join(f"{req['count']}x {self.data['items'][req['item']]['name']}" for req in path["requirements"])
                    text += f" **(You need: {required})**"
        
        return (text, reactions)
    
    async def handle_reaction(self, reaction: str):
        """
        Handle a Ryver reaction.

        The reaction is assumed to be on the current active message.
        Use a reaction of "" to enter the first room to get a message.
        """
        try:
            text, reactions = self.enter_room(reaction)
        except ValueError as e:
            return
        mid = await self.chat.send_message(text, creator)
        if reactions is not None:
            msg = (await pyryver.retry_until_available(self.chat.get_message_from_id, mid, timeout=5.0))[0]
            self.ryver_msg = msg
            for reaction in reactions:
                await msg.react(reaction)


def list_adventures() -> typing.List[typing.Dict[str, str]]:
    """
    List all adventures.
    """
    global ADVENTURES_LIST
    if not ADVENTURES_LIST:
        with open(ADVENTURES_FILE, "r") as f:
            ADVENTURES_LIST = json.load(f)
    return ADVENTURES_LIST
