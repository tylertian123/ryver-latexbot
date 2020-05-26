"""
This module holds organization data and settings as well as some functions.
"""
import aiohttp
import asyncio
import gcalendar
import json
import latexbot_util as util
import os
import pyryver
import requests
import time
import trivia
import typing
import xkcd
from caseinsensitivedict import CaseInsensitiveDict
from datetime import datetime, timedelta
from dateutil import tz
from gcalendar import Calendar
from markdownify import markdownify


VERSION = "v0.5.1-dev"

creator = pyryver.Creator(f"LaTeX Bot {VERSION}", "")

user_avatars = {}

roles = CaseInsensitiveDict()
admins = set()
org_tz = None # type: str
home_chat = None # type: pyryver.GroupChat
announcements_chat = None # type: pyryver.GroupChat
messages_chat = None # type: pyryver.GroupChat
calendar_id = None # type: str
daily_message_time = None # type: str
last_xkcd = None # type: int
command_prefixes = [] # type: typing.List[str]
aliases = [] # type: typing.List[typing.Dict[str, str]]
access_rules = {} # type: typing.Dict[str, typing.Dict[str, typing.Any]]
opinions = [] # type: typing.List[typing.Dict[str, typing.List[str]]]
ROLES_FILE = "data/roles.json"
CONFIG_FILE = "data/config.json"
TRIVIA_FILE = "data/trivia.json"

SERVICE_ACCOUNT_FILE = "calendar_credentials.json"
calendar = gcalendar.Calendar(SERVICE_ACCOUNT_FILE)

daily_message_task = None # type: asyncio.Future

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
        "accessRules": access_rules,
        "opinions": opinions,
    }


def init_config(ryver: pyryver.Ryver, config: typing.Dict[str, typing.Any]):
    """
    Initialize config data from a config dict.
    """
    global admins, org_tz, home_chat, announcements_chat, calendar_id, daily_message_time, messages_chat, last_xkcd, command_prefixes, aliases, access_rules, opinions
    err = []
    try:
        admins = set(config["admins"])
    except Exception as e:
        err.append("Error: Invalid field 'admins'. Defaulting to [] or leaving unchanged.")
        admins = admins or []
    try:
        org_tz = config["organizationTimeZone"]
    except Exception as e:
        err.append("Error: Invalid field 'organizationTimeZone'. Defaulting to UTC or leaving unchanged.")
        org_tz = org_tz or "UTC"
    try:
        home_chat = ryver.get_groupchat(nickname=config["homeChat"])
    except Exception as e:
        err.append("Error: Invalid field 'homeChat'. Defaulting to +Test or leaving unchanged.")
        home_chat = home_chat or ryver.get_groupchat(nickname="Test")
    try:
        announcements_chat = ryver.get_groupchat(nickname=config["announcementsChat"])
    except Exception as e:
        err.append("Error: Invalid field 'announcementsChat'. Defaulting to +Gen or leaving unchanged.")
        announcements_chat = announcements_chat or ryver.get_groupchat(nickname="Gen")
    try:
        messages_chat = ryver.get_groupchat(nickname=config["messagesChat"])
    except Exception as e:
        err.append("Error: Invalid field 'messagesChat'. Defaulting to +Test or leaving unchanged.")
        messages_chat = messages_chat or ryver.get_groupchat(nickname="Test")
    try:
        calendar_id = config["googleCalendarId"]
    except Exception as e:
        err.append("Error: Invalid field 'googleCalendarId'. Defaulting to null or leaving unchanged.")
    try:
        daily_message_time = config["dailyMessageTime"]
    except Exception as e:
        err.append("Error: Invalid field 'dailyMessageTime'. Defaulting to null or leaving unchanged.")
    # Schedule or unschedule the daily message task
    if daily_message_time:
        schedule_daily_message()
    else:
        if daily_message_task:
            daily_message_task.cancel()
    try:
        last_xkcd = config["lastXKCD"]
    except Exception as e:
        err.append("Error: Invalid field 'lastXKCD'. Defaulting to 0 or leaving unchanged.")
        last_xkcd = last_xkcd or 0
    try:
        command_prefixes = config["commandPrefixes"]
    except Exception as e:
        err.append("Error: Invalid field 'commandPrefixes'. Defaulting to ['@latexbot '] or leaving unchanged.")
        command_prefixes = command_prefixes or ["@latexbot "]
    try:
        aliases = config["aliases"]
    except Exception as e:
        err.append("Error: Invalid field 'aliases'. Defaulting to [] or leaving unchanged.")
        aliases = aliases or []
    try:
        access_rules = config["accessRules"] # type: typing.Dict[str, typing.Dict[str, typing.Any]]
    except Exception as e:
        err.append("Error: Invalid field 'accessRules'. Defaulting to {} or leaving unchanged.")
        access_rules = access_rules or {}
    try:
        opinions = config["opinions"] # type: typing.List[typing.Dict[str, typing.List[str]]]
    except Exception as e:
        err.append("Error: Invalid field 'opinions'. Defaulting to [] or leaving unchanged.")
        opinions = opinions or []
    return err


def save_config():
    """
    Save config to the JSON file specified by CONFIG_FILE.
    """
    with open(CONFIG_FILE, "w") as f:
        json.dump(make_config(), f)


async def daily_message(init_delay: float = 0):
    """
    Send the daily message.
    """
    global last_xkcd
    try:
        await asyncio.sleep(init_delay)
        while True:
            print("Checking today's events...")
            now = util.current_time()
            events = calendar.get_today_events(calendar_id, now)
            if not events:
                print("No events today!")
            else:
                resp = "Reminder: These events are happening today:"
                for event in events:
                    start = Calendar.parse_time(event["start"])
                    end = Calendar.parse_time(event["end"])

                    # The event has a time, and it starts today (not already started)
                    if start.tzinfo and start > now:
                        resp += f"\n# {event['summary']} today at *{start.strftime(util.TIME_DISPLAY_FORMAT)}*"
                    else:
                        # Otherwise format like normal
                        start_str = start.strftime(util.DATETIME_DISPLAY_FORMAT if start.tzinfo else util.DATE_DISPLAY_FORMAT)
                        end_str = end.strftime(util.DATETIME_DISPLAY_FORMAT if end.tzinfo else util.DATE_DISPLAY_FORMAT)
                        resp += f"\n# {event['summary']} (*{start_str}* to *{end_str}*)"

                    # Add description if there is one
                    if "description" in event and event["description"] != "":
                        # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
                        resp += f"\u200B:\n{markdownify(event['description'])}"
                await announcements_chat.send_message(resp, creator)
                print("Events reminder sent!")
            
            print("Checking for holidays...")
            url = f"https://www.checkiday.com/api/3/?d={util.current_time().strftime('%Y/%m/%d')}"
            async with aiohttp.request("GET", url) as resp:
                if resp.status != 200:
                    print(f"HTTP error while trying to get holidays: {resp}")
                    data = {
                        "error": f"HTTP error while trying to get holidays: {resp}",
                    }
                else:
                    data = await resp.json()
            if data["error"] != "none":
                await messages_chat.send_message(f"Error while trying to check today's holidays: {data['error']}", creator)
            else:
                if data.get("holidays", None):
                    msg = f"Here is a list of all the holidays today:\n"
                    msg += "\n".join(f"* [{holiday['name']}]({holiday['url']})" for holiday in data["holidays"])
                    await messages_chat.send_message(msg, creator)
            print("Done checking for holidays.")
            print("Checking for a new xkcd...")
            comic = await xkcd.get_comic()
            if comic['num'] <= last_xkcd:
                print(f"No new xkcd found (latest is {comic['num']}).")
            else:
                print(f"New comic found! (#{comic['num']})")
                xkcd_creator = pyryver.Creator(creator.name, util.XKCD_PROFILE)
                await messages_chat.send_message(f"New xkcd!\n\n{xkcd.comic_to_str(comic)}", xkcd_creator)
                # Update xkcd number
                last_xkcd = comic['num']
                save_config()
            print("Daily message sent.")
            # Sleep for an entire day
            await asyncio.sleep(60 * 60 * 24)
    except asyncio.CancelledError:
        pass


def schedule_daily_message():
    """
    Start the daily message task with the correct delay.
    """
    # Cancel the existing task
    global daily_message_task
    if daily_message_task:
        daily_message_task.cancel()
    
    if not daily_message_time:
        print("Daily message not scheduled because time isn't defined.")
        return
    t = datetime.strptime(daily_message_time, "%H:%M")
    now = util.current_time()
    # Get that time, today
    t = datetime.combine(now, t.time(), tzinfo=tz.gettz(org_tz))
    # If already passed, get that time the next day
    if t < now:
        t += timedelta(days=1)
    init_delay = (t - now).total_seconds()
    print(f"Daily message re-scheduled, starting after {init_delay} seconds.")
    daily_message_task = asyncio.ensure_future(daily_message(init_delay))


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
        print(f"Error while loading roles: {e}. Defaulting to {{}}.")
        roles = CaseInsensitiveDict()
    # Load config
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        errs = init_config(ryver, config)
        if errs:
            print("Error loading config:", *errs, sep="\n")
            await home_chat.send_message("Error loading config:\n" + "\n".join(errs), creator)
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print(f"Error while loading config: {e}. Using the following defaults:")
        # Call init_config with an empty dict so variables are initialized to their defaults
        # Ignore errors
        init_config(ryver, {})
    # Load trivia questions
    try:
        with open(TRIVIA_FILE, "r") as f:
            trivia_questions = json.load(f)
        trivia.set_custom_trivia_questions(trivia_questions)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error while loading custom trivia questions: {e}")
