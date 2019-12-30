import pyryver
from quicklatex_render import ql_render
from random import randrange
import time
import os

ryver = pyryver.Ryver(
    os.environ["LATEXBOT_ORG"], os.environ["LATEXBOT_USER"], os.environ["LATEXBOT_PASS"])

forums = ryver.get_cached_chats(pyryver.TYPE_FORUM)
teams = ryver.get_cached_chats(pyryver.TYPE_TEAM)

chat = pyryver.get_obj_by_field(forums, pyryver.FIELD_NAME, "Test")

creator = pyryver.Creator("LaTeX Bot v0.2.2", "")

# Current admins are: @tylertian, @moeez, @michalkdavis, and @Julia
admins = set([1311906, 1605991, 1108002, 1108009])
enabled = True

help_text = f"""
Basic commands:
  - `@latexbot render <formula>` - Render LaTeX.
  - `@latexbot help` - Print a help message.
  - `@latexbot ping` - I will respond with "Pong" if I'm here.
  - `@latexbot updateChats` - Update the list of forums/teams.
  - `@latexbot whatDoYouThink <thing>` - Ask my opinion of a thing!

Commands only accessible by Bot Admins:
  - `@latexbot moveToForum [(name|nickname)=]<forum>` - Move me to another forum.
  - `@latexbot moveToTeam [(name|nickname)=]<team>` - Move me to another team.
  - `@latexbot deleteMessages <count>` - Delete the last <count> messages.
  - `@latexbot disable` - Disable me.
  - `@latexbot enable` - Enable me.
  - `@latexbot kill` - Kill me (:fearful:).
  - `@latexbot sleep <seconds>` - Put me to sleep for a certain amount of time.

Current Bot Admins are: {admins}.

Note: Starting from LaTeX Bot v0.2.0, I will respond no matter which forum/team the message was sent in.
However, the `moveToForum`/`moveToTeam` commands can still be used to specify where I should send other messages, and `updateChats` needs to be run for me to discover new chat rooms.
"""

print("LaTeX Bot is running!")
chat.send_message("""
LaTeX Bot v0.2.2 is online! Note that to reduce load, I only check messages once per 3 seconds or more!
""" + help_text, creator)

def check_admin(msg: pyryver.ChatMessage) -> bool:
    return msg.get_raw_data()["from"]["id"] in admins

def _render(chat: pyryver.Chat, msg: pyryver.ChatMessage, formula: str):
    if len(formula) > 0:
        img = ql_render(formula)
        chat.send_message(f"![{formula}]({img})", creator)
    else:
        chat.send_message("Formula can't be empty.", creator)


def _movetoforum(_chat: pyryver.Chat, msg: pyryver.ChatMessage, name: str):
    global chat
    if not check_admin(msg):
        _chat.send_message(
            "I'm sorry Dave, I'm afraid I can't do that.", creator)
        return
    if len(name) > 0:
        field = pyryver.FIELD_NAME
        # Handle the name= or nickname= syntax
        if name.startswith("name="):
            field = pyryver.FIELD_NAME
            # Slice off the beginning
            name = name[name.index("=") + 1:]
        elif name.startswith("nickname="):
            field = pyryver.FIELD_NICKNAME
            name = name[name.index("=") + 1:]

        # Find new chat
        new_forum = pyryver.get_obj_by_field(forums, field, name)
        if not new_forum:
            # Note the underscore
            _chat.send_message("Forum not found.", creator)
        else:
            _chat.send_message(f"LaTeX Bot has moved to {name}.", creator)
            chat = new_forum
            chat.send_message("LaTeX Bot has moved here.", creator)


def _movetoteam(_chat: pyryver.Chat, msg: pyryver.ChatMessage, name: str):
    global chat
    if not check_admin(msg):
        _chat.send_message(
            "I'm sorry Dave, I'm afraid I can't do that.", creator)
        return
    if len(name) > 0:
        field = pyryver.FIELD_NAME
        # Handle the name= or nickname= syntax
        if name.startswith("name="):
            field = pyryver.FIELD_NAME
            # Slice off the beginning
            name = name[name.index("=") + 1:]
        elif name.startswith("nickname="):
            field = pyryver.FIELD_NICKNAME
            name = name[name.index("=") + 1:]

        new_team = pyryver.get_obj_by_field(teams, field, name)
        if not new_team:
            _chat.send_message("Team not found.", creator)
        else:
            _chat.send_message(f"LaTeX Bot has moved to {name}.", creator)
            chat = new_team
            chat.send_message("LaTeX Bot has moved here.", creator)


def _help(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    chat.send_message(help_text, creator)


def _ping(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    chat.send_message("Pong", creator)


def _updatechats(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    global forums, teams
    forums = ryver.get_cached_chats(pyryver.TYPE_FORUM, force_update=True)
    teams = ryver.get_cached_chats(pyryver.TYPE_TEAM, force_update=True)
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
    

command_processors = {
    "render": _render,
    "moveToForum": _movetoforum,
    "moveToTeam": _movetoteam,
    "help": _help,
    "ping": _ping,
    "updateChats": _updatechats,
    "deleteMessages": _deletemessages,
    "disable": _disable,
    "kill": _kill,
    "whatDoYouThink": _whatdoyouthink,
    "sleep": _sleep,
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
                chat.send_message("Error: Cannot find source of message. Try `@latexbot updateChats`.", creator)
                continue
            # We need to get the actual message from the chat, because the one in the notification may be cut off
            chat_message = chat_source.get_message_from_id(message_id)[0]
            text = chat_message.get_body().split(" ")

            if text[0] == "@latexbot" and len(text) >= 2:
                print("Command received: " + " ".join(text))
                
                if enabled:
                    if text[1] in command_processors:
                        command_processors[text[1]](chat_source, chat_message, " ".join(text[2:]))
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
