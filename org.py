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
ROLES_FILE = "data/roles.json"

def load_roles():
    """
    Load roles from the JSON file specified by ROLES_FILE.
    """
    global roles
    try:
        with open(ROLES_FILE, "r") as f:
            roles = json.load(f)
    except json.JSONDecodeError as e:
        roles = roles or {}
        print(f"Error while loading roles: {e}")
    except FileNotFoundError as e:
        roles = roles or {}
        print(f"Roles file does not exist!")


def save_roles():
    """
    Save roles to the JSON file specified by ROLES_FILE.
    """
    with open(ROLES_FILE, "w") as f:
        json.dump(roles, f)


def init():
    """
    Initialize everything.
    """
    global ryver, forums, teams, users, user_avatars, chat
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

    load_roles()
