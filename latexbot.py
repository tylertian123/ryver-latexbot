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
import xkcd
from datetime import datetime, timedelta
from dateutil import tz
from gcalendar import Calendar
from latexbot_util import *
from quicklatex_render import ql_render
from random import randrange
from requests import HTTPError
from traceback import format_exc

# Make print() flush immediately
# Otherwise the logs won't show up in real time in Docker
old_print = print


def print(*args, **kwargs):
    kwargs["flush"] = True
    # Add timestamp
    old_print(current_time().strftime("%Y-%m-%d %H:%M:%S"), *args, **kwargs)


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
            examples = "\n".join(
                "* " + ex for ex in properties["examples"]) if properties["examples"] else "***No examples provided.***"

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
    Render a LaTeX formula. Powered by QuickLaTeX.

    The formula is rendered in inline mode.
    Put \\displaystyle before the formula to switch to display mode.

    Thanks to QuickLaTeX (https://quicklatex.com/)!
    ---
    group: General Commands
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
    group: General Commands
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
    group: General Commands
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
    group: General Commands
    syntax: <thing>
    ---
    > `@latexbot whatDoYouThink <insert controversial topic here>`
    """
    msgs = no_msgs if hash(s.strip().lower()) % 2 == 0 else yes_msgs
    chat.send_message(msgs[randrange(len(msgs))], creator)


def _xkcd(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Get the latest xkcd or a specific xkcd by number.
    ---
    group: General Commands
    syntax: [number]
    ---
    > `@latexbot xkcd` - Get the latest xkcd.
    > `@latexbot xkcd 149` - Get xkcd #149.
    """
    if s:
        try:
            number = int(s)
        except ValueError:
            chat.send_message(f"Invalid number.", creator)
            return
    else:
        number = None
    
    try:
        comic = xkcd.get_comic(number)
        if not comic:
            chat.send_message(f"Error: This comic does not exist (404). Have this image of a turtle instead.\n\n![A turtle](https://cdn.britannica.com/66/195966-138-F9E7A828/facts-turtles.jpg)", creator)
            return
        
        resp = f"Comic #{comic['num']} (Posted {comic['year']}-{comic['month'].zfill(2)}-{comic['day'].zfill(2)}):\n\n"
        resp += f"# {comic['title']}\n![{comic['alt']}]({comic['img']})"
        if "extra_parts" in comic:
            resp += "\n\n***Note: This comic contains extra parts that cannot be displayed here. "
            resp += f"Check out the full comic at https://xkcd.com/{comic['num']}.***"
        chat.send_message(resp, creator)
    except HTTPError as e:
        chat.send_message(f"An error occurred: {e}", creator)


def _events(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Display information about ongoing and upcoming events from Google Calendar.

    If the count is not specified, this command will display the next 3 events. 
    This number includes ongoing events.
    ---
    group: Events/Google Calendar Commands
    syntax: [count]
    ---
    > `@latexbot events 5` - Get the next 5 events, including ongoing events.
    """
    try:
        count = int(s) if s else 3
        if count < 1:
            raise ValueError
    except ValueError:
        chat.send_message(f"Error: Invalid number.", creator)
        return
    
    events = org.calendar.get_upcoming_events(org.calendar_id, count)

    now = current_time()
    ongoing = []
    upcoming = []
    
    # Process all the events
    for event in events:
        start = Calendar.parse_time(event["start"])
        end = Calendar.parse_time(event["end"])
        # See if the event has started
        # If the date has no timezone info, make it the organization timezone for comparisons
        if not start.tzinfo:
            start = start.replace(tzinfo=tz.gettz(org.org_tz))
            # No timezone info means this was created as an all-day event
            has_time = False
        else:
            has_time = True
        if now > start:
            ongoing.append((event, start, end, has_time))
        else:
            upcoming.append((event, start, end, has_time))

    if len(ongoing) > 0:
        resp = "Ongoing Events:"
        for evt in ongoing:
            event, start, end, has_time = evt
            # The day number of the event
            day = caldays_diff(now, start) + 1
            # If the event does not have a time, then don't include the time
            start_str = datetime.strftime(start, DATETIME_DISPLAY_FORMAT if has_time else DATE_DISPLAY_FORMAT)
            end_str = datetime.strftime(end, DATETIME_DISPLAY_FORMAT if has_time else DATE_DISPLAY_FORMAT)
            resp += f"\n* Day **{day}** of {event['summary']} (**{start_str}** to **{end_str}**)"
            if "description" in event and event["description"] != "":
                # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
                resp += f"\u200B:\n  * {strip_html(event['description'])}"
        resp += "\n\n"
    else:
        resp = ""
    if len(upcoming) > 0:
        resp += "Upcoming Events:"
        for evt in upcoming:
            event, start, end, has_time = evt
            # days until the event
            day = caldays_diff(start, now)
            # If the event does not have a time, then don't include the time
            start_str = datetime.strftime(start, DATETIME_DISPLAY_FORMAT if has_time else DATE_DISPLAY_FORMAT)
            end_str = datetime.strftime(end, DATETIME_DISPLAY_FORMAT if has_time else DATE_DISPLAY_FORMAT)
            resp += f"\n* **{day}** day(s) until {event['summary']} (**{start_str}** to **{end_str}**)"
            if "description" in event and event["description"] != "":
                # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
                resp += f"\u200B:\n  * {strip_html(event['description'])}"
    else:
        resp += "***No upcoming events at the moment.***"

    chat.send_message(resp, creator)


def _quickaddevent(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Add an event to Google Calendar based on a simple text string.

    Powered by Google Magic. Don't ask me how it works.

    For more details, see [the Google Calendar API Documentation for quickAdd](https://developers.google.com/calendar/v3/reference/events/quickAdd).
    ---
    group: Events/Google Calendar Commands
    syntax: <event>
    ---
    > `@latexbot quickAddEvent Appointment at Somewhere on June 3rd 10am-10:25am`
    """
    event = org.calendar.quick_add(org.calendar_id, s)
    start = Calendar.parse_time(event["start"])
    end = Calendar.parse_time(event["end"])
    # Correctly format based on whether the event is an all-day event
    # All day events don't come with timezone info
    start_str = datetime.strftime(start, DATETIME_DISPLAY_FORMAT if start.tzinfo else DATE_DISPLAY_FORMAT)
    end_str = datetime.strftime(end, DATETIME_DISPLAY_FORMAT if end.tzinfo else DATE_DISPLAY_FORMAT)
    chat.send_message(f"Created event {event['summary']} (**{start_str}** to **{end_str}**).\nLink: {event['htmlLink']}", creator)


def _addevent(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Add an event to Google Calendar.

    If the event name or start/end time/date contains spaces, surround it with quotes (").

    The description is optional but must be on a new line separate from the rest of the command.
    To type a newline in the chat box, use Shift+Enter.

    The time is optional; if not specified, the event will be created as an all-day event.

    The date must be in one of the formats shown below:
    - YYYY-MM-DD, e.g. 2020-01-01
    - YYYY/MM/DD, e.g. 2020/01/01
    - MMM DD YYYY, e.g. Jan 01 2020
    - MMM DD, YYYY, e.g. Jan 01, 2020

    The time must be in one of the formats shown below:
    - HH:MM, e.g. 00:00
    - HH:MM (AM/PM), e.g. 12:00 AM
    - HH:MM(AM/PM), e.g. 12:00AM
    ---
    group: Events/Google Calendar Commands
    syntax: <name> <startdate> [starttime] <enddate> [endtime] [description on a new line]
    ---
    > `@latexbot addEvent "Foo Bar" 2020-01-01 2020-01-02` - Add an event named "Foo Bar", starting on 2020-01-01 and ending the next day.
    > `@latexbot addEvent "Foo Bar" "Jan 1, 2020" "Jan 2, 2020"` - An alternative syntax for creating the same event.
    > `@latexbot addEvent Foo 2020-01-01 00:00 2020-01-01 12:00` - Add an event named "Foo", starting midnight on 2020-01-01 and ending 12 PM on the same day.
    """
    # If a description is included
    if "\n" in s:
        i = s.index("\n")
        desc = s[i + 1:]
        s = s[:i]
    else:
        desc = None
    try:
        s = shlex.split(s)
    except ValueError as e:
        chat.send_message(f"Invalid syntax: {e}", creator)
        return  
    if len(s) != 3 and len(s) != 5:
        chat.send_message("Error: Invalid syntax. Check `@latexbot help addEvent` for help. You may have to use quotes if any of the parameters contain spaces.", creator)
        return
    
    # No times specified
    if len(s) == 3:
        start = tryparse_datetime(s[1], ALL_DATE_FORMATS)
        if not start:
            chat.send_message(f"Error: The date {s[1]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", creator)
            return
        end = tryparse_datetime(s[2], ALL_DATE_FORMATS)
        if not end:
            chat.send_message(f"Error: The date {s[2]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", creator)
            return
        event_body = {
            "start": {
                "date": datetime.strftime(start, CALENDAR_DATE_FORMAT),
            },
            "end": {
                "date": datetime.strftime(end, CALENDAR_DATE_FORMAT),
            }
        }
    else:
        start_date = tryparse_datetime(s[1], ALL_DATE_FORMATS)
        if not start_date:
            chat.send_message(f"Error: The date {s[1]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", creator)
            return
        start_time = tryparse_datetime(s[2], ALL_TIME_FORMATS)
        if not start_time:
            chat.send_message(f"Error: The time {s[2]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", creator)
            return

        end_date = tryparse_datetime(s[3], ALL_DATE_FORMATS)
        if not end_date:
            chat.send_message(f"Error: The date {s[3]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", creator)
            return
        end_time = tryparse_datetime(s[4], ALL_TIME_FORMATS)
        if not end_time:
            chat.send_message(f"Error: The time {s[4]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", creator)
            return
        
        # Merge to get datetimes
        start = datetime.combine(start_date, start_time.time())
        end = datetime.combine(end_date, end_time.time())
        event_body = {
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": org.org_tz,
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": org.org_tz,
            }
        }
    event_body["summary"] = s[0]
    if desc:
        event_body["description"] = desc
    event = org.calendar.add_event(org.calendar_id, event_body)
    start_str = datetime.strftime(start, DATETIME_DISPLAY_FORMAT if len(s) == 5 else DATE_DISPLAY_FORMAT)
    end_str = datetime.strftime(end, DATETIME_DISPLAY_FORMAT if len(s) == 5 else DATE_DISPLAY_FORMAT)
    if not desc:
        chat.send_message(f"Created event {event['summary']} (**{start_str}** to **{end_str}**).\nLink: {event['htmlLink']}", creator)
    else:
        # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
        chat.send_message(f"Created event {event['summary']} (**{start_str}** to **{end_str}**)\u200B:\n{strip_html(event['description'])}\n\nLink: {event['htmlLink']}", creator)


def _deleteevent(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Delete an event by name from Google Calendar.

    Note that the event name only has to be a partial match, and is case-insensitive.
    Therefore, try to be as specific as possible to avoid accidentally deleting the wrong event.

    This command can only remove events that have not ended.

    Unlike addEvent, this command only takes a single argument, so quotes should not be used.
    ---
    group: Events/Google Calendar Commands
    syntax: <name>
    ---
    > `@latexbot deleteEvent Foo Bar` - Remove the event "Foo Bar".
    """
    s = s.lower()
    events = org.calendar.get_upcoming_events(org.calendar_id)
    matched_event = None
    
    for event in events:
        # Found a match
        if s in event["summary"].lower():
            matched_event = event
            break
    
    if matched_event:
        org.calendar.remove_event(org.calendar_id, matched_event["id"])
        # Format the start and end of the event into strings
        start = Calendar.parse_time(matched_event["start"])
        end = Calendar.parse_time(matched_event["end"])
        start_str = datetime.strftime(start, DATETIME_DISPLAY_FORMAT if start.tzinfo else DATE_DISPLAY_FORMAT)
        end_str = datetime.strftime(end, DATETIME_DISPLAY_FORMAT if end.tzinfo else DATE_DISPLAY_FORMAT)
        chat.send_message(f"Deleted event {matched_event['summary']} (**{start_str}** to **{end_str}**).", creator)
    else:
        chat.send_message(f"Error: No event matches that name.", creator)


def _setreminderstime(chat: pyryver.Chat, msg: pyryver.ChatMessage, s: str):
    """
    Set the time event reminder messages are sent each day or turn them on/off.

    The time must be in the "HH:MM" format (24-hour clock).
    Use the argument "off" to turn reminders off.
    ---
    group: Events/Google Calendar Commands
    syntax: <time|off>
    ---
    > `@latexbot setRemindersTime 00:00` - Set event reminder messages to be sent at 12am each day.
    > `@latexbot setRemindersTime off` - Turn off reminders.
    """
    if s.lower() == "off":
        org.event_reminder_time = None
    else:
        # Try parse to ensure validity
        try:
            datetime.strptime(s, "%H:%M")
        except ValueError:
            chat.send_message("Invalid time format.", creator)
            return
        org.event_reminder_time = s
    # Cancel existing and reschedule
    if org.reminder_event:
        org.scheduler.cancel(org.reminder_event)
    schedule_next_reminder()
    org.save_config()
    if org.event_reminder_time:
        chat.send_message(f"Reminders will now be sent at {s} daily.", creator)
    else:
        chat.send_message(f"Reminders have been disabled.", creator)


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

    # Special case for start = 1
    if start == 1:
        msgs = get_msgs_before(chat, msg.get_id(), end)
    else:
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

    # Special case for start = 1
    if start == 1:
        msgs = get_msgs_before(chat, msg.get_id(), end)
    else:
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

    roles = "\n".join(
        role for role, usernames in org.roles.items() if s in usernames)

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
        roles_str = "\n".join(
            f"**{role}**: {', '.join(usernames)}" for role, usernames in org.roles.items())
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
            chat.send_message(
                f"Error: The role {role} does not exist.", creator)
            return
        # Add all users to set
        usernames.update(org.roles[role])

    author = msg.get_author()
    # Pretend to be the creator
    msg_creator = pyryver.Creator(
        author.get_display_name(), org.user_avatars.get(author.get_id(), ""))
    chat.send_message(
        f"{' '.join('@' + username for username in usernames)}\n{message}", msg_creator)
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
    usernames = [username[1:] if username.startswith(
        "@") else username for username in args[1:]]

    for role in roles:
        if " " in role or "," in role:
            chat.send_message(
                f"Invalid role: {role}. Role names must not contain spaces or commas. Skipping...", creator)
            continue
        # Role already exists
        if role in org.roles:
            for username in usernames:
                if username in org.roles[role]:
                    chat.send_message(
                        f"Warning: User '{username}' already has role '{role}'.", creator)
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
    usernames = [username[1:] if username.startswith(
        "@") else username for username in args[1:]]

    for role in roles:
        if not role in org.roles:
            chat.send_message(
                f"Error: The role {role} does not exist. Skipping...", creator)
            continue

        for username in usernames:
            if not username in org.roles[role]:
                chat.send_message(
                    f"Warning: User {username} does not have the role {role}.", creator)
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
    chat.send_message(
        f"```json\n{json.dumps(org.roles, indent=2)}\n```", creator)


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
        chat.send_message(
            f"Operation successful. Use `@latexbot getAllRoles` to view the updated roles.", creator)
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

    The access level is a number. Here are the possible values:
    0 - Everyone
    1 - Forum Admins
    2 - Org Admins
    3 - Bot Admins
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
    chat.send_message(
        f"```json\n{json.dumps(org.make_config(), indent=2)}\n```", creator)


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
    org.init(force_reload=True)
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
            org.home_chat = new_chat
            org.save_config()
            chat.send_message(f"LaTeX Bot has moved to {name}.", creator)
            org.home_chat.send_message("LaTeX Bot has moved here.", creator)


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
    try:
        s = shlex.split(s)
    except ValueError as e:
        chat.send_message(f"Invalid syntax: {e}", creator)
        return
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
    "xkcd": [_xkcd, ACCESS_LEVEL_EVERYONE],

    "events": [_events, ACCESS_LEVEL_EVERYONE],
    "addEvent": [_addevent, ACCESS_LEVEL_ORG_ADMIN],
    "quickAddEvent": [_quickaddevent, ACCESS_LEVEL_ORG_ADMIN],
    "deleteEvent": [_deleteevent, ACCESS_LEVEL_ORG_ADMIN],
    "setRemindersTime": [_setreminderstime, ACCESS_LEVEL_ORG_ADMIN],

    "deleteMessages": [_deletemessages, ACCESS_LEVEL_FORUM_ADMIN],
    "moveMessages": [_movemessages, ACCESS_LEVEL_FORUM_ADMIN],
    "countMessagesSince": [_countmessagessince, ACCESS_LEVEL_FORUM_ADMIN],

    "getUserRoles": [_getuserroles, ACCESS_LEVEL_EVERYONE],
    "getAllRoles": [_getallroles, ACCESS_LEVEL_EVERYONE],
    "@role": [_atrole, ACCESS_LEVEL_EVERYONE],
    "addToRole": [_addtorole, ACCESS_LEVEL_ORG_ADMIN],
    "removeFromRole": [_removefromrole, ACCESS_LEVEL_ORG_ADMIN],
    "exportRoles": [_exportroles, ACCESS_LEVEL_EVERYONE],
    "importRoles": [_importroles, ACCESS_LEVEL_ORG_ADMIN],

    "disable": [_disable, ACCESS_LEVEL_ORG_ADMIN],
    "kill": [_kill, ACCESS_LEVEL_BOT_ADMIN],
    "sleep": [_sleep, ACCESS_LEVEL_BOT_ADMIN],
    "execute": [_execute, ACCESS_LEVEL_BOT_ADMIN],
    "changeAccess": [_changeaccess, ACCESS_LEVEL_BOT_ADMIN],
    "makeAdmin": [_makeadmin, ACCESS_LEVEL_BOT_ADMIN],
    "removeAdmin": [_removeadmin, ACCESS_LEVEL_BOT_ADMIN],
    "exportConfig": [_exportconfig, ACCESS_LEVEL_EVERYONE],
    "importConfig": [_importconfig, ACCESS_LEVEL_BOT_ADMIN],

    "updateChats": [_updatechats, ACCESS_LEVEL_FORUM_ADMIN],
    "moveTo": [_moveto, ACCESS_LEVEL_ORG_ADMIN],

    "setActivated": [_setactivated, ACCESS_LEVEL_TYLER],
    "impersonate": [_impersonate, ACCESS_LEVEL_TYLER],
}


################################ OTHER FUNCTIONS ################################

def remind_events():
    """
    Send event reminder messages for today's events.
    """
    print("Checking today's events...")
    now = current_time()
    events = org.calendar.get_today_events(org.calendar_id, now)
    if not events:
        print("No events today!")
        return
    
    resp = "Reminder: These events are happening today:"
    for event in events:
        start = Calendar.parse_time(event["start"])
        end = Calendar.parse_time(event["end"])

        # The event has a time, and it starts today (not already started)
        if start.tzinfo and start > now:
            resp += f"\n* {event['summary']} today at **{start.strftime(TIME_DISPLAY_FORMAT)}**"
        else:
            # Otherwise format like normal
            start_str = start.strftime(DATETIME_DISPLAY_FORMAT if start.tzinfo else DATE_DISPLAY_FORMAT)
            end_str = end.strftime(DATETIME_DISPLAY_FORMAT if end.tzinfo else DATE_DISPLAY_FORMAT)
            resp += f"\n* {event['summary']} (**{start_str}** to **{end_str}**)"

        # Add description if there is one
        if "description" in event and event["description"] != "":
            # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
            resp += f"\u200B:\n  * {strip_html(event['description'])}"
    org.announcements_chat.send_message(resp, creator)
    print("Events reminder sent!")
    # Clear the scheduler event and schedule the next event
    org.reminder_event = None
    schedule_next_reminder()


def schedule_next_reminder():
    """
    Schedule the next reminder event.
    """
    if not org.event_reminder_time:
        print("Next reminder event not scheduled because time isn't defined.")
        return
    t = datetime.strptime(org.event_reminder_time, "%H:%M")
    now = current_time()
    # Get that time, today
    t = datetime.combine(now, t.time(), tzinfo=tz.gettz(org.org_tz))
    # If already passed, get that time the next day
    if t < now:
        t += timedelta(days=1)
    timestamp = t.astimezone(tz_utc).timestamp()
    org.scheduler.enterabs(timestamp, 1, remind_events)


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
                        org.home_chat.send_message(
                            "Error: Cannot find source of message. Try `@latexbot updateChats`.", creator)
                        continue
                    # We need to get the actual message from the chat, because the one in the notification may be cut off
                    message = chat_source.get_message_from_id(message_id)[0]
                    
                    if message.get_body().startswith("@latexbot ") and len(message.get_body()) > len("@latexbot "):
                        print(f"Command received from user {message.get_author_id()}: {message.get_body()}")
                        # Chop off the beginning
                        text = message.get_body()[len("@latexbot "):]
                        # Separate command from args
                        try:
                            i = text.index(" ")
                            command = text[:i]
                            args = text[i + 1:]
                        except ValueError:
                            command = text
                            args = ""

                        global enabled
                        if enabled:
                            if command in command_processors:
                                # Check access level
                                if not is_authorized(chat_source, message, command_processors[command][1]):
                                    chat_source.send_message(
                                        get_access_denied_message(), creator)
                                    print("Access was denied.")
                                else:
                                    command_processors[command][0](
                                        chat_source, message, args)
                                    print("Command processed.")
                            else:
                                chat_source.send_message(
                                    "Sorry, I didn't understand what you were asking me to do.", creator)
                                print("Command syntax was invalid.")
                        elif command == "enable":
                            if not is_authorized(chat_source, message, ACCESS_LEVEL_ORG_ADMIN):
                                org.home_chat.send_message(
                                    get_access_denied_message(), creator)
                            else:
                                enabled = True
                                chat_source.send_message("I'm alive!", creator)
                                print("Command processed.")
                    else:
                        print("Notification was not a proper command. Skipping...")

                org.scheduler.run(blocking=False)
                time.sleep(1)
        except KeyboardInterrupt:
            break
        except Exception as e:
            msg = format_exc()
            print("Unexpected exception:")
            print(msg)
            # Sleep for 10 seconds to hopefully have the connection fix itself
            time.sleep(10)
            org.home_chat.send_message(
                "An unexpected error has occurred:\n```\n" + msg + "\n```", creator)
            org.home_chat.send_message(
                "@tylertian Let's hope that never happens again.", creator)
        print("Recovered!")

    org.home_chat.send_message("LaTeX Bot has been killed. Goodbye!", creator)


if __name__ == "__main__":
    print(f"LaTeX Bot {VERSION} has been started. Initializing...")
    init()
    print("LaTeX Bot is running!")
    org.home_chat.send_message(
        f"LaTeX Bot {VERSION} is online! Note that to reduce load, I only check messages once per 3 seconds or more!", creator)
    org.home_chat.send_message(help_text, creator)
    start()
