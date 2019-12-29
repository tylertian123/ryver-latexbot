import pyryver
from quicklatex_render import ql_render
import time
import os

ryver = pyryver.Ryver(
    os.environ["LATEXBOT_ORG"], os.environ["LATEXBOT_USER"], os.environ["LATEXBOT_PASS"])

forums = ryver.get_cached_chats(pyryver.TYPE_FORUM)
teams = ryver.get_cached_chats(pyryver.TYPE_TEAM)

chat = pyryver.get_obj_by_field(forums, pyryver.FIELD_NAME, "Test")

creator = None

# Current admins are: @tylertian, @moeez, @michalkdavis, and @Julia
admins = set([1311906, 1605991, 1108002, 1108009])

help_text = """
Command set:
  - `@latexbot render <formula>` - Renders LaTeX.
  - `@latexbot help` - Print a help message.
  - `@latexbot ping` - I will respond with "Pong" if I'm here.
  - `@latexbot moveToForum [(name|nickname)=]<forum>` - Move me to another forum.
  - `@latexbot moveToTeam [(name|nickname)=]<team>` - Move me to another team.
  - `@latexbot updateChats` - Updates the list of forums/teams. Only Bot Admins can do this.
  - `@latexbot deleteMessages <count>` - Deletes the last <count> messages. Only Bot Admins can do this.

Note: Starting from LaTeX Bot v0.2.0, I will respond no matter which forum/team the message was sent in.
However, the `moveToForum`/`moveToTeam` commands can still be used to specify where I should send other messages, and `updateChats` needs to be run for me to discover new chat rooms.
"""

print("LaTeX Bot is running!")
chat.send_message("""
LaTeX Bot v0.2.0-alpha is online! Note that to reduce load, I only check messages once per 3 seconds or more!
""" + help_text, creator)


def _render(chat: pyryver.Chat, msg: pyryver.ChatMessage, formula: str):
    global creator
    if len(formula) > 0:
        img = ql_render(formula)
        chat.send_message(f"![{formula}]({img})", creator)
    else:
        chat.send_message("Formula can't be empty.", creator)


def _movetoforum(_chat: pyryver.Chat, msg: pyryver.ChatMessage, name: str):
    global chat, creator, forums
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
    global chat, creator, teams
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
    global creator
    chat.send_message(help_text, creator)


def _ping(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    global creator
    chat.send_message("Pong", creator)


def _updatechats(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    global creator, forums, teams
    if msg.get_raw_data()["from"]["id"] not in admins:
        chat.send_message(
            "I'm sorry Dave, I'm afraid I can't do that.", creator)
        return
    forums = ryver.get_cached_chats(pyryver.TYPE_FORUM, force_update=True)
    teams = ryver.get_cached_chats(pyryver.TYPE_TEAM, force_update=True)
    chat.send_message("Forums/Teams updated.", creator)

def _deletemessages(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    global creator
    if msg.get_raw_data()["from"]["id"] not in admins:
        chat.send_message(
            "I'm sorry Dave, I'm afraid I can't do that.", creator)
        return
    
    count = 0
    try:
        count = int(s)
    except ValueError:
        chat.send_message("Invalid number.", creator)
    msgs = chat.get_messages(count)
    for message in msgs:
        message.delete()

command_processors = {
    "render": _render,
    "moveToForum": _movetoforum,
    "moveToTeam": _movetoteam,
    "help": _help,
    "ping": _ping,
    "updateChats": _updatechats,
    "deleteMessages": _deletemessages,
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
            # We need to get the actual message from the chat, because the one in the notification may be cut off
            chat_message = chat_source.get_message_from_id(message_id)[0]
            text = chat_message.get_body().split(" ")

            if text[0] == "@latexbot" and len(text) >= 2:
                print("Command received: " + " ".join(text))

                if text[1] in command_processors:
                    command_processors[text[1]](chat_source, chat_message, " ".join(text[2:]))
                else:
                    chat_source.send_message(
                        "Sorry, I didn't understand what you were asking me to do.", creator)
                print("Command processed.")

        time.sleep(3)
except KeyboardInterrupt:
    pass
except Exception as e:
    chat.send_message("An unexpected error has occurred:\n" + str(e), creator)

chat.send_message("LaTeX Bot has been killed. Goodbye!", creator)
