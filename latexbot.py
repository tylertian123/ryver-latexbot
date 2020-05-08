import asyncio
import org
import aiohttp # DON'T MOVE THIS!
import os
import pyryver
import quicklatex_render
import typing
import xkcd
from latexbot_util import *

# Make print() flush immediately
# Otherwise the logs won't show up in real time in Docker
old_print = print


def print(*args, **kwargs):
    kwargs["flush"] = True
    # Add timestamp
    old_print(current_time().strftime("%Y-%m-%d %H:%M:%S"), *args, **kwargs)


################################ GLOBAL VARIABLES AND CONSTANTS ################################

VERSION = "v0.5.0-dev-ASYNC"

creator = pyryver.Creator(f"LaTeX Bot {VERSION}", "")

enabled = True

# Auto generated later
help_text = ""
extended_help_text = {}


################################ UTILITY FUNCTIONS ################################


def generate_help_text(ryver: pyryver.Ryver):
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
    admins = ", ".join([ryver.get_user(id=id).get_name() for id in org.admins])
    if admins:
        help_text += f"\nCurrent Bot Admins are: {admins}."
    else:
        help_text += "\nNo Bot Admins are in the configuration."
    help_text += "\n\nFor more details about a command, try `@latexbot help <command>`."


################################ COMMAND PROCESSORS ################################


async def _render(chat: pyryver.Chat, msg_id: str, formula: str):
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
        img = quicklatex_render.ql_render(formula)
        await chat.send_message(f"Formula: `{formula}`\n![{formula}]({img})", creator)
    else:
        await chat.send_message("Formula can't be empty.", creator)


async def _help(chat: pyryver.Chat, msg_id: str, s: str):
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
        await chat.send_message(help_text, creator)
    else:
        default = f"Error: {s} is not a valid command, or does not have an extended description."
        await chat.send_message(extended_help_text.get(s, default), creator)


async def _ping(chat: pyryver.Chat, msg_id: str, s: str):
    """
    I will respond with 'Pong' if I'm here.
    ---
    group: General Commands
    syntax:
    """
    await chat.send_message("Pong", creator)


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


async def _whatdoyouthink(chat: pyryver.Chat, msg_id: str, s: str):
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
    await chat.send_message(msgs[randrange(len(msgs))], creator)


async def _xkcd(chat: pyryver.Chat, msg_id: str, s: str):
    """
    Get the latest xkcd or a specific xkcd by number.
    ---
    group: General Commands
    syntax: [number]
    ---
    > `@latexbot xkcd` - Get the latest xkcd.
    > `@latexbot xkcd 149` - Get xkcd #149.
    """
    xkcd_creator = pyryver.Creator(creator.name, XKCD_PROFILE)
    if s:
        try:
            number = int(s)
        except ValueError:
            await chat.send_message(f"Invalid number.", xkcd_creator)
            return
    else:
        number = None
    
    try:
        comic = await xkcd.get_comic(number)
        if not comic:
            await chat.send_message(f"Error: This comic does not exist (404). Have this image of a turtle instead.\n\n![A turtle](https://cdn.britannica.com/66/195966-138-F9E7A828/facts-turtles.jpg)", xkcd_creator)
            return
        
        await chat.send_message(xkcd.comic_to_str(comic), xkcd_creator)
    except aiohttp.ClientResponseError as e:
        await chat.send_message(f"An error occurred: {e}", xkcd_creator)


async def _deletemessages(chat: pyryver.Chat, msg_id: str, s: str):
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
        await chat.send_message("Invalid syntax.", creator)
        return

    # Special case for start = 1
    if start == 1:
        msgs = await get_msgs_before(chat, msg_id, end)
    else:
        # Cut off the end (newer messages)
        # Subtract 1 for 1-based indexing
        msgs = (await get_msgs_before(chat, msg_id, end))[:-(start - 1)]
    for message in msgs:
        await message.delete()
    await (await chat.get_message_from_id(msg_id))[0].delete()


async def _movemessages(chat: pyryver.Chat, msg_id: str, s: str):
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
        await chat.send_message("Invalid syntax.", creator)
        return

    to = parse_chat_name(chat.get_ryver(), " ".join(s[1:]))
    if not to:
        await chat.send_message("Forum/team not found", creator)
        return

    # Special case for start = 1
    if start == 1:
        msgs = await get_msgs_before(chat, msg_id, end)
    else:
        # Cut off the end (newer messages)
        # Subtract 1 for 1-based indexing
        msgs = (await get_msgs_before(chat, msg_id, end))[:-(start - 1)]

    await to.send_message(f"# Begin Moved Message\n\n---", creator)

    for msg in msgs:
        # Get the creator
        msg_creator = msg.get_creator()
        # If no creator then get author
        if not msg_creator:
            # First attempt to search for the ID in the list
            # if that fails then get it directly using a request
            msg_author = chat.get_ryver().get_user(id=msg.get_author_id) or (await msg.get_author())
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
                u = [chat.get_ryver().get_user(id=person.get_id()) for person in people]
                msg_body += f"\n:{emoji}:: {', '.join([user.get_display_name() if user else 'unknown' for user in u])}"

        await to.send_message(msg_body, msg_creator)
        await msg.delete()
    await msgs[-1].delete()

    await to.send_message("---\n\n# End Moved Message", creator)


async def _countmessagessince(chat: pyryver.Chat, msg_id: str, s: str):
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
            await chat.send_message("Invalid regex: " + str(e), creator)
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
        msgs = (await get_msgs_before(chat, msg_id, 50))[::-1]
        for message in msgs:
            count += 1
            if match(message.get_body()):
                # Found a match
                resp = f"There are a total of {count} messages, including your command but not this message."
                resp += f"\n\nMessage matched (sent by {(await message.get_author()).get_display_name()}):\n{sanitize(message.get_body())}"
                await chat.send_message(resp, creator)
                return
        # No match - change anchor
        msg_id = msgs[-1].get_id()
    await chat.send_message(
        "Error: Max search depth of 250 messages exceeded without finding a match.", creator)


command_processors = {
    "render": [_render, ACCESS_LEVEL_EVERYONE],
    "help": [_help, ACCESS_LEVEL_EVERYONE],
    "ping": [_ping, ACCESS_LEVEL_EVERYONE],
    "whatDoYouThink": [_whatdoyouthink, ACCESS_LEVEL_EVERYONE],
    "xkcd": [_xkcd, ACCESS_LEVEL_EVERYONE],

    "deleteMessages": [_deletemessages, ACCESS_LEVEL_FORUM_ADMIN],
    "moveMessages": [_movemessages, ACCESS_LEVEL_FORUM_ADMIN],
    "countMessagesSince": [_countmessagessince, ACCESS_LEVEL_FORUM_ADMIN],
}


################################ OTHER FUNCTIONS ################################


async def main():
    print(f"LaTeX Bot {VERSION} has been started. Initializing...")
    # Init Ryver session
    cache = pyryver.FileCacheStorage("data", "latexbot-")
    async with pyryver.Ryver(os.environ["LATEXBOT_ORG"], os.environ["LATEXBOT_USER"], os.environ["LATEXBOT_PASS"], cache) as ryver:
        # Init other stuff
        await ryver.load_missing_chats()
        await org.init(ryver)        
        generate_help_text(ryver)
        # Start live session
        async with ryver.get_live_session() as session:
            @session.on_connection_loss
            async def _on_conn_loss():
                print("Error: Connection lost!")
                session.close()
            
            @session.on_chat
            async def _on_chat(msg: typing.Dict[str, str]):
                text = msg["text"]
                # TODO: Make the prefix optional in DMs
                if text.startswith(org.command_prefix) and len(text) > len(org.command_prefix):
                    # Check the sender
                    from_user = ryver.get_user(jid=msg["from"])
                    # Ignore messages sent by us
                    if from_user.get_username() == os.environ["LATEXBOT_USER"]:
                        return
                    to = ryver.get_chat(jid=msg["to"])
                    print(f"Command received from {from_user.get_name()} to {to.get_name()}: {text}")
                    # Check if this is a DM
                    if isinstance(to, pyryver.User):
                        # For DMs special processing is required
                        # Since we don't want to reply to ourselves, reply to the sender directly instead
                        to = from_user
                    await session.send_typing(to)
                    # TODO: This can be removed after latexbot with pyryver 0.2.0 completely replaces the old latexbot
                    await ryver.mark_all_notifs_read()
                    # Chop off the beginning
                    text = text[len(org.command_prefix):]
                    # Separate command from args
                    if " " in text or "\n" in text:
                        i = min(text.index(" ") if " " in text else float("inf"), text.index("\n") if "\n" in text else float("inf"))
                        command = text[:i]
                        args = text[i + 1:]
                    else:
                        command = text
                        args = ""
                    
                    if command in command_processors:
                        # Check the access level
                        if not await is_authorized(to, from_user, command_processors[command][1]):
                            await to.send_message(get_access_denied_message(), creator)
                            print("Access was denied.")
                        else:
                            await command_processors[command][0](to, msg['key'], args)
                            print("Command processed.")
                    else:
                        print("Invalid command.")
                        await to.send_message(f"Sorry, I didn't understand what you were asking me to do.", creator)

            print("LaTeX Bot is running!")
            await org.home_chat.send_message( 
                f"LaTeX Bot {VERSION} is online! Note that to reduce load, I only check messages once per 3 seconds or more!", creator)
            await org.home_chat.send_message(help_text, creator)

            await session.run_forever()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
