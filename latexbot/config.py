"""
Global config.

Config JSON format:
- "admins": IDs of all the Bot Admins. (list of ints)
- "organizationTimeZone": The organization timezone. (string)
- "homeChat": The nickname of the chat to send misc messsages to. (string)
- "announcementsChat": The nickname of the chat to send event reminders to. (string)
- "messagesChat": The nickname of the chat to send off-topic messages to. (string)
- "googleCalendarId": The ID of the Google calendar to use for events. (string)
- "dailyMessageTime": The time of day when daily messages are sent, in the format "HH:MM". If null, daily messages will be disabled. (string)
- "lastXKCD": The number of the latest xkcd. Used to check for new comics. (int)
- "commandPrefixes": A list of all the accepted prefixes for commands. (list of str)
- "aliases": A list of command aliases, each with the following format (list of dict):
    [
        - "from": The alias (str)
        - "to": The text the alias expands to (str)
    ]
- "accessRules": Command access rules (dict):
    - "<command name>": The access rules for a specific command, with the following format (dict):
        - "level": If present, overrides the access level of this command (int, optional)
        - "allowUser": A list of usernames. If present, users in this list can access this command regardless of level (list of str, optional)
        - "disallowUser": A list of usernames. If present, users in this list cannot access this command regardless of level (list of str, optional)
        - "allowRole": A list of role names. If present, users with any of the roles in this list can access this command regardless of level (list of str, optional)
        - "disallowRole": A list of role names. If present, users with any of the roles in this list cannot access this command regardless of level (list of str, optional)
- "opinions": A list of opinions for whatDoYouThink, each with the following format (list of dict):
    [
        - "thing": A list of things this opinion is for. Has to be lowercase! (list of str)
        - "user": A list of users that has to be matched for this opinion (optional, list of str)
        - "opinion": A list of possible responses from which the response is randomly chosen (list of str)
    ]
"""

import typing
from config_loader import ConfigLoader
from datetime import datetime

loader = ConfigLoader()

def admins_loader(admins: list): # pylint: disable=redefined-outer-name
    if admins and not isinstance(admins[0], int):
        raise ValueError("Admins must be a list of ints!")
    return set(admins)
def command_prefixes_loader(p: list):
    if not p or not isinstance(p[0], str):
        raise ValueError("Command prefixes must be a non-empty list of strings!")
    return p
def aliases_loader(aliases: list): # pylint: disable=redefined-outer-name
    for alias in aliases:
        if not isinstance(alias, dict):
            raise ValueError("Incorrect aliases format!")
        if "from" not in alias or "to" not in alias or not isinstance(alias["from"], str) or not isinstance(alias["to"], str):
            raise ValueError("Incorrect aliases format!")
    return aliases
def access_rules_loader(access_rules: dict): # pylint: disable=redefined-outer-name
    for rules in access_rules.values():
        if not isinstance(rules, dict):
            raise ValueError("Invalid access rules format!")
        if not rules:
            raise ValueError("Empty rules are not allowed!")
    return access_rules
def opinions_loader(opinions: list): # pylint: disable=redefined-outer-name
    for opinion in opinions:
        if not isinstance(opinion, dict):
            raise ValueError("Incorrect opinions format!")
        if "thing" not in opinion or "opinion" not in opinion:
            raise ValueError("Incorrect opinions format!")
    return opinions

loader.field("admins", list, admins_loader, list, set())
loader.field("organizationTimeZone", str, default="UTC")
loader.field("homeChat", str, default="Test")
loader.field("announcementsChat", str, default="Test")
loader.field("messagesChat", str, default="Test")
loader.field("googleCalendarId", (str, type(None)))
loader.field("dailyMessageTime", (str, type(None)), lambda t: None if t is None else datetime.strptime(t, "%H:%M"), 
             lambda t: None if t is None else t.strftime("%H:%M"), default=datetime.strptime("00:00", "%H:%M"))
loader.field("lastXKCD", int, default=0)
loader.field("commandPrefixes", list, command_prefixes_loader, default=["@latexbot "])
loader.field("aliases", list, aliases_loader, default=[])
loader.field("accessRules", dict, access_rules_loader, default={})
loader.field("opinions", list, opinions_loader, default=[])

config = {}

admins = None # type: typing.Set[int]
timezone = None # type: str
home_chat = None # type: str
announce_chat = None # type: str
msgs_chat = None # type: str
calendar_id = None # type: str
daily_msg_time = None # type: datetime
last_xkcd = None # type: int
prefixes = None # type: typing.List[str]
aliases = None # type: typing.List[typing.Dict[str, str]]
access_rules = None # type: typing.Dict[str, typing.Dict[str, typing.Any]]
opinions = None # type: typing.List[typing.Dict[str, typing.Any]]

def load(data: typing.Dict[str, typing.Any], use_defaults: bool = True) -> str:
    """
    Load the config from parsed JSON data.
    """
    global admins, timezone, home_chat, announce_chat, msgs_chat, calendar_id # pylint: disable=global-statement
    global daily_msg_time, last_xkcd, prefixes, aliases, access_rules, opinions # pylint: disable=global-statement
    err = loader.load(data, config, use_defaults)
    admins = config["admins"]
    timezone = config["organizationTimeZone"]
    home_chat = config["homeChat"]
    announce_chat = config["announcementsChat"]
    msgs_chat = config["messagesChat"]
    calendar_id = config["googleCalendarId"]
    daily_msg_time = config["dailyMessageTime"]
    last_xkcd = config["lastXKCD"]
    prefixes = config["commandPrefixes"]
    aliases = config["aliases"]
    access_rules = config["accessRules"]
    opinions = config["opinions"]
    return err

def dump(use_defaults: bool = True) -> typing.Tuple[typing.Dict[str, typing.Any], str]:
    """
    Dump the config to a dict.
    """
    config["admins"] = admins
    config["organizationTimeZone"] = timezone
    config["homeChat"] = home_chat
    config["announcementsChat"] = announce_chat
    config["messagesChat"] = msgs_chat
    config["googleCalendarId"] = calendar_id
    config["dailyMessageTime"] = daily_msg_time
    config["lastXKCD"] = last_xkcd
    config["commandPrefixes"] = prefixes
    config["aliases"] = aliases
    config["accessRules"] = access_rules
    config["opinions"] = opinions
    return loader.dump(config, use_defaults)
