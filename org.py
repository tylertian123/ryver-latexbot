import pyryver
import json
import latexbot
import os
import requests
import time
import typing
import gcalendar
from caseinsensitivedict import CaseInsensitiveDict

user_avatars = {}

roles = CaseInsensitiveDict()
admins = set()
org_tz = None
home_chat = None
announcements_chat = None
messages_chat = None
calendar_id = None
daily_message_time = None
last_xkcd = None
command_prefixes = []
aliases = []
ROLES_FILE = "data/roles.json"
CONFIG_FILE = "data/config.json"

SERVICE_ACCOUNT_FILE = "calendar_credentials.json"
calendar = gcalendar.Calendar(SERVICE_ACCOUNT_FILE)


def save_roles():
    """
    Save roles to the JSON file specified by ROLES_FILE.
    """
    with open(ROLES_FILE, "w") as f:
        json.dump(roles.to_dict(), f)


def make_config():
    """
    Generate a config dict to be saved as a JSON.

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
        - "from": The alias
        - "to": The text the alias expands to
    """
    return {
        "admins": list(admins),
        "organizationTimeZone": org_tz,
        "homeChat": home_chat.get_nickname(),
        "announcementsChat": announcements_chat.get_nickname(),
        "messagesChat": messages_chat.get_nickname(),
        "googleCalendarId": calendar_id,
        "dailyMessageTime": daily_message_time,
        "lastXKCD": last_xkcd,
        "commandPrefixes": command_prefixes,
        "aliases": aliases,
    }


def init_config(ryver: pyryver.Ryver, config: typing.Dict[str, typing.Any]):
    """
    Initialize config data from a config dict.
    """
    global admins, org_tz, home_chat, announcements_chat, calendar_id, daily_message_time, messages_chat, last_xkcd, command_prefixes, aliases
    try:
        admins = set(config["admins"])
    except KeyError:
        print("Error: 'admins' not specified. Defaulting to [] or leaving unchanged.")
        admins = admins or []
    try:
        org_tz = config["organizationTimeZone"]
    except KeyError:
        print("Error: 'organizationTimeZone' not specified. Defaulting to UTC or leaving unchanged.")
        org_tz = org_tz or "UTC"
    try:
        home_chat = ryver.get_groupchat(nickname=config["homeChat"])
    except KeyError:
        print("Error: 'homeChat' not specified. Defaulting to +Test or leaving unchanged.")
        home_chat = home_chat or ryver.get_groupchat(nickname="Test")
    try:
        announcements_chat = ryver.get_groupchat(nickname=config["announcementsChat"])
    except KeyError:
        print("Error: 'announcementsChat' not specified. Defaulting to +Gen or leaving unchanged.")
        announcements_chat = announcements_chat or ryver.get_groupchat(nickname="Gen")
    try:
        messages_chat = ryver.get_groupchat(nickname=config["messagesChat"])
    except KeyError:
        print("Error: 'messagesChat' not specified. Defaulting to +Test or leaving unchanged.")
        messages_chat = messages_chat or ryver.get_groupchat(nickname="Test")
    try:
        calendar_id = config["googleCalendarId"]
    except KeyError:
        print("Error: 'googleCalendarId' not specified. Defaulting to null or leaving unchanged.")
    try:
        daily_message_time = config["dailyMessageTime"]
    except KeyError:
        print("Error: 'dailyMessageTime' not specified. Defaulting to null or leaving unchanged.")
    # Schedule or unschedule the daily message task
    if daily_message_time:
        latexbot.schedule_daily_message()
    else:
        if latexbot.daily_message_task:
            latexbot.daily_message_task.cancel()
    try:
        last_xkcd = config["lastXKCD"]
    except KeyError:
        print("Error: 'lastXKCD' not specified. Defaulting to 0 or leaving unchanged.")
        last_xkcd = last_xkcd or 0
    try:
        command_prefixes = config["commandPrefixes"]
    except KeyError:
        print("Error: 'commandPrefixes' not specified. Defaulting to ['@latexbot '] or leaving unchanged.")
        command_prefixes = command_prefixes or ["@latexbot "]
    try:
        aliases = config["aliases"]
    except KeyError:
        print("Error: 'aliases' not specified. Defaulting to [] or leaving unchanged.")
        aliases = aliases or []


def save_config():
    """
    Save config to the JSON file specified by CONFIG_FILE.
    """
    with open(CONFIG_FILE, "w") as f:
        json.dump(make_config(), f)


async def init(ryver: pyryver.Ryver):
    """
    Initialize everything.
    """
    global user_avatars, roles

    # Get user avatar URLs
    # This information is not included in the regular user info
    info = await ryver.get_info()
    users_json = info["users"]
    user_avatars = {u["id"]: u["avatarUrl"] for u in users_json}

    # Load roles
    try:
        with open(ROLES_FILE, "r") as f:
            roles = CaseInsensitiveDict(json.load(f))
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error while loading roles: {e}. Defaulting to [].")
        roles = []
    # Load config
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        init_config(ryver, config)
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print(f"Error while loading config: {e}. Using the following defaults:")
        # Call init_config with an empty dict so variables are initialized to their defaults
        init_config(ryver, {})
        
