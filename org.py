import os
import pyryver
import requests

ryver = None
forums = []
teams = []
users = []
user_avatars = {}
chat = None

def init():
    """
    Initialize everything.
    """
    global ryver, forums, teams, users, user_avatars, chat
    if not ryver:
        ryver = pyryver.Ryver(os.environ["LATEXBOT_ORG"], os.environ["LATEXBOT_USER"], os.environ["LATEXBOT_PASS"])
    forums = ryver.get_cached_chats(pyryver.TYPE_FORUM, force_update=True)
    teams = ryver.get_cached_chats(pyryver.TYPE_TEAM, force_update=True)
    users = ryver.get_cached_chats(pyryver.TYPE_USER, force_update=True)

    # Get user avatar URLs
    # This information is not included in the regular user info
    # It is retrieved from a different URL
    resp = requests.post(ryver.url_prefix +
                         "Ryver.Info()?$format=json", headers=ryver.headers)
    resp.raise_for_status()
    users_json = resp.json()["d"]["users"]
    user_avatars = {u["id"]: u["avatarUrl"] for u in users_json}

    chat = pyryver.get_obj_by_field(forums, pyryver.FIELD_NAME, "Test")
