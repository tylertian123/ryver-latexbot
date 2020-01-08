import pyryver
from quicklatex_render import ql_render
from random import randrange
import time
import os
import requests

ryver = pyryver.Ryver(
    os.environ["LATEXBOT_ORG"], os.environ["LATEXBOT_USER"], os.environ["LATEXBOT_PASS"])

forums = ryver.get_cached_chats(pyryver.TYPE_FORUM)
teams = ryver.get_cached_chats(pyryver.TYPE_TEAM)
users = ryver.get_cached_chats(pyryver.TYPE_USER)

# Get user avatar URLs
# This information is not included in the regular user info
# It is retrieved from a different URL
resp = requests.post(ryver.url_prefix +
                     "Ryver.Info()?$format=json", headers=ryver.headers)
resp.raise_for_status()
users_json = resp.json()["d"]["users"]
user_avatars = {u["id"]: u["avatarUrl"] for u in users_json}

chat = pyryver.get_obj_by_field(forums, pyryver.FIELD_NAME, "Test")

version = "v0.2.4"

creator = pyryver.Creator(f"LaTeX Bot {version}", "")

# Current admins are: @tylertian, @moeez, @michalkdavis, and @Julia
admins = set([1311906, 1605991, 1108002, 1108009])
enabled = True

help_text = f"""
Basic commands:
  - `@latexbot render <formula>` - Render LaTeX.
  - `@latexbot help` - Print a help message.
  - `@latexbot ping` - I will respond with "Pong" if I'm here.
  - `@latexbot updateChats` - Update the list of forums/teams and users.
  - `@latexbot whatDoYouThink <thing>` - Ask my opinion of a thing!

Commands only accessible by Bot Admins:
  - `@latexbot moveTo [(name|nickname)=]<forum|team>` - Move me to another forum/team.
  - `@latexbot deleteMessages <count>` - Delete the last <count> messages.
  - `@latexbot moveMessages <count> [(name|nickname)=]<forum|team>` - Move the last <count> messages to another forum/team.
  - `@latexbot disable` - Disable me.
  - `@latexbot enable` - Enable me.
  - `@latexbot kill` - Kill me (:fearful:).
  - `@latexbot sleep <seconds>` - Put me to sleep for a certain amount of time.

Current Bot Admins are: {admins}.

Note: Starting from LaTeX Bot v0.2.0, I will respond no matter which forum/team the message was sent in.
However, the `moveToForum`/`moveToTeam` commands can still be used to specify where I should send other messages, and `updateChats` needs to be run for me to discover new chat rooms.
"""

print("LaTeX Bot is running!")
chat.send_message(f"""
LaTeX Bot {version} is online! Note that to reduce load, I only check messages once per 3 seconds or more!
""" + help_text, creator)


def check_admin(msg: pyryver.ChatMessage) -> bool:
    return msg.get_raw_data()["from"]["id"] in admins


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


def _render(chat: pyryver.Chat, msg: pyryver.ChatMessage, formula: str):
    if len(formula) > 0:
        img = ql_render(formula)
        chat.send_message(f"![{formula}]({img})", creator)
    else:
        chat.send_message("Formula can't be empty.", creator)


def _moveto(_chat: pyryver.Chat, msg: pyryver.ChatMessage, name: str):
    global chat
    if not check_admin(msg):
        _chat.send_message(
            "I'm sorry Dave, I'm afraid I can't do that.", creator)
        return
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


def _help(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    chat.send_message(help_text, creator)


def _ping(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    chat.send_message("Pong", creator)


def _updatechats(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    global forums, teams
    forums = ryver.get_cached_chats(pyryver.TYPE_FORUM, force_update=True)
    teams = ryver.get_cached_chats(pyryver.TYPE_TEAM, force_update=True)
    users = ryver.get_cached_chats(pyryver.TYPE_USER, force_update=True)
    chat.send_message("Forums/Teams updated.", creator)


def _deletemessages(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    if not check_admin(msg):
        chat.send_message(
            "I'm sorry Dave, I'm afraid I can't do that.", creator)
        return

    count = 0
    try:
        count = int(s)
    except ValueError:
        chat.send_message("Invalid number.", creator)
        return
    msgs = chat.get_messages(count)
    for message in msgs:
        message.delete()


def _disable(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    if not check_admin(msg):
        chat.send_message(
            "I'm sorry Dave, I'm afraid I can't do that.", creator)
        return
    global enabled
    enabled = False
    chat.send_message("LaTeX Bot disabled.", creator)


def _kill(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    if not check_admin(msg):
        chat.send_message(
            "I'm sorry Dave, I'm afraid I can't do that.", creator)
        return
    chat.send_message("Goodbye, world.", creator)
    raise Exception("I have been killed :(")


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
    ":thumbsdown",
    "I hate it.",
    "Please no.",
    "It's bad.",
    "It's stupid.",
]


def _whatdoyouthink(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    msgs = yes_msgs if randrange(2) == 0 else no_msgs
    chat.send_message(msgs[randrange(len(msgs))], creator)


def _sleep(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    secs = 0
    try:
        secs = float(s)
    except ValueError:
        chat.send_message("Invalid number.", creator)
        return
    chat.send_message("Good night! :sleeping:", creator)
    time.sleep(secs)
    chat.send_message("Good morning!", creator)


def _movemessages(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    if not check_admin(msg):
        chat.send_message(
            "I'm sorry Dave, I'm afraid I can't do that.", creator)
        return

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

    msgs = chat.get_messages(count)
    for msg in msgs[::-1]:
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
                msg_author.get_display_name(), user_avatars[msg_author.get_id()])
        
        msg_body = msg.get_body()
        # Handle reactions
        # Because reactions are from multiple people they can't really be moved the same way
        if msg.get_reactions():
            msg_body += "\n"
            for emoji, people in msg.get_reactions().items():
                # Instead for each reaction, append a line at the bottom with the emoji
                # and every user's display name who reacted with the reaction
                u = [pyryver.get_obj_by_field(users, pyryver.FIELD_ID, person) for person in people]
                msg_body += f"\n:{emoji}:: {', '.join([user.get_display_name() if user else 'unknown' for user in u])}"

        msg_id = to.send_message(msg_body, msg_creator)
        msg.delete()


command_processors = {
    "render": _render,
    "moveTo": _moveto,
    "help": _help,
    "ping": _ping,
    "updateChats": _updatechats,
    "deleteMessages": _deletemessages,
    "disable": _disable,
    "kill": _kill,
    "whatDoYouThink": _whatdoyouthink,
    "sleep": _sleep,
    "moveMessages": _movemessages,
}

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
            chat_message = chat_source.get_message_from_id(message_id)[0]
            text = chat_message.get_body().split(" ")

            if text[0] == "@latexbot" and len(text) >= 2:
                print("Command received: " + " ".join(text))

                if enabled:
                    if text[1] in command_processors:
                        command_processors[text[1]](
                            chat_source, chat_message, " ".join(text[2:]))
                    else:
                        chat_source.send_message(
                            "Sorry, I didn't understand what you were asking me to do.", creator)
                    print("Command processed.")
                elif text[1] == "enable":
                    enabled = True
                    chat_source.send_message("I'm alive!", creator)
                    print("Command processed.")

        time.sleep(3)
except KeyboardInterrupt:
    pass
except Exception as e:
    chat.send_message("An unexpected error has occurred:\n" + str(e), creator)
    chat.send_message("LaTeX Bot has been killed. Goodbye!", creator)
    raise

chat.send_message("LaTeX Bot has been killed. Goodbye!", creator)
