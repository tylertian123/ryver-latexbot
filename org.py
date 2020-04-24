import json
import os
import pyryver
import requests

ryver = None
forums = []
teams = []
users = []
user_avatars = {}
chat = None

roles = {}
admins = set()
events = []
ROLES_FILE = "data/roles.json"
CONFIG_FILE = "data/config.json"
EVENTS_FILE = "data/events.json"

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
        "admins": list(admins)
    }


def init_config(config):
    """
    Initialize config data from a config dict.
    """
    global admins
    admins = set(config["admins"])


def save_config():
    """
    Save config to the JSON file specified by CONFIG_FILE.
    """
    with open(CONFIG_FILE, "w") as f:
        json.dump(make_config(), f)


def save_events():
    """
    Save events to the JSON file specified by EVENTS_FILE.
    """
    with open(EVENTS_FILE, "w") as f:
        json.dump(events, f)


def init():
    """
    Initialize everything.
    """
    global ryver, forums, teams, users, user_avatars, chat, roles
    if not ryver:
        ryver = pyryver.Ryver(os.environ["LATEXBOT_ORG"], os.environ["LATEXBOT_USER"], os.environ["LATEXBOT_PASS"])
    forums = ryver.get_chats(pyryver.TYPE_FORUM)
    teams = ryver.get_chats(pyryver.TYPE_TEAM)
    users = ryver.get_chats(pyryver.TYPE_USER)

    # Get user avatar URLs
    # This information is not included in the regular user info
    # It is retrieved from a different URL
    resp = requests.post(ryver.url_prefix +
                         "Ryver.Info()?$format=json", headers=ryver.headers)
    resp.raise_for_status()
    users_json = resp.json()["d"]["users"]
    user_avatars = {u["id"]: u["avatarUrl"] for u in users_json}

    chat = pyryver.get_obj_by_field(forums, pyryver.FIELD_NAME, "Test")

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
    # Load events
    try:
        with open(EVENTS_FILE, "r") as f:
            events = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error while loading events: {e}")
