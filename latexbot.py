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

VERSION = "v0.4.0-dev"

creator = pyryver.Creator(f"LaTeX Bot {VERSION}", "")

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
        if command[0].__doc__ == "":
            print(f"Warning: Command {name} has no documentation, skipped")
            continue

        try:
            properties = parse_doc(command[0].__doc__)
            if properties.get("hidden", False) == "true":
                # skip hidden commands
                continue
            
            # Generate syntax string
            syntax = f"`@latexbot {name} {properties['syntax']}`" if properties["syntax"] else f"`@latexbot {name}`"
            # Generate short description
            description = f"{syntax} - {properties['short_desc']} {ACCESS_LEVEL_STRS[command[1]]}"

            # Group commands
            group = properties['group']
            if group in commands:
                commands[group].append(description)
            else:
                commands[group] = [description]
            
            extended_description = properties["long_desc"] or "***No extended description provided.***"
            examples = "\n".join("* " + ex for ex in properties["examples"]) if properties["examples"] else "***No examples provided.***"

            description += f"\n\n{extended_description}\n\n**Examples:**\n{examples}"
            extended_help_text[name] = description
        except (ValueError, KeyError) as e:
            print(f"Error while parsing doc for {name}: {e}")

    for group, cmds in commands.items():
        help_text += group + ":\n"
        for description in cmds:
            help_text += f"  - {description}\n"
        help_text += "\n"
    help_text += f"\nCurrent Bot Admins are: {', '.join([pyryver.get_obj_by_field(org.users, pyryver.FIELD_ID, uid).get_display_name() for uid in org.admins])}."
    help_text += "\n\nFor more details about a command, try `@latexbot help <command>`."


################################ COMMAND PROCESSORS ################################


def _render(chat: pyryver.Chat, msg: pyryver.ChatMessage, formula: str):
    """
    Render a LaTeX formula.

    The formula is rendered in inline mode.
    ---
    group: Basic Commands
    syntax: <formula>
    ---
    > `@latexbot render f(x) = \\sum_{i=0}^{n} \\frac{a_i}{1+x}`
    """
    if len(formula) > 0:
        img = ql_render(formula)
        chat.send_message(f"![{formula}]({img})", creator)
    else:
        chat.send_message("Formula can't be empty.", creator)


def _help(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Get a list of all the commands, or details about a command.

    Use this command without any arguments to get an overview of all the commands,
    or give the name of the command you would like to know more about.
    ---
    group: Basic Commands
    syntax: [command]
    ---
    > `@latexbot help` - Get general help
    > `@latexbot help render` - Get help about the "render" command.
    """
    s = s.strip()
    if s == "":
        chat.send_message(help_text, creator)
    else:
        chat.send_message(extended_help_text.get(s, 
            f"Error: {s} is not a valid command, or does not have an extended description."), creator)


def _ping(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    I will respond with 'Pong' if I'm here.
    ---
    group: Basic Commands
    syntax:
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
    Ask my opinion of a thing!

    Disclaimer: These are my own opinions, Tyler is not responsible for anything said.
    ---
    group: Basic Commands
    syntax: <thing>
    ---
    > `@latexbot whatDoYouThink <insert controversial topic here>`
    """
    msgs = no_msgs if hash(s.strip().lower()) % 2 == 0 else yes_msgs
    chat.send_message(msgs[randrange(len(msgs))], creator)


COMPETITIONS = None


def _howmanydaysuntilcomp(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Shows how many days until the next event.
    ---
    group: Basic Commands
    syntax:
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
    """
    Delete messages.

    If no <start> is provided, this command deletes the last <count>/<end> messages.
    If <start> is provided, this command deletes messages from <start> to <end> inclusive, with 1-based indexing.

    The command message itself is always deleted.
    ---
    group: Administrative Commands
    syntax: [<start>-]<end|count>
    ---
    > `@latexbot deleteMessages 10` - Delete the last 10 messages.
    > `@latexbot deleteMessages 10-20` - Delete the 10th last to 20th last messages, inclusive.
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
    """
    Move messages to another forum or team.

    If no <start> is provided, this command moves the last <count>/<end> messages.
    If <start> is provided, this command moves messages from <start> to <end> inclusive, with 1-based indexing.

    By default this command goes by the display name of the forum/team.
    Specify `nickname=` before the forum/team name to use nicknames instead.

    Note that reactions cannot be moved perfectly, and are instead shown with text.
    ---
    group: Administrative Commands
    syntax: [<start>-]<end|count> [(name|nickname)=]<forum|team>
    ---
    > `@latexbot moveMessages 10 Off-Topic` - Move the last 10 messages to Off-Topic.
    > `@latexbot moveMessages 10-20 nickname=OffTopic` - Move the 10th last to 20th last messages (inclusive) to a forum/team with the nickname +OffTopic.
    """
    s = s.split()
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
    """
    Count the number of messages since the first message that matches a pattern.

    This command counts messages from the first message that matches <pattern> to the command message (inclusive).
    It can be a very useful tool for deleting or moving long conversations without having to count the messages manually.
    The search pattern is case insensitive.

    If <pattern> is surrounded with slashes `/like so/`, it is treated as a regex, with the multiline and ignorecase flags.
    
    This command will only search through the last 250 messages maximum.
    ---
    group: Administrative Commands
    syntax: <pattern>
    ---
    > `@latexbot countMessagesSince foo bar` - Count the number of messages since someone said "foo bar".
    > `@latexbot countMessagesSince /(\\s|^)@(\\w+)(?=\\s|$)/` - Count the number of messages since someone last used an @ mention.
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
    List all roles of a user.
    ---
    group: Roles Commands
    syntax: <user>
    ---
    > `@latexbot getUserRoles tylertian` - Gets all the roles of Tyler.
    """
    # Mentions
    if s.startswith("@"):
        s = s[1:]

    roles = "\n".join(role for role, usernames in org.roles.items() if s in usernames)
    
    if roles:
        chat.send_message(
            f"User '{s}' has the following roles:\n{roles}", creator)
    else:
        chat.send_message(f"User '{s}' has no roles.", creator)


def _getallroles(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    List all roles and users with those roles.
    ---
    group: Roles Commands
    syntax:
    """
    if org.roles:
        roles_str = "\n".join(f"**{role}**: {', '.join(usernames)}" for role, usernames in org.roles.items())
        chat.send_message(f"All roles:\n{roles_str}", creator)
    else:
        chat.send_message(f"There are currently no roles.", creator)


def _atrole(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    @ mention all users with any of the specified roles.
    
    Roles are in a comma-separated list, e.g. Foo,Bar,Baz.
    ---
    group: Roles Commands
    syntax: <roles> [message]
    ---
    > `@latexbot @role Foo` - Mention all users with the role "Foo".
    > `@latexbot @role Foo,Bar Hello World` - Mention all users with the role "Foo" or the role "Bar" with the message "Hello World".
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
        mention_roles = [r.strip() for r in role.split(",")]
    
    # Use a set so there's no repeat mentions
    usernames = set()
    for role in mention_roles:
        if not role in org.roles:
            chat.send_message(f"Error: The role {role} does not exist.", creator)
            return
        # Add all users to set
        usernames.update(org.roles[role])

    author = msg.get_author()
    # Pretend to be the creator
    msg_creator = pyryver.Creator(
        author.get_display_name(), org.user_avatars.get(author.get_id(), ""))
    chat.send_message(f"{' '.join('@' + username for username in usernames)}\n{message}", msg_creator)
    # Get rid of the original message
    msg.delete()


def _addtorole(chat: pyryver.Chat, msg: pyryver.Message, s: str):
    """
    Add people to a role.

    Role names cannot contain spaces or commas.
    
    Roles are in a comma-separated list, e.g. Foo,Bar,Baz.
    ---
    group: Roles Commands
    syntax: <roles> <people>
    ---
    > `@latexbot addToRole Foo tylertian` - Give Tyler the "Foo" role.
    > `@latexbot addToRole Foo,Bar tylertian latexbot` Give Tyler and LaTeX Bot the "Foo" and "Bar" roles.
    """
    args = s.split()
    if len(args) < 2:
        chat.send_message("Invalid syntax.", creator)
        return

    roles = [r.strip() for r in args[0].split(",")]
    usernames = [username[1:] if username.startswith("@") else username for username in args[1:]]

    for role in roles:
        if " " in role or "," in role:
            chat.send_message(f"Invalid role: {role}. Role names must not contain spaces or commas. Skipping...", creator)
            continue
        # Role already exists
        if role in org.roles:
            for username in usernames:
                if username in org.roles[role]:
                    chat.send_message(f"Warning: User '{username}' already has role '{role}'.", creator)
                else:
                    org.roles[role].append(username)
        else:
            org.roles[role] = usernames
    org.save_roles()

    chat.send_message("Operation successful.", creator)


def _removefromrole(chat: pyryver.Chat, msg: pyryver.Message, s: str):
    """
    Remove people from a role.

    Roles are in a comma-separated list, e.g. Foo,Bar,Baz.
    ---
    group: Roles Commands
    syntax: <roles> <people>
    ---
    > `@latexbot removeFromRole Foo tylertian` - Remove Tyler from the "Foo" role.
    > `@latexbot removeFromRole Foo,Bar tylertian latexbot` Remove Tyler and LaTeX Bot from the "Foo" and "Bar" roles.
    """
    args = s.split()
    if len(args) < 2:
        chat.send_message("Invalid syntax.", creator)
        return

    roles = [r.strip() for r in args[0].split(",")]
    usernames = [username[1:] if username.startswith("@") else username for username in args[1:]]

    for role in roles:
        if not role in org.roles:
            chat.send_message(f"Error: The role {role} does not exist. Skipping...", creator)
            continue
        
        for username in usernames:
            if not username in org.roles[role]:
                chat.send_message(f"Warning: User {username} does not have the role {role}.", creator)
                continue
            org.roles[role].remove(username)
        
        # Delete empty roles
        if len(org.roles[role]) == 0:
            org.roles.pop(role)
    org.save_roles()

    chat.send_message("Operation successful.", creator)


def _exportroles(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Export roles data as a JSON. 
    ---
    group: Roles Commands
    syntax:
    """
    chat.send_message(f"```json\n{json.dumps(org.roles, indent=2)}\n```", creator)


def _importroles(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Import roles data as a JSON.
    ---
    group: Roles Commands
    syntax: <data>
    ---
    > `@latexbot importRoles {}` - Clear all roles.
    """
    try:
        org.roles = json.loads(s)
        org.save_roles()
        chat.send_message(f"Operation successful. Use `@latexbot getAllRoles` to view the updated roles.", creator)
    except json.JSONDecodeError as e:
        chat.send_message(f"Error decoding JSON: {e}", creator)


def _disable(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Disable me.

    Might be buggy. Why do you want to use this anyways?
    ---
    group: Developer Commands
    syntax:
    """
    global enabled
    enabled = False
    chat.send_message("LaTeX Bot disabled.", creator)


def _kill(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Kill me (:fearful:).

    With the current settings, I will restart a few minutes after being killed.
    Consider using the disable or sleep commands if you intend to disable me.
    ---
    group: Developer Commands
    syntax:
    """
    chat.send_message("Goodbye, world.", creator)
    # Simulate Ctrl+C
    raise KeyboardInterrupt


def _sleep(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Put me to sleep.

    When sleeping, I will not respond to any commands.
    If you accidentally put me to sleep for a long time, contact Tyler to wake me back up.
    ---
    group: Developer Commands
    syntax: <seconds>
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
    Execute arbitrary Python code.

    Before you start messing around, keep in mind I run in a Docker container,
    so everything you do here is sandboxed.

    All output to stdout and stderr will be sent as a message after the code finishes executing.

    Best to stay away from this command unless you're a dev.
    ---
    group: Developer Commands
    syntax: <code>
    ---
    > `@latexbot execute print("Hello World")`
    > `@latexbot execute chat.send_message("Hello from LaTeX Bot")`
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
            f"An exception has occurred:\n```\n{format_exc()}\n```", creator)
    finally:
        sys.stdout = stdout
        sys.stderr = stderr


def _changeaccess(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Change the access level of a command.
    
    The access level is a number. Here are the possible values:\n
    0 - Everyone\n
    1 - Forum Admins\n
    2 - Org Admins\n
    3 - Bot Admins\n
    9001 - Tyler

    Might contain bugs.
    ---
    group: Developer Commands
    syntax: <command> <level>
    ---
    > `@latexbot changeAccess render 1` - Change the access level for "render" to Forum Admins or higher.
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
    Make a user a Bot Admin.
    ---
    group: Developer Commands
    syntax: <user>
    """
    if s.startswith("@"):
        s = s[1:]

    user = pyryver.get_obj_by_field(org.users, pyryver.FIELD_USERNAME, s)
    if not user:
        chat.send_message(f"User not found.", creator)
        return
    org.admins.add(user.get_id())
    generate_help_text()
    org.save_config()
    chat.send_message(f"User {s} has been added to Bot Admins.", creator)


def _removeadmin(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Remove a user from Bot Admins.
    ---
    group: Developer Commands
    syntax: <user>
    """
    if s.startswith("@"):
        s = s[1:]

    user = pyryver.get_obj_by_field(org.users, pyryver.FIELD_USERNAME, s)
    if not user:
        chat.send_message(f"User not found.", creator)
        return
    try:
        org.admins.remove(user.get_id())
        generate_help_text()
        org.save_config()
        chat.send_message(f"User {s} is no longer a Bot Admin.", creator)
    except KeyError:
        chat.send_message(f"User {s} is not a Bot Admin.", creator)


def _exportconfig(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Export config as a JSON.
    ---
    group: Developer Commands
    syntax:
    """
    chat.send_message(f"```json\n{json.dumps(org.make_config(), indent=2)}\n```", creator)


def _importconfig(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Import config from JSON.
    ---
    group: Developer Commands
    syntax: <data>
    """
    try:
        org.init_config(json.loads(s))
        generate_help_text()
        org.save_config()
        chat.send_message(f"Operation successful.", creator)
    except (json.JSONDecodeError, KeyError) as e:
        chat.send_message(f"Error decoding config: {e}", creator)


def _updatechats(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Update the cached list of forums/teams and users.

    As getting organization data takes time, LaTeX Bot caches this information,
    so when org data is updated, such as when a new user joins, or when a new forum is created,
    LaTeX Bot might fail to recognize it. Run this command to fix it.
    ---
    group: Miscellaneous Commands
    syntax:
    """
    org.init()
    chat.send_message("Forums/Teams/Users updated.", creator)


def _moveto(chat: pyryver.Chat, msg: pyryver.ChatMessage, name: str):
    """
    Move my home to another forum/team.

    My home is where I'll send miscellaneous info such as crash backtraces.

    The forum/team specification has the same syntax as moveMessages.
    ---
    group: Miscellaneous Commands
    syntax: [(name|nickname)=]<forum|team>
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
    Activates or deactivates a user.

    Might be buggy.
    ---
    group: Hidden Commands
    syntax: <user>
    hidden: true
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
    Impersonates someone.
    ---
    group: Hidden Commands
    syntax: <displayname> <avatarURL>
    hidden: true
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
    "exportRoles": [_exportroles, ACCESS_LEVEL_ORG_ADMIN],
    "importRoles": [_importroles, ACCESS_LEVEL_ORG_ADMIN],

    "disable": [_disable, ACCESS_LEVEL_ORG_ADMIN],
    "kill": [_kill, ACCESS_LEVEL_BOT_ADMIN],
    "sleep": [_sleep, ACCESS_LEVEL_BOT_ADMIN],
    "execute": [_execute, ACCESS_LEVEL_BOT_ADMIN],
    "changeAccess": [_changeaccess, ACCESS_LEVEL_BOT_ADMIN],
    "makeAdmin": [_makeadmin, ACCESS_LEVEL_BOT_ADMIN],
    "removeAdmin": [_removeadmin, ACCESS_LEVEL_BOT_ADMIN],
    "exportConfig": [_exportconfig, ACCESS_LEVEL_BOT_ADMIN],
    "importConfig": [_importconfig, ACCESS_LEVEL_BOT_ADMIN],

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
                    text = chat_message.get_body().split()

                    if text[0] == "@latexbot" and len(text) >= 2:
                        print(f"Command received from user {chat_message.get_author_id()}: " + " ".join(text))

                        global enabled
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
        print("Recovered!")

    org.chat.send_message("LaTeX Bot has been killed. Goodbye!", creator)


if __name__ == "__main__":
    print(f"LaTeX Bot {VERSION} has been started. Initializing...")
    init()
    print("LaTeX Bot is running!")
    org.chat.send_message(
        f"LaTeX Bot {VERSION} is online! Note that to reduce load, I only check messages once per 3 seconds or more!", creator)
    org.chat.send_message(help_text, creator)
    start()
