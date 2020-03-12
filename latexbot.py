import pyryver
from quicklatex_render import ql_render
from random import randrange
from traceback import format_exc
from datetime import datetime
import shlex
import time
import os
import requests
import typing
import sys
import io
import json
import re

# Make print() flush immediately
# Otherwise the logs won't show up in real time in Docker
old_print = print


def print(*args, **kwargs):
    kwargs["flush"] = True
    # Add timestamp
    old_print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), *args, **kwargs)


ryver = pyryver.Ryver(
    os.environ["LATEXBOT_ORG"], os.environ["LATEXBOT_USER"], os.environ["LATEXBOT_PASS"])

print("LaTeX Bot has been started.")
print("Updating forums/teams/users list...")
forums = ryver.get_cached_chats(pyryver.TYPE_FORUM, force_update=True)
teams = ryver.get_cached_chats(pyryver.TYPE_TEAM, force_update=True)
users = ryver.get_cached_chats(pyryver.TYPE_USER, force_update=True)

print("Getting user avatar URLs...")
# Get user avatar URLs
# This information is not included in the regular user info
# It is retrieved from a different URL
resp = requests.post(ryver.url_prefix +
                     "Ryver.Info()?$format=json", headers=ryver.headers)
resp.raise_for_status()
users_json = resp.json()["d"]["users"]
user_avatars = {u["id"]: u["avatarUrl"] for u in users_json}

print("Initializing...")
chat = pyryver.get_obj_by_field(forums, pyryver.FIELD_NAME, "Test")

version = "v0.3.6"

creator = pyryver.Creator(f"LaTeX Bot {version}", "")

# Current admins are: @tylertian, @moeez
admins = set([1311906, 1605991])
enabled = True

# Auto generated later
help_text = ""


def _render(chat: pyryver.Chat, msg: pyryver.ChatMessage, formula: str):
    """
    {
        "group": "Basic Commands",
        "syntax": "<formula>",
        "description": "Render a LaTeX formula."
    }
    """
    if len(formula) > 0:
        img = ql_render(formula)
        chat.send_message(f"![{formula}]({img})", creator)
    else:
        chat.send_message("Formula can't be empty.", creator)


def _help(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Basic Commands",
        "syntax": "",
        "description": "Get a list of all the commands."
    }
    """
    chat.send_message(help_text, creator)


def _ping(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Basic Commands",
        "syntax": "",
        "description": "I will respond with 'Pong' if I'm here."
    }
    """
    chat.send_message("Pong", creator)


yes_msgs = [
    "Yes.",
    "I like it!",
    "Brilliant!",
    "Genius!",
    "Do it!",
    "It's good.",
    ":thumbsup:",
]
no_msgs = [
    "No.",
    ":thumbsdown:",
    "I hate it.",
    "Please no.",
    "It's bad.",
    "It's stupid.",
]


def _whatdoyouthink(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Basic Commands",
        "syntax": "<thing>",
        "description": "Ask my opinion of a thing!"
    }
    """
    msgs = yes_msgs if randrange(2) == 0 else no_msgs
    chat.send_message(msgs[randrange(len(msgs))], creator)


COMPETITIONS = None


def _howmanydaysuntilcomp(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Basic Commands",
        "syntax": "",
        "description": "How many days until the next competition?"
    }
    """
    global COMPETITIONS
    # Load competitions if not already loaded
    if not COMPETITIONS:
        COMPETITIONS = []
        with open("comps.json", "r") as comps_json:
            comps = json.load(comps_json)
            for comp in comps["comps"]:
                COMPETITIONS.append((comp["name"], datetime.strptime(
                    comp["start"], "%Y-%m-%d"), datetime.strptime(comp["end"], "%Y-%m-%d")))
    now = datetime.now()
    for comp in COMPETITIONS:
        diff = days_diff(comp[1], now)
        if diff > 0:
            chat.send_message(f"{diff} days left until {comp[0]}.", creator)
            return
        else:
            end_diff = days_diff(comp[2], now)
            if end_diff > 0:
                chat.send_message(f"{comp[0]} is ongoing.", creator)
                return
    chat.send_message("No upcoming events.", creator)


def _deletemessages(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Administrative Commands",
        "syntax": "<count>",
        "description": "Delete the last <count> messages."
    }
    """
    count = 0
    try:
        count = int(s)
    except ValueError:
        chat.send_message("Invalid number.", creator)
        return
    msgs = chat.get_message_from_id(msg.get_id(), before=count)
    for message in msgs:
        message.delete()


def _movemessages(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Administrative Commands",
        "syntax": "moveMessages <count> [(name|nickname)=]<forum|team>",
        "description": "Move the last <count> messages to another forum or team."
    }
    """
    s = s.split(" ")
    if len(s) < 2:
        chat.send_message("Invalid syntax.", creator)
        return

    count = 0
    try:
        count = int(s[0])
    except ValueError:
        chat.send_message("Invalid number.", creator)
        return

    to = get_chat_from_str(" ".join(s[1:]))
    if not to:
        chat.send_message("Forum/team not found", creator)
        return

    msgs = []
    # Get around the 25 message restriction
    msgs = chat.get_message_from_id(msg.get_id(), before=min(25, count))[:-1]
    count -= len(msgs)
    while count > 0:
        prev_msgs = chat.get_message_from_id(
            msgs[0].get_id(), before=min(25, count))[:-1]
        msgs = prev_msgs + msgs
        count -= len(prev_msgs)

    to.send_message(f"# Begin Moved Message\n\n---", creator)

    for msg in msgs:
        # Get the creator
        msg_creator = msg.get_creator()
        # If no creator then get author
        if not msg_creator:
            # First attempt to search for the ID in the list
            # if that fails then get it directly using a request
            msg_author = pyryver.get_obj_by_field(
                users, pyryver.FIELD_ID, msg.get_author_id()) or msg.get_author()
            # Pretend to be another person
            msg_creator = pyryver.Creator(
                msg_author.get_display_name(), user_avatars.get(msg_author.get_id(), ""))

        msg_body = sanitize(msg.get_body())
        # Handle reactions
        # Because reactions are from multiple people they can't really be moved the same way
        if msg.get_reactions():
            msg_body += "\n"
            for emoji, people in msg.get_reactions().items():
                # Instead for each reaction, append a line at the bottom with the emoji
                # and every user's display name who reacted with the reaction
                u = [pyryver.get_obj_by_field(
                    users, pyryver.FIELD_ID, person) for person in people]
                msg_body += f"\n:{emoji}:: {', '.join([user.get_display_name() if user else 'unknown' for user in u])}"

        msg_id = to.send_message(msg_body, msg_creator)
        msg.delete()
    msgs[-1].delete()

    to.send_message("---\n\n# End Moved Message", creator)


def _getuserroles(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Roles Commands",
        "syntax": "<user>",
        "description": "List all roles of a user."
    }
    """
    # Mentions
    if s.startswith("@"):
        s = s[1:]
    user = pyryver.get_obj_by_field(users, pyryver.FIELD_USER_USERNAME, s)
    if not user:
        chat.send_message("Error: User not found.", creator)
        return
    roles = "\n".join(parse_roles(user.get_about()))
    if roles:
        chat.send_message(
            f"User '{s}' has the following roles:\n{roles}", creator)
    else:
        chat.send_message(f"User '{s}' has no roles.", creator)


def _getallroles(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Roles Commands",
        "syntax": "",
        "description": "List all roles and users with those roles."
    }
    """
    all_roles = {}
    for user in users:
        if user.get_activated():
            roles = parse_roles(user.get_about())
            for role in roles:
                if role in all_roles:
                    all_roles[role].append(user.get_username())
                else:
                    all_roles[role] = [user.get_username()]

    if all_roles:
        roles_str = "\n".join(
            [f"**{role}**: {', '.join(usernames)}" for role, usernames in all_roles.items()])
        chat.send_message(f"All roles:\n{roles_str}", creator)
    else:
        chat.send_message(f"There are currently no roles.", creator)


def _atrole(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Roles Commands",
        "syntax": "<roles> [message]",
        "description": "@'s all users with a role. Roles are in a comma-separated list, e.g. Foo,Bar,Baz."
    }
    """
    mention_roles = []
    message = ""
    try:
        # Try to separate the role and the message
        role = s[:s.index(" ")]
        # Split by commas and strip
        mention_roles = set([r.strip() for r in role.split(",")])
        message = s[s.index(" ") + 1:]
    except ValueError:
        # If space not found, the entire string is the role
        role = s
        # Split by commas and strip
        mention_roles = set([r.strip() for r in role.split(",")])
    usernames = []

    # Check roles for each user
    for user in users:
        if user.get_activated():
            user_roles = parse_roles(user.get_about())
            # Test if the union of the two roles sets has any elements
            # i.e. See if there are any elements common to both
            if set(user_roles) & mention_roles:
                usernames.append("@" + user.get_username())

    if len(usernames) == 0:
        chat.send_message("Error: No users have that role.", creator)
        return

    author = msg.get_author()
    # Pretend to be the creator
    msg_creator = pyryver.Creator(
        author.get_display_name(), user_avatars.get(author.get_id(), ""))
    chat.send_message(f"{' '.join(usernames)}\n{message}", msg_creator)
    # Get rid of the original message
    msg.delete()


def _addtorole(chat: pyryver.Chat, msg: pyryver.Message, s: str):
    """
    {
        "group": "Roles Commands",
        "syntax": "<roles> <people>",
        "description": "Add people to a role. Note role names cannot contain spaces or commas. Roles are in a comma-separated list, e.g. Foo,Bar,Baz."
    }
    """
    args = s.split(" ")
    if len(args) < 2:
        chat.send_message("Invalid syntax.", creator)
        return

    roles = [r.strip() for r in args[0].split(",")]
    for username in args[1:]:
        if username.startswith("@"):
            # The username can begin with an @ for mentions
            username = username[1:]
        user = pyryver.get_obj_by_field(
            users, pyryver.FIELD_USER_USERNAME, username)
        if not user:
            chat.send_message(
                f"User '{username}' not found! Try `@latexbot updateChats` to update the list of users.\nSkipping...", creator)
            continue
        # Watch out for no about
        existing_roles = parse_roles(
            user.get_about()) if user.get_about() else []

        # Add each role
        for role in roles:
            if role in existing_roles:
                chat.send_message(
                    f"Warning: User '{username}' already has role '{role}'.", creator)
                continue

            user.set_profile(about=(user.get_about() or "") +
                             f"\n<Role: {role}>")

    chat.send_message("Operation successful.", creator)


def _removefromrole(chat: pyryver.Chat, msg: pyryver.Message, s: str):
    """
    {
        "group": "Roles Commands",
        "syntax": "<roles> <people>",
        "description": "Remove people from a role. Roles are in a comma-separated list, e.g. Foo,Bar,Baz."
    }
    """
    args = s.split(" ")
    if len(args) < 2:
        chat.send_message("Invalid syntax.", creator)
        return

    roles = [r.strip() for r in args[0].split(",")]
    for username in args[1:]:
        if username.startswith("@"):
            # The username can begin with an @ for mentions
            username = username[1:]
        user = pyryver.get_obj_by_field(
            users, pyryver.FIELD_USER_USERNAME, username)
        if not user:
            chat.send_message(
                f"User '{username}' not found! Try `@latexbot updateChats` to update the list of users.\nSkipping...", creator)
            continue
        # In case about is None
        if not user.get_about():
            chat.send_message(
                f"Warning: User '{username}' does not have any roles.", creator)
            continue
        # Filter out all the lines that have any of the roles in it
        role_strs = set([f"<Role: {role}>" for role in roles])
        about = '\n'.join(
            [l for l in user.get_about().split("\n") if l not in role_strs])
        if len(about) == len(user.get_about()):
            chat.send_message(
                f"Warning: User '{username}' does not have any of the roles listed.", creator)
            continue
        user.set_profile(about=about)

    chat.send_message("Operation successful.", creator)


def _disable(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Developer Commands",
        "syntax": "",
        "description": "Disable me."
    }
    """
    global enabled
    enabled = False
    chat.send_message("LaTeX Bot disabled.", creator)


def _kill(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Developer Commands",
        "syntax": "",
        "description": "Kill me (:fearful:)."
    }
    """
    chat.send_message("Goodbye, world.", creator)
    # Simulate Ctrl+C
    raise KeyboardInterrupt


def _sleep(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Developer Commands",
        "syntax": "<seconds>",
        "description": "Put me to sleep."
    }
    """
    secs = 0
    try:
        secs = float(s)
    except ValueError:
        chat.send_message("Invalid number.", creator)
        return
    chat.send_message("Good night! :sleeping:", creator)
    time.sleep(secs)
    chat.send_message("Good morning!", creator)


def _execute(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Developer Commands",
        "syntax": "<code>",
        "description": "Execute arbitrary Python code."
    }
    """
    # Temporarily replace stdout and stderr
    stdout = sys.stdout
    stderr = sys.stderr
    # Merge stdout and stderr
    try:
        sys.stdout = io.StringIO()
        sys.stderr = sys.stdout
        exec(s, globals(), locals())
        output = sys.stdout.getvalue()

        chat.send_message(output, creator)
    except Exception as e:
        chat.send_message(
            f"An exception has occurred:\n{format_exc()}", creator)
    finally:
        sys.stdout = stdout
        sys.stderr = stderr


def _changeaccess(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Developer Commands",
        "syntax": "<command> <level>",
        "description": "Change the access level of a command."
    }
    """
    s = s.split()
    if len(s) != 2:
        chat.send_message(f"Invalid syntax.", creator)
        return

    cmd, level = s
    try:
        level = int(level)
    except ValueError:
        chat.send_message(f"Invalid number.", creator)
        return

    try:
        command_processors[cmd][1] = level
        regenerate_help_text()
        chat.send_message(f"Access levels updated.", creator)
    except KeyError:
        chat.send_message(f"Command not found.", creator)


def _makeadmin(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Developer Commands",
        "syntax": "<user>",
        "description": "Make a user a Bot Admin."
    }
    """
    if s.startswith("@"):
        s = s[1:]

    user = pyryver.get_obj_by_field(users, pyryver.FIELD_USERNAME, s)
    if not user:
        chat.send_message(f"User not found.", creator)
        return
    admins.add(user.get_id())
    regenerate_help_text()
    chat.send_message(f"User {s} has been added to Bot Admins.")


def _removeadmin(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Developer Commands",
        "syntax": "<user>",
        "description": "Remove a user from Bot Admins."
    }
    """
    if s.startswith("@"):
        s = s[1:]

    user = pyryver.get_obj_by_field(users, pyryver.FIELD_USERNAME, s)
    if not user:
        chat.send_message(f"User not found.", creator)
        return
    try:
        admins.remove(user.get_id())
        regenerate_help_text()
        chat.send_message(f"User {s} is no longer a Bot Admin.")
    except KeyError:
        chat.send_message(f"User {s} is not a Bot Admin.", creator)


def _updatechats(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Miscellaneous Commands",
        "syntax": "",
        "description": "Update the list of forums/teams and users."
    }
    """
    global forums, teams, users, user_avatars
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
    chat.send_message("Forums/Teams/Users updated.", creator)


def _moveto(_chat: pyryver.Chat, msg: pyryver.ChatMessage, name: str):
    """
    {
        "group": "Miscellaneous Commands",
        "syntax": "[(name|nickname)=]<forum|team>",
        "description": "Move my home to another forum/team."
    }
    """
    global chat
    if len(name) > 0:
        # Find new chat
        new_chat = get_chat_from_str(name)
        if not new_chat:
            # Note the underscore
            _chat.send_message("Forum/team not found.", creator)
        else:
            _chat.send_message(f"LaTeX Bot has moved to {name}.", creator)
            chat = new_chat
            chat.send_message("LaTeX Bot has moved here.", creator)


def _setactivated(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Hidden Commands",
        "syntax": "<user>",
        "description": "Activates or deactivates a user.",
        "hidden": true
    }
    """
    s = s.split()

    if len(s) != 2:
        chat.send_message("Invalid syntax.", creator)
        return

    username = s[0]
    if username.startswith("@"):
        username = username[1:]

    activate = True
    if s[1] == "True" or s[1] == "true":
        activate = True
    elif s[1] == "False" or s[1] == "false":
        activate = False
    else:
        chat.send_message("Invalid syntax.", creator)
        return

    user = pyryver.get_obj_by_field(users, pyryver.FIELD_USERNAME, s)
    if not user:
        chat.send_message(f"User not found.", creator)
        return
    user.set_activated(activate)
    chat.send_message(f"User {username} changed.", creator)


def _impersonate(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    {
        "group": "Hidden Commands",
        "syntax": "<displayname> <avatarurl>",
        "description": "Impersonates someone.",
        "hidden": true
    }
    """
    global creator
    s = shlex.split(s)
    if len(s) != 2:
        chat.send_message("Invalid syntax.", creator)
        return
    creator = pyryver.Creator(s[0], s[1])
    chat.send_message(f"I am now someone else.", creator)


ACCESS_LEVEL_EVERYONE = 0
ACCESS_LEVEL_FORUM_ADMIN = 1
ACCESS_LEVEL_ORG_ADMIN = 2
ACCESS_LEVEL_BOT_ADMIN = 3
ACCESS_LEVEL_TYLER = 9001

ACCESS_LEVEL_STRS = {
    ACCESS_LEVEL_EVERYONE: "",
    ACCESS_LEVEL_FORUM_ADMIN: "**Accessible to Forum, Org and Bot Admins only.**",
    ACCESS_LEVEL_ORG_ADMIN: "**Accessible to Org and Bot Admins only.**",
    ACCESS_LEVEL_BOT_ADMIN: "**Accessible to Bot Admins only.**",
    ACCESS_LEVEL_TYLER: "**Accessible to Tyler only.**"
}


command_processors = {
    "render": [_render, ACCESS_LEVEL_EVERYONE],
    "help": [_help, ACCESS_LEVEL_EVERYONE],
    "ping": [_ping, ACCESS_LEVEL_EVERYONE],
    "whatDoYouThink": [_whatdoyouthink, ACCESS_LEVEL_EVERYONE],
    "howManyDaysUntilComp": [_howmanydaysuntilcomp, ACCESS_LEVEL_EVERYONE],

    "deleteMessages": [_deletemessages, ACCESS_LEVEL_FORUM_ADMIN],
    "moveMessages": [_movemessages, ACCESS_LEVEL_FORUM_ADMIN],

    "getUserRoles": [_getuserroles, ACCESS_LEVEL_EVERYONE],
    "getAllRoles": [_getallroles, ACCESS_LEVEL_EVERYONE],
    "@role": [_atrole, ACCESS_LEVEL_EVERYONE],
    "addToRole": [_addtorole, ACCESS_LEVEL_ORG_ADMIN],
    "removeFromRole": [_removefromrole, ACCESS_LEVEL_ORG_ADMIN],

    # "disable": [_disable, ACCESS_LEVEL_ORG_ADMIN],
    "kill": [_kill, ACCESS_LEVEL_BOT_ADMIN],
    "sleep": [_sleep, ACCESS_LEVEL_BOT_ADMIN],
    "execute": [_execute, ACCESS_LEVEL_BOT_ADMIN],
    "changeAccess": [_changeaccess, ACCESS_LEVEL_TYLER],
    "makeAdmin": [_makeadmin, ACCESS_LEVEL_TYLER],
    "removeAdmin": [_removeadmin, ACCESS_LEVEL_TYLER],

    "updateChats": [_updatechats, ACCESS_LEVEL_FORUM_ADMIN],
    "moveTo": [_moveto, ACCESS_LEVEL_ORG_ADMIN],

    "setActivated": [_setactivated, ACCESS_LEVEL_TYLER],
    "impersonate": [_impersonate, ACCESS_LEVEL_TYLER],
}


def is_authorized(chat: pyryver.Chat, msg: pyryver.ChatMessage, level: int) -> bool:
    if level <= ACCESS_LEVEL_EVERYONE:
        return True

    if level <= ACCESS_LEVEL_TYLER and msg.get_author_id() == 1311906:
        return True

    if level <= ACCESS_LEVEL_BOT_ADMIN and msg.get_author_id() in admins:
        return True

    user = pyryver.get_obj_by_field(
        users, pyryver.FIELD_ID, msg.get_author_id())
    if not user:
        return False

    if level <= ACCESS_LEVEL_ORG_ADMIN and user.is_admin():
        return True

    is_forum_admin = False
    if isinstance(chat, pyryver.GroupChat):
        member = chat.get_member(msg.get_author_id())
        if member:
            is_forum_admin = member.is_admin()

    if level <= ACCESS_LEVEL_FORUM_ADMIN and is_forum_admin:
        return True

    return False


access_denied_messages = [
    "I'm sorry Dave, I'm afraid I can't do that.",
    "ACCESS DENIED",
    "![NO](https://i.kym-cdn.com/photos/images/original/001/483/348/bdd.jpg)",
    "This operation requires a higher access level. Please ask an admin.",
    "Nice try.",
    "![Access Denied](https://cdn.windowsreport.com/wp-content/uploads/2018/08/fix-access-denied-error-windows-10.jpg)",
    "![No.](https://i.imgur.com/DKUR9Tk.png)",
    "![No](https://pics.me.me/thumb_no-no-meme-face-hot-102-7-49094780.png)",
]


def get_access_denied_message() -> str:
    return access_denied_messages[randrange(len(access_denied_messages))]


def get_chat_from_str(name: str) -> pyryver.Chat:
    field = pyryver.FIELD_NAME
    # Handle the name= or nickname= syntax
    if name.startswith("name="):
        field = pyryver.FIELD_NAME
        # Slice off the beginning
        name = name[name.index("=") + 1:]
    elif name.startswith("nickname="):
        field = pyryver.FIELD_NICKNAME
        name = name[name.index("=") + 1:]
    return pyryver.get_obj_by_field(forums + teams, field, name)


def parse_roles(about: str) -> typing.List[str]:
    if not about:
        return []
    roles = []
    for line in about.split("\n"):
        if line.startswith("<Role: ") and line.endswith(">"):
            role = line[line.index(":") + 2:-1]
            # roles cannot have spaces
            if " " in role:
                continue
            roles.append(role)
    return roles


def days_diff(a: datetime, b: datetime) -> int:
    diff = a - b
    if diff.seconds > 0:
        return diff.days + 1
    return diff.days


mention_regex = re.compile(r"(\s|^)@(\w+)(?=\s|$)", flags=re.MULTILINE)


def sanitize(msg: str) -> str:
    """
    Sanitize the given input text.

    Currently, this method makes all mentions ineffective by adding a backslash before the @.
    """
    return mention_regex.sub(r"\1\@\2", msg)


def regenerate_help_text():
    global help_text
    help_text = ""
    commands = {}
    for name, command in command_processors.items():
        try:
            properties = json.loads(command[0].__doc__ or "")
            try:
                if properties["hidden"] == True:
                    continue
            except KeyError:
                pass
            syntax = f"`@latexbot {name} {properties['syntax']}`" if properties["syntax"] else f"`@latexbot {name}`"
            cmd = f"{syntax} - {properties['description']} {ACCESS_LEVEL_STRS[command[1]]}"
            group = properties['group']
            if group in commands:
                commands[group].append(cmd)
            else:
                commands[group] = [cmd]
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse doc for command {name}!\n{e}")
            pass

    for group, cmds in commands.items():
        help_text += group + ":\n"
        for cmd in cmds:
            help_text += f"  - {cmd}\n"
        help_text += "\n"
    help_text += f"\nCurrent Bot Admins are: {', '.join([pyryver.get_obj_by_field(users, pyryver.FIELD_ID, uid).get_display_name() for uid in admins])}."


if __name__ == "__main__":
    # Auto-generate help text
    print("Auto-generating help text...")
    regenerate_help_text()

    print("LaTeX Bot is running!")
    chat.send_message(
        f"LaTeX Bot {version} is online! Note that to reduce load, I only check messages once per 3 seconds or more!", creator)
    chat.send_message(help_text, creator)

    while True:
        try:
            # Clear notifs
            ryver.mark_all_notifs_read()
            while True:
                notifs = ryver.get_notifs(unread=True)
                if len(notifs) > 0:
                    ryver.mark_all_notifs_read()

                for notif in notifs:
                    print("New notification received!")
                    # Verify that the notification is a mention
                    if not notif.get_predicate() == pyryver.NOTIF_PREDICATE_MENTION:
                        print("Notification was not a direct mention. Skipping...")
                        continue

                    via = notif.get_via()
                    # Little bit of magic here
                    message_id = via["id"]
                    chat_id = via["workroom"]["id"]
                    chat_source = pyryver.get_obj_by_field(
                        forums + teams, pyryver.FIELD_ID, chat_id)
                    if not chat_source:
                        print("Error: Cannot find chat for: " + str(via))
                        chat.send_message(
                            "Error: Cannot find source of message. Try `@latexbot updateChats`.", creator)
                        continue
                    # We need to get the actual message from the chat, because the one in the notification may be cut off
                    chat_message = chat_source.get_message_from_id(message_id)[
                        0]
                    text = chat_message.get_body().split(" ")

                    if text[0] == "@latexbot" and len(text) >= 2:
                        print(
                            f"Command received from user {chat_message.get_author_id()}: " + " ".join(text))

                        if enabled:
                            if text[1] in command_processors:
                                # Check access level
                                if not is_authorized(chat_source, chat_message, command_processors[text[1]][1]):
                                    chat_source.send_message(
                                        get_access_denied_message(), creator)
                                    print("Access was denied.")
                                else:
                                    command_processors[text[1]][0](
                                        chat_source, chat_message, " ".join(text[2:]))
                                    print("Command processed.")
                            else:
                                chat_source.send_message(
                                    "Sorry, I didn't understand what you were asking me to do.", creator)
                                print("Command syntax was invalid.")
                        elif text[1] == "enable":
                            if not is_authorized(chat_source, chat_message, ACCESS_LEVEL_ORG_ADMIN):
                                chat.send_message(
                                    get_access_denied_message(), creator)
                            else:
                                enabled = True
                                chat_source.send_message("I'm alive!", creator)
                                print("Command processed.")
                    else:
                        print("Notification was not a proper command. Skipping...")

                time.sleep(1)
        except KeyboardInterrupt:
            break
        except Exception as e:
            msg = format_exc()
            print("Unexpected exception:")
            print(msg)
            # Sleep for 10 seconds to hopefully have the connection fix itself
            time.sleep(10)
            chat.send_message(
                "An unexpected error has occurred:\n```\n" + msg + "\n```", creator)
            chat.send_message(
                "@tylertian Let's hope that never happens again.", creator)

    chat.send_message("LaTeX Bot has been killed. Goodbye!", creator)
