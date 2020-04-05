import io
import json
import org
import os
import pyryver
import re
import shlex
import sys
import time
import typing
from datetime import datetime
from latexbot_util import *
from quicklatex_render import ql_render
from random import randrange
from traceback import format_exc

# Make print() flush immediately
# Otherwise the logs won't show up in real time in Docker
old_print = print


def print(*args, **kwargs):
    kwargs["flush"] = True
    # Add timestamp
    old_print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), *args, **kwargs)


################################ GLOBAL VARIABLES AND CONSTANTS ################################

VERSION = "v0.3.8"

creator = pyryver.Creator(f"LaTeX Bot {VERSION}", "")

# Current admins are: @tylertian, @moeez
admins = set([1311906, 1605991])
enabled = True

# Auto generated later
help_text = ""
extended_help_text = {}

################################ UTILITY FUNCTIONS ################################


def generate_help_text():
    global help_text
    help_text = ""
    commands = {}
    for name, command in command_processors.items():
        try:
            # Parse the docstring as a JSON
            properties = json.loads(command[0].__doc__ or "")
            try:
                # Skip hidden commands
                if properties["hidden"] == True:
                    continue
            except KeyError:
                pass

            # Generate basic description
            syntax = f"`@latexbot {name} {properties['syntax']}`" if properties["syntax"] else f"`@latexbot {name}`"
            description = f"{syntax} - {properties['description']} {ACCESS_LEVEL_STRS[command[1]]}"
            group = properties['group']
            if group in commands:
                commands[group].append(description)
            else:
                commands[group] = [description]

            # Generate full description
            if "extended_description" in properties:
                extended_description = ''.join(properties["extended_description"])
            else:
                extended_description = "***No extended description provided.***"
            
            # Examples
            if "examples" in properties:
                examples = '\n'.join(f"`{example}`" for example in properties["examples"])
            else:
                examples = "***No examples provided.***"
            
            description += f"\n\n{extended_description}\n\n**Examples:**\n{examples}"
            extended_help_text[name] = description

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse doc for command {name}!\n{e}")
            pass

    for group, cmds in commands.items():
        help_text += group + ":\n"
        for description in cmds:
            help_text += f"  - {description}\n"
        help_text += "\n"
    help_text += f"\nCurrent Bot Admins are: {', '.join([pyryver.get_obj_by_field(org.users, pyryver.FIELD_ID, uid).get_display_name() for uid in admins])}."
    help_text += "\n\nFor more details about a command, try `@latexbot help <command>`."


################################ COMMAND PROCESSORS ################################


def _render(chat: pyryver.Chat, msg: pyryver.ChatMessage, formula: str):
    r"""
    {
        "group": "Basic Commands",
        "syntax": "<formula>",
        "description": "Render a LaTeX formula.",
        "extended_description": [
            "The formula is rendered in inline mode."
        ],
        "examples": [
            "@latexbot render f(x) = \\sum_{i=0}^{n} \\frac{a_i}{1+x}"
        ]
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
        "syntax": "[command]",
        "description": "Get a list of all the commands, or details about a command.",
        "extended_description": [
            "Use this command without any arguments to get an overview of all the commands, ",
            "or give the name of the command you would like to know more about."
        ],
        "examples": [
            "@latexbot help",
            "@latexbot help render"
        ]
    }
    """
    s = s.strip()
    if s == "":
        chat.send_message(help_text, creator)
    else:
        chat.send_message(extended_help_text.get(s, 
            f"Error: {s} is not a valid command, or does not have an extended description."), creator)


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
        "description": "Ask my opinion of a thing!",
        "extended_description": [
            "Disclaimer: These are my own opinions, Tyler is not responsible for anything said."
        ],
        "examples": [
            "@latexbot whatDoYouThink <insert controversial topic here>"
        ]
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
        diff = caldays_diff(comp[1], now)
        if diff > 0:
            chat.send_message(f"{diff} days left until {comp[0]}.", creator)
            return
        else:
            end_diff = caldays_diff(comp[2], now)
            if end_diff > 0:
                chat.send_message(
                    f"It is currently day {caldays_diff(now, comp[1]) + 1} of {comp[0]}.", creator)
                return
    chat.send_message("No upcoming events.", creator)


def _deletemessages(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    r"""
    {
        "group": "Administrative Commands",
        "syntax": "[<start>-]<end|count>",
        "description": "Delete messages.",
        "extended_description": [
            "If no <start> is provided, this command deletes the last <count>/<end> messages.\n",
            "If <start> is provided, this command deletes messages from <start> to <end> inclusive, with 1-based indexing.",
            "\n\nThe command message itself is always deleted."
        ],
        "examples": [
            "@latexbot deleteMessages 10",
            "@latexbot deleteMessages 10-20"
        ]
    }
    """
    try:
        # Try and parse the range
        if "-" in s:
            start = int(s[:s.index("-")].strip())
            s = s[s.index("-") + 1:].strip()
        else:
            start = 1
        end = int(s)
    except (ValueError, IndexError):
        chat.send_message("Invalid syntax.", creator)
        return

    # Cut off the end (newer messages)
    # Subtract 1 for 1-based indexing
    msgs = get_msgs_before(chat, msg.get_id(), end)[:-(start - 1)]
    for message in msgs:
        message.delete()
    msg.delete()


def _movemessages(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    r"""
    {
        "group": "Administrative Commands",
        "syntax": "[<start>-]<end|count> [(name|nickname)=]<forum|team>",
        "description": "Moves messages to another forum or team.",
        "extended_description": [
            "If no <start> is provided, this command moves the last <count>/<end> messages.\n",
            "If <start> is provided, this command moves messages from <start> to <end> inclusive, with 1-based indexing.\n\n",
            "By default this command goes by the display name of the forum/team. ",
            "Specify `nickname=` before the forum/team name to use nicknames instead.",
            "\n\nNote that reactions cannot be moved perfectly, and are instead shown with text."
        ],
        "examples": [
            "@latexbot moveMessages 10 Off-Topic",
            "@latexbot moveMessages 10-20 nickname=OffTopic"
        ]
    }
    """
    s = s.split(" ")
    if len(s) < 2:
        chat.send_message("Invalid syntax.", creator)
        return

    msg_range = s[0]
    try:
        # Try and parse the range
        if "-" in msg_range:
            start = int(msg_range[:msg_range.index("-")].strip())
            msg_range = msg_range[msg_range.index("-") + 1:].strip()
        else:
            start = 1
        end = int(msg_range)
    except (ValueError, IndexError):
        chat.send_message("Invalid syntax.", creator)
        return

    to = parse_chat_name(" ".join(s[1:]))
    if not to:
        chat.send_message("Forum/team not found", creator)
        return

    # Cut off the end (newer messages)
    # Subtract 1 for 1-based indexing
    msgs = get_msgs_before(chat, msg.get_id(), end)[:-(start - 1)]

    to.send_message(f"# Begin Moved Message\n\n---", creator)

    for msg in msgs:
        # Get the creator
        msg_creator = msg.get_creator()
        # If no creator then get author
        if not msg_creator:
            # First attempt to search for the ID in the list
            # if that fails then get it directly using a request
            msg_author = pyryver.get_obj_by_field(
                org.users, pyryver.FIELD_ID, msg.get_author_id()) or msg.get_author()
            # Pretend to be another person
            msg_creator = pyryver.Creator(
                msg_author.get_display_name(), org.user_avatars.get(msg_author.get_id(), ""))

        msg_body = sanitize(msg.get_body())
        # Handle reactions
        # Because reactions are from multiple people they can't really be moved the same way
        if msg.get_reactions():
            msg_body += "\n"
            for emoji, people in msg.get_reactions().items():
                # Instead for each reaction, append a line at the bottom with the emoji
                # and every user's display name who reacted with the reaction
                u = [pyryver.get_obj_by_field(
                    org.users, pyryver.FIELD_ID, person) for person in people]
                msg_body += f"\n:{emoji}:: {', '.join([user.get_display_name() if user else 'unknown' for user in u])}"

        msg_id = to.send_message(msg_body, msg_creator)
        msg.delete()
    msgs[-1].delete()

    to.send_message("---\n\n# End Moved Message", creator)


def _countmessagessince(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    r"""
    {
        "group": "Administrative Commands",
        "syntax": "<pattern>",
        "description": "Count the number of messages since the first message that matches a pattern.",
        "extended_description": [
            "This command counts messages from the first message that matches <pattern> to the command message (inclusive). ",
            "The search pattern is case insensitive.\n\n",
            "If <pattern> is surrounded with slashes /like so/, it is treated as a regex, with the multiline and ignorecase flags.\n\n",
            "This command will only search through the last 250 messages maximum."
        ],
        "examples": [
            "@latexbot countMessagesSince foo bar",
            "@latexbot countMessagesSince /(\\s|^)@(\\w+)(?=\\s|$)/"
        ]
    }
    """
    if s.startswith("/") and s.endswith("/"):
        try:
            expr = re.compile(s[1:-1], re.MULTILINE | re.IGNORECASE)
            # Use the regex search function as the match function
            match = expr.search
        except re.error as e:
            chat.send_message("Invalid regex: " + str(e), creator)
            return
    else:
        s = s.lower()
        # Case insensitive match
        def match(x): return x.lower().find(s) >= 0

    count = 1
    # Max search depth: 250
    while count < 250:
        # Reverse the messages as by default the oldest is the first
        # Search 50 at a time
        msgs = get_msgs_before(chat, msg.get_id(), 50)[::-1]
        for message in msgs:
            count += 1
            if match(message.get_body()):
                # Found a match
                chat.send_message(
                    f"There are a total of {count} messages, including your command but not this message.\n\nMessage matched (sent by {message.get_author().get_display_name()}):\n{sanitize(message.get_body())}", creator)
                return
        # No match - change anchor
        msg = msgs[-1]
    chat.send_message(
        "Error: Max search depth of 250 messages exceeded without finding a match.", creator)


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
    user = pyryver.get_obj_by_field(org.users, pyryver.FIELD_USER_USERNAME, s)
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
    for user in org.users:
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
    for user in org.users:
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
        author.get_display_name(), org.user_avatars.get(author.get_id(), ""))
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
            org.users, pyryver.FIELD_USER_USERNAME, username)
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
            org.users, pyryver.FIELD_USER_USERNAME, username)
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
        generate_help_text()
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

    user = pyryver.get_obj_by_field(org.users, pyryver.FIELD_USERNAME, s)
    if not user:
        chat.send_message(f"User not found.", creator)
        return
    admins.add(user.get_id())
    generate_help_text()
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

    user = pyryver.get_obj_by_field(org.users, pyryver.FIELD_USERNAME, s)
    if not user:
        chat.send_message(f"User not found.", creator)
        return
    try:
        admins.remove(user.get_id())
        generate_help_text()
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
    org.init()
    chat.send_message("Forums/Teams/Users updated.", creator)


def _moveto(chat: pyryver.Chat, msg: pyryver.ChatMessage, name: str):
    """
    {
        "group": "Miscellaneous Commands",
        "syntax": "[(name|nickname)=]<forum|team>",
        "description": "Move my home to another forum/team."
    }
    """
    if len(name) > 0:
        # Find new chat
        new_chat = parse_chat_name(name)
        if not new_chat:
            # Note the underscore
            chat.send_message("Forum/team not found.", creator)
        else:
            chat.send_message(f"LaTeX Bot has moved to {name}.", creator)
            org.chat = new_chat
            org.chat.send_message("LaTeX Bot has moved here.", creator)


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

    user = pyryver.get_obj_by_field(org.users, pyryver.FIELD_USERNAME, s)
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


command_processors = {
    "render": [_render, ACCESS_LEVEL_EVERYONE],
    "help": [_help, ACCESS_LEVEL_EVERYONE],
    "ping": [_ping, ACCESS_LEVEL_EVERYONE],
    "whatDoYouThink": [_whatdoyouthink, ACCESS_LEVEL_EVERYONE],
    "howManyDaysUntilComp": [_howmanydaysuntilcomp, ACCESS_LEVEL_EVERYONE],

    "deleteMessages": [_deletemessages, ACCESS_LEVEL_FORUM_ADMIN],
    "moveMessages": [_movemessages, ACCESS_LEVEL_FORUM_ADMIN],
    "countMessagesSince": [_countmessagessince, ACCESS_LEVEL_FORUM_ADMIN],

    "getUserRoles": [_getuserroles, ACCESS_LEVEL_EVERYONE],
    "getAllRoles": [_getallroles, ACCESS_LEVEL_EVERYONE],
    "@role": [_atrole, ACCESS_LEVEL_EVERYONE],
    "addToRole": [_addtorole, ACCESS_LEVEL_ORG_ADMIN],
    "removeFromRole": [_removefromrole, ACCESS_LEVEL_ORG_ADMIN],

    "disable": [_disable, ACCESS_LEVEL_ORG_ADMIN],
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


################################ OTHER FUNCTIONS ################################

def init():
    org.init()
    generate_help_text()


def start():
    while True:
        try:
            # Clear notifs
            org.ryver.mark_all_notifs_read()
            while True:
                notifs = org.ryver.get_notifs(unread=True)
                if len(notifs) > 0:
                    org.ryver.mark_all_notifs_read()

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
                        org.forums + org.teams, pyryver.FIELD_ID, chat_id)
                    if not chat_source:
                        print("Error: Cannot find chat for: " + str(via))
                        org.chat.send_message(
                            "Error: Cannot find source of message. Try `@latexbot updateChats`.", creator)
                        continue
                    # We need to get the actual message from the chat, because the one in the notification may be cut off
                    chat_message = chat_source.get_message_from_id(message_id)[
                        0]
                    text = chat_message.get_body().split(" ")

                    if text[0] == "@latexbot" and len(text) >= 2:
                        print(f"Command received from user {chat_message.get_author_id()}: " + " ".join(text))

                        global enabled
                        if enabled:
                            if text[1] in command_processors:
                                # Check access level
                                if not is_authorized(chat_source, chat_message, command_processors[text[1]][1], admins):
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
                            if not is_authorized(chat_source, chat_message, ACCESS_LEVEL_ORG_ADMIN, admins):
                                org.chat.send_message(
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
            org.chat.send_message(
                "An unexpected error has occurred:\n```\n" + msg + "\n```", creator)
            org.chat.send_message(
                "@tylertian Let's hope that never happens again.", creator)

    org.chat.send_message("LaTeX Bot has been killed. Goodbye!", creator)


if __name__ == "__main__":
    print(f"LaTeX Bot {VERSION} has been started. Initializing...")
    init()
    print("LaTeX Bot is running!")
    org.chat.send_message(
        f"LaTeX Bot {VERSION} is online! Note that to reduce load, I only check messages once per 3 seconds or more!", creator)
    org.chat.send_message(help_text, creator)
    start()
