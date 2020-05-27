"""
Text-based adventures.
"""

import math
import json
import pyryver
import typing
from org import creator


ADVENTURES_FILE = "data/adventures/adventures.json"
ADVENTURES_DIR = "data/adventures/"
ADVENTURES_LIST = None


class Player:
    """
    A player in the adventure.
    """
    def __init__(self):
        self.health = 100
        self.room = 0
        self.inventory = {}
        self.visited_rooms = set()
        self.last_checkpoint = None

    def copy(self):
        """
        Make a copy of this player.
        """
        other = Player()
        other.health = self.health
        other.room = self.room
        other.inventory = self.inventory.copy()
        other.visited_rooms = self.visited_rooms.copy()
        other.last_checkpoint = self.last_checkpoint
        return other
    
    def checkpoint(self):
        """
        Update last checkpoint info.
        """
        self.last_checkpoint = self.copy()
    
    def inv_add(self, item: int, count: int = 1):
        """
        Add an item to the player's inventory.
        """
        if item in self.inventory:
            self.inventory[item] += count
        else:
            self.inventory[item] = count
    
    def format_inv(self, items: typing.List[typing.Dict[str, typing.Any]]) -> str:
        """
        Get the inventory contents as a formatted string for display.
        """
        if not self.inventory:
            return "You have no items."
        text = "Inventory:"
        for item_id, count in self.inventory.items():
            item = items[item_id]
            text += f"\n- {count}x :{item['icon']}:{item['name']}"
        return text
    
    def format_health(self) -> str:
        """
        Get the player's health as a formatted string for display.
        """
        hearts = math.ceil(self.health / 10)
        return f"{self.health} (" + ":heart:" * hearts + ":broken_heart:" * (10 - hearts) + ")"


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
    
    def enter_room(self, room: typing.Union[str, int], skip_processing: bool = False) -> typing.Tuple[str, typing.List[str]]:
        """
        Enter a room. 

        The argument should be the path name (a reaction) or a number.
        Using a number directly allows you to enter a room regardless of restrictions.

        If skip_processing is set to True, then the room data will not be processed
        (only the message will be generated; e.g. traps won't be hit again).

        If the room was successfully entered, returns a tuple of (text, reactions),
        where text is the room's text and reactions is a list of reactions for paths.

        If the room was not successfully entered (e.g. because of missing requirements)
        this function returns a tuple of (message, None).
        """
        if isinstance(room, str):
            current_room = self.data["rooms"][self.player.room]
            if "paths" not in current_room or room not in current_room["paths"]:
                raise ValueError("Invalid room")
            path = current_room["paths"][room]
            if "requirements" in path:
                for req in path["requirements"]:
                    if self.player.inventory.get(req["item"], 0) < req["count"]:
                        item_obj = self.data["items"][req["item"]]
                        return (f"You need **{req['count']}x :{item_obj['icon']}:{item_obj['name']}**!", None)
            room_id = path["room"]
        else:
            room_id = room

        self.player.room = room_id
        room = self.data["rooms"][room_id]
        # Process and generate text
        text = room["text"]
        room_visited = room_id in self.player.visited_rooms
        self.player.visited_rooms.add(room_id)

        if not skip_processing:
            if "trap" in room:
                trap = room["trap"]
                if not ("onetime" in trap and trap["onetime"] and room_visited):
                    self.player.health -= trap["damage"]
                    if self.player.health > 0:
                        text += f"\n\nYou took {trap['damage']} damage. You have {self.player.format_health()} health left."
                    else:
                        text += f"\n\nYou took {trap['damage']} damage. **You died and through some magical power, you were warped back to the last checkpoint.**\n\n---"
                        # Reset to the checkpoint
                        # If there is no recorded checkpoint, start from the beginning
                        self.player = self.player.last_checkpoint or Player()
                        # Init the player's last checkpoint
                        self.player.checkpoint()
                        # Respawn the player
                        respawn = self.enter_room(self.player.room, True)
                        return (text + "\n\n" + respawn[0], respawn[1])
                        
            if "items" in room and not room_visited:
                text += "\n\nYou found these items:\n"
                for item in room["items"]:
                    item_obj = self.data["items"][item["item"]]
                    text += f"\n- **{item['count']}x :{item_obj['icon']}:{item_obj['name']}**: *{item_obj['description']}*"
                    self.player.inv_add(item["item"], item["count"])
            if "end" in room and room["end"]:
                text += "\n\n# The End"
            if "checkpoint" in room and room["checkpoint"]:
                text += "\n\n***Checkpoint hit!***"
                self.player.checkpoint()
        
        reactions = []
        if "paths" in room:
            text += "\n"
            for reaction, path in room["paths"].items():
                reactions.append(reaction)
                text += f"\n:{reaction}:: {path['description']}"
                if "requirements" in path:
                    required = ", ".join(f"{req['count']}x :{self.data['items'][req['item']]['icon']}:{self.data['items'][req['item']]['name']}" for req in path["requirements"])
                    text += f" **(You need: {required})**"
        text += "\n:briefcase:: View your inventory and stats."
        reactions.append("briefcase")
        
        return (text, reactions)
    
    async def handle_reaction(self, reaction: str):
        """
        Handle a Ryver reaction.

        The reaction is assumed to be on the current active message.
        Use a reaction of "" to enter the first room to get a message.
        """
        if reaction == "briefcase":
            await self.chat.send_message(f"Health: {self.player.format_health()}\n{self.player.format_inv(self.data['items'])}", creator)
            return
        try:
            if reaction == "":
                reaction = 0
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


def save_adventures(adventures: typing.List[typing.Dict[str, str]] = ADVENTURES_LIST):
    """
    Save the adventures file.
    """
    with open(ADVENTURES_FILE, "w") as f:
        json.dump(adventures, f)
