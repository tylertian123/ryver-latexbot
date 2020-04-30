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
org_tz = "EST5EDT"
home_chat = None
announcements_chat = None
calendar_id = None
event_reminder_time = None
ROLES_FILE = "data/roles.json"
CONFIG_FILE = "data/config.json"

SERVICE_ACCOUNT_FILE = "calendar_credentials.json"
calendar = gcalendar.Calendar(SERVICE_ACCOUNT_FILE)

scheduler = sched.scheduler(time.time, time.sleep)
reminder_event = None

def save_roles():
    """
    Save roles to the JSON file specified by ROLES_FILE.
    """
    with open(ROLES_FILE, "w") as f:
        json.dump(roles, f)


def make_config():
    """
    Generate a config dict to be saved as a JSON.
    """
    return {
        "admins": list(admins),
        "organizationTimeZone": org_tz,
        "homeChat": home_chat.get_nickname(),
        "announcementsChat": announcements_chat.get_nickname(),
        "googleCalendarId": calendar_id,
        "eventReminderTime": event_reminder_time,
    }


def init_config(config):
    """
    Initialize config data from a config dict.
    """
    global admins, org_tz, home_chat, announcements_chat, calendar_id, event_reminder_time
    admins = set(config["admins"])
    org_tz = config["organizationTimeZone"]
    home_chat = pyryver.get_obj_by_field(forums, pyryver.FIELD_NICKNAME, config["homeChat"])
    announcements_chat = pyryver.get_obj_by_field(forums, pyryver.FIELD_NICKNAME, config["announcementsChat"])
    calendar_id = config["googleCalendarId"]
    event_reminder_time = config["eventReminderTime"]
    if event_reminder_time:
        # Cancel the existing event
        if reminder_event:
            scheduler.cancel(reminder_event)
        latexbot.schedule_next_reminder()


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
        print(f"Error while loading roles: {e}")
    # Load config
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        init_config(config)
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print(f"Error while loading config: {e}")
        global home_chat, announcements_chat
        # Defaults for home and announcements
        home_chat = pyryver.get_obj_by_field(forums, pyryver.FIELD_NICKNAME, "Test")
        announcements_chat = pyryver.get_obj_by_field(forums, pyryver.FIELD_NICKNAME, "Gen")
