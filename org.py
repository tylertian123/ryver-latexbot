import json
import latexbot
import os
import pyryver
import requests
import sched
import time
import gcalendar

ryver = None
forums = []
teams = []
users = []
user_avatars = {}

roles = {}
admins = set()
org_tz = None
home_chat = None
announcements_chat = None
messages_chat = None
calendar_id = None
daily_message_time = None
last_xkcd = None
ROLES_FILE = "data/roles.json"
CONFIG_FILE = "data/config.json"

SERVICE_ACCOUNT_FILE = "calendar_credentials.json"
calendar = gcalendar.Calendar(SERVICE_ACCOUNT_FILE)

scheduler = sched.scheduler(time.time, time.sleep)
daily_message_event = None

def save_roles():
    """
    Save roles to the JSON file specified by ROLES_FILE.
    """
    with open(ROLES_FILE, "w") as f:
        json.dump(roles, f)


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
    }


def init_config(config):
    """
    Initialize config data from a config dict.
    """
    global admins, org_tz, home_chat, announcements_chat, calendar_id, daily_message_time, messages_chat, last_xkcd
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
        home_chat = pyryver.get_obj_by_field(forums, pyryver.FIELD_NICKNAME, config["homeChat"])
    except KeyError:
        print("Error: 'homeChat' not specified. Defaulting to +Test or leaving unchanged.")
        home_chat = home_chat or pyryver.get_obj_by_field(forums, pyryver.FIELD_NICKNAME, "Test")
    try:
        announcements_chat = pyryver.get_obj_by_field(forums, pyryver.FIELD_NICKNAME, config["announcementsChat"])
    except KeyError:
        print("Error: 'announcementsChat' not specified. Defaulting to +Gen or leaving unchanged.")
        announcements_chat = announcements_chat or pyryver.get_obj_by_field(forums, pyryver.FIELD_NICKNAME, "Gen")
    try:
        messages_chat = pyryver.get_obj_by_field(forums, pyryver.FIELD_NICKNAME, config["messagesChat"])
    except KeyError:
        print("Error: 'messagesChat' not specified. Defaulting to +Test or leaving unchanged.")
        messages_chat = messages_chat or pyryver.get_obj_by_field(forums, pyryver.FIELD_NICKNAME, "Test")
    try:
        calendar_id = config["googleCalendarId"]
    except KeyError:
        print("Error: 'googleCalendarId' not specified. Defaulting to null or leaving unchanged.")
    try:
        daily_message_time = config["dailyMessageTime"]
    except KeyError:
        print("Error: 'dailyMessageTime' not specified. Defaulting to null or leaving unchanged.")
    if daily_message_time:
        # Cancel the existing event
        if daily_message_event:
            scheduler.cancel(daily_message_event)
        latexbot.schedule_next_message()
    try:
        last_xkcd = config["lastXKCD"]
    except KeyError:
        print("Error: 'lastXKCD' not specified. Defaulting to 0 or leaving unchanged.")
        last_xkcd = last_xkcd or 0


def save_config():
    """
    Save config to the JSON file specified by CONFIG_FILE.
    """
    with open(CONFIG_FILE, "w") as f:
        json.dump(make_config(), f)


def init(force_reload=False):
    """
    Initialize everything.

    If force_reload is True, cached data will not be used.
    """
    global ryver, forums, teams, users, user_avatars, roles
    if not ryver:
        ryver = pyryver.Ryver(os.environ["LATEXBOT_ORG"], os.environ["LATEXBOT_USER"], os.environ["LATEXBOT_PASS"])
    forums = ryver.get_cached_chats(pyryver.TYPE_FORUM, name="data/pyryver.forums.json", force_update=force_reload)
    teams = ryver.get_cached_chats(pyryver.TYPE_TEAM, name="data/pyryver.teams.json", force_update=force_reload)
    users = ryver.get_cached_chats(pyryver.TYPE_USER, name="data/pyryver.users.json", force_update=force_reload)

    # Get user avatar URLs
    # This information is not included in the regular user info
    # It is retrieved from a different URL
    resp = requests.post(ryver.url_prefix +
                         "Ryver.Info()?$format=json", headers=ryver.headers)
    resp.raise_for_status()
    users_json = resp.json()["d"]["users"]
    user_avatars = {u["id"]: u["avatarUrl"] for u in users_json}

    # Load roles
    try:
        with open(ROLES_FILE, "r") as f:
            roles = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error while loading roles: {e}. Defaulting to [].")
        roles = []
    # Load config
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        init_config(config)
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print(f"Error while loading config: {e}. Using the following defaults:")
        # Call init_config with an empty dict so variables are initialized to their defaults
        init_config({})
        
