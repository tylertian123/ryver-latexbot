"""
This module contains command definitions for LaTeX Bot.
"""
import aiohttp
import config
import json
import pyryver
import random
import re
import render
import util
import xkcd
from caseinsensitivedict import CaseInsensitiveDict


async def command_render(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Render a LaTeX formula.

    `\\displaystyle` is automatically put before the equation.

    Thank you to Matthew Mirvish for making this work!
    ---
    group: General Commands
    syntax: <formula>
    ---
    > `@latexbot render f(x) = \\sum_{i=0}^{n} \\frac{a_i}{1+x}`
    """
    if len(args) > 0:
        try:
            img_data = await render.render(args, color="gray", transparent=True)
        except ValueError as e:
            await chat.send_message(f"Error while rendering formula:\n```\n{e}\n```")
            return
        file = (await chat.get_ryver().upload_file("formula.png", img_data, "image/png")).get_file()
        await chat.send_message(f"Formula: `{args}`\n![{args}]({file.get_url()})", bot.msg_creator)
    else:
        await chat.send_message("Formula can't be empty.", bot.msg_creator)


async def command_chem(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Render a chemical formula.

    The formula is rendered with the mhchem package with LaTeX.
    ---
    group: General Commands
    syntax: <formula>
    ---
    > `@latexbot chem HCl_{(aq)} + NaOH_{(aq)} -> H2O_{(l)} + NaCl_{(aq)}`
    """
    if len(args) > 0:
        try:
            img_data = await render.render(f"\\ce{{{args}}}", color="gray", transparent=True, extra_packages=["mhchem"])
        except ValueError as e:
            await chat.send_message(f"Error while rendering formula:\n```\n{e}\n```\n\nDid you forget to put spaces on both sides of the reaction arrow?")
            return
        file = (await chat.get_ryver().upload_file("formula.png", img_data, "image/png")).get_file()
        await chat.send_message(f"Formula: `{args}`\n![{args}]({file.get_url()})", bot.msg_creator)
    else:
        await chat.send_message("Formula can't be empty.", bot.msg_creator)


async def command_help(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
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
    args = args.strip()
    if args == "":
        await chat.send_message(bot.help, bot.msg_creator)
    else:
        default = f"Error: {args} is not a valid command, or does not have an extended description."
        if args in bot.command_help:
            text = bot.command_help[args]
            if await bot.commands.commands[args].is_authorized(bot, chat, user):
                text += "\n\n:white_check_mark: **You have access to this command.**"
            else:
                text += "\n\n:no_entry: **You do not have access to this command.**"
            await chat.send_message(text, bot.msg_creator)
        else:
            await chat.send_message(default, bot.msg_creator)


async def command_ping(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    I will respond with 'Pong' if I'm here.
    ---
    group: General Commands
    syntax:
    """
    await chat.send_message("Pong", bot.msg_creator)


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


async def command_whatDoYouThink(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Ask my opinion of a thing!

    Disclaimer: These are my own opinions, Tyler is not responsible for anything said.
    ---
    group: General Commands
    syntax: <thing>
    ---
    > `@latexbot whatDoYouThink <insert controversial topic here>`
    """
    args = args.lower()
    # Match configured opinions
    for opinion in config.opinions:
        if args in opinion["thing"]:
            # Match user if required
            if "user" in opinion:
                if user.get_username() in opinion["user"]:
                    await chat.send_message(opinion["opinion"][random.randrange(len(opinion["opinion"]))], bot.msg_creator)
                    return
            else:
                await chat.send_message(opinion["opinion"][random.randrange(len(opinion["opinion"]))], bot.msg_creator)
                return
    msgs = no_msgs if hash(args) % 2 == 0 else yes_msgs
    await chat.send_message(msgs[random.randrange(len(msgs))], bot.msg_creator)


async def command_xkcd(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Get the latest xkcd or a specific xkcd by number.
    ---
    group: General Commands
    syntax: [number]
    ---
    > `@latexbot xkcd` - Get the latest xkcd.
    > `@latexbot xkcd 149` - Get xkcd #149.
    """
    xkcd_creator = pyryver.Creator(bot.msg_creator.name, util.XKCD_PROFILE)
    if args:
        try:
            number = int(args)
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


async def command_checkiday(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Get a list of today's holidays or holidays for any date.

    This command uses the https://www.checkiday.com/ API.

    The date is optional; if specified, it must be in the YYYY/MM/DD format.
    ---
    group: General Commands
    syntax: [date]
    ---
    > `@latexbot checkiday` - Get today's holidays.
    > `@latexbot checkiday 2020/05/12` - Get the holidays on May 12, 2020.
    """
    url = f"https://www.checkiday.com/api/3/?d={args or util.current_time(config.timezone).strftime('%Y/%m/%d')}"
    async with aiohttp.request("GET", url) as resp:
        if resp.status != 200:
            await chat.send_message(f"HTTP error while trying to get holidays: {resp}", bot.msg_creator)
            return
        data = await resp.json()
    if data["error"] != "none":
        await chat.send_message(f"Error: {data['error']}", bot.msg_creator)
        return
    if not data.get("holidays", None):
        await chat.send_message(f"No holidays on {data['date']}.")
        return
    else:
        msg = f"Here is a list of all the holidays on {data['date']}:\n"
        msg += "\n".join(f"* [{holiday['name']}]({holiday['url']})" for holiday in data["holidays"])
        await chat.send_message(msg, bot.msg_creator)


async def command_deleteMessages(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
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
        if "-" in args:
            start = int(args[:args.index("-")].strip())
            args = args[args.index("-") + 1:].strip()
        else:
            start = 1
        end = int(args)
    except (ValueError, IndexError):
        await chat.send_message("Invalid syntax.", bot.msg_creator)
        return

    # Special case for start = 1
    if start == 1:
        msgs = await util.get_msgs_before(chat, msg_id, end)
    else:
        # Cut off the end (newer messages)
        # Subtract 1 for 1-based indexing
        msgs = (await util.get_msgs_before(chat, msg_id, end))[:-(start - 1)]
    for message in msgs:
        await message.delete()
    await (await pyryver.retry_until_available(chat.get_message, msg_id, timeout=5.0)).delete()


async def command_moveMessages(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
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
    args = args.split()
    if len(args) < 2:
        chat.send_message("Invalid syntax.", bot.msg_creator)
        return

    msg_range = args[0]
    try:
        # Try and parse the range
        if "-" in msg_range:
            start = int(msg_range[:msg_range.index("-")].strip())
            msg_range = msg_range[msg_range.index("-") + 1:].strip()
        else:
            start = 1
        end = int(msg_range)
    except (ValueError, IndexError):
        await chat.send_message("Invalid syntax.", bot.msg_creator)
        return

    to = util.parse_chat_name(chat.get_ryver(), " ".join(args[1:]))
    if not to:
        await chat.send_message("Forum/team not found", bot.msg_creator)
        return

    # Special case for start = 1
    if start == 1:
        msgs = await util.get_msgs_before(chat, msg_id, end)
    else:
        # Cut off the end (newer messages)
        # Subtract 1 for 1-based indexing
        msgs = (await util.get_msgs_before(chat, msg_id, end))[:-(start - 1)]

    await to.send_message(f"# Begin Moved Message\n\n---", bot.msg_creator)

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
                msg_author.get_display_name(), bot.user_avatars.get(msg_author.get_id(), ""))

        msg_body = util.sanitize(msg.get_body())
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

    await to.send_message("---\n\n# End Moved Message", bot.msg_creator)


async def command_countMessagesSince(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    r"""
    Count the number of messages since the first message that matches a pattern.

    This command counts messages from the first message that matches <pattern> to the command message (inclusive).
    It can be a very useful tool for deleting or moving long conversations without having to count the messages manually.
    The search pattern is case insensitive.

    If <pattern> is surrounded with slashes `/like so/`, it is treated as a **Python style** regex, with the multiline and ignorecase flags.

    This command will only search through the last 250 messages maximum.
    ---
    group: Administrative Commands
    syntax: <pattern>
    ---
    > `@latexbot countMessagesSince foo bar` - Count the number of messages since someone said "foo bar".
    > `@latexbot countMessagesSince /((?:^|[^a-zA-Z0-9_!@#$%&*])(?:(?:@)(?!\/)))([a-zA-Z0-9_]*)(?:\b(?!@)|$)/` - Count the number of messages since someone last used an @ mention.
    """
    if args.startswith("/") and args.endswith("/"):
        try:
            expr = re.compile(args[1:-1], re.MULTILINE | re.IGNORECASE)
            # Use the regex search function as the match function
            match = expr.search
        except re.error as e:
            await chat.send_message("Invalid regex: " + str(e), bot.msg_creator)
            return
    else:
        args = args.lower()
        # Case insensitive match
        match = lambda x: x.lower().find(args) != -1

    count = 1
    # Max search depth: 250
    while count < 250:
        # Reverse the messages as by default the oldest is the first
        # Search 50 at a time
        msgs = (await util.get_msgs_before(chat, msg_id, 50))[::-1]
        for message in msgs:
            count += 1
            if match(message.get_body()):
                # Found a match
                resp = f"There are a total of {count} messages, including your command but not this message."
                author_name = (await message.get_author()).get_display_name()
                resp += f"\n\nMessage matched (sent by {author_name}):\n{util.sanitize(message.get_body())}"
                await chat.send_message(resp, bot.msg_creator)
                return
        # No match - change anchor
        msg_id = msgs[-1].get_id()
    await chat.send_message(
        "Error: Max search depth of 250 messages exceeded without finding a match.", bot.msg_creator)


async def command_roles(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Get information about roles.

    The roles system allow you to mention a group of people at once through 
    Discord-style role mentions like @RoleName. When a mention like this is
    detected, LaTeX Bot will automatically replace it with mentions for the 
    people with that role. Note that role names work like Ryver usernames, ie
    they can only contain alphanumeric characters and underscores, and are
    case-insensitive.

    If a username is supplied, this command gets all roles of the user.
    If a role name is supplied, this command gets all users with that role.
    If no parameters are supplied, this command gets all roles and users
    with roles.
    ---
    group: Roles Commands
    syntax: [user|role]
    """
    if not bot.roles:
        await chat.send_message(f"There are currently no roles.", bot.msg_creator)
    if args == "":
        if bot.roles:
            roles_str = "\n".join(
                f"**{role}**: {', '.join(usernames)}" for role, usernames in bot.roles.items())
            await chat.send_message(f"All roles:\n{roles_str}", bot.msg_creator)
    else:
        # A mention
        if args.startswith("@"):
            args = args[1:]
        # A role
        if args in bot.roles:
            users = "\n".join(bot.roles[args])
            await chat.send_message(f"These users have the role '{args}':\n{users}", bot.msg_creator)
        # Check if it's a username
        elif chat.get_ryver().get_user(username=args):
            roles = "\n".join(role for role, usernames in bot.roles.items() if args in usernames)
            if roles:
                await chat.send_message(
                    f"User '{args}' has the following roles:\n{roles}", bot.msg_creator)
            else:
                await chat.send_message(f"User '{args}' has no roles.", bot.msg_creator)
        else:
            await chat.send_message(f"'{args}' is not a valid username or role name.", bot.msg_creator)


async def command_addToRole(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Add people to a role.

    Note that role names work like Ryver usernames, ie they can only contain 
    alphanumeric characters and underscores, and are case-insensitive.

    Roles are in a comma-separated list, e.g. Foo,Bar,Baz.
    ---
    group: Roles Commands
    syntax: <roles> <people>
    ---
    > `@latexbot addToRole Foo tylertian` - Give Tyler the "Foo" role.
    > `@latexbot addToRole Foo,Bar tylertian latexbot` Give Tyler and LaTeX Bot the "Foo" and "Bar" roles.
    """
    args = args.split()
    if len(args) < 2:
        await chat.send_message("Invalid syntax.", bot.msg_creator)
        return

    roles = [r.strip() for r in args[0].split(",")]
    usernames = [username[1:] if username.startswith(
        "@") else username for username in args[1:]]

    for role in roles:
        if " " in role or "," in role:
            await chat.send_message(
                f"Invalid role: {role}. Role names must not contain spaces or commas. Skipping...", bot.msg_creator)
            continue
        # Role already exists
        if role in bot.roles:
            for username in usernames:
                if username in bot.roles[role]:
                    await chat.send_message(
                        f"Warning: User '{username}' already has role '{role}'.", bot.msg_creator)
                else:
                    bot.roles[role].append(username)
        else:
            bot.roles[role] = usernames
    bot.save_roles()

    await chat.send_message("Operation successful.", bot.msg_creator)


async def command_removeFromRole(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
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
    args = args.split()
    if len(args) < 2:
        await chat.send_message("Invalid syntax.", bot.msg_creator)
        return

    roles = [r.strip() for r in args[0].split(",")]
    usernames = [username[1:] if username.startswith(
        "@") else username for username in args[1:]]

    for role in roles:
        if not role in bot.roles:
            await chat.send_message(
                f"Error: The role {role} does not exist. Skipping...", bot.msg_creator)
            continue
        
        for username in usernames:
            if not username in bot.roles[role]:
                await chat.send_message(
                    f"Warning: User {username} does not have the role {role}.", bot.msg_creator)
                continue
            bot.roles[role].remove(username)

        # Delete empty roles
        if len(bot.roles[role]) == 0:
            bot.roles.pop(role)
    bot.save_roles()

    await chat.send_message("Operation successful.", bot.msg_creator)


async def command_deleteRole(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Completely delete a role, removing all users from that role.

    Roles are in a comma-separated list, e.g. Foo,Bar,Baz.
    ---
    group: Roles Commands
    syntax: <roles>
    ---
    > `@latexbot deleteRole Foo` - Remove everyone from the role Foo and delete it.
    """
    if args == "":
        await chat.send_message("Error: Please specify at least one role!", bot.msg_creator)
        return
    roles = [r.strip() for r in args.split(",")]
    for role in roles:
        try:
            bot.roles.pop(role)
        except KeyError:
            await chat.send_message(f"Error: The role {role} does not exist. Skipping...", bot.msg_creator)
    bot.save_roles()

    await chat.send_message("Operation successful.", bot.msg_creator)


async def command_exportRoles(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Export roles data as a JSON. 

    If the data is less than 1k characters long, it will be sent as a chat message.
    Otherwise it will be sent as a file attachment.
    ---
    group: Roles Commands
    syntax:
    """
    await util.send_json_data(chat, bot.roles.to_dict(), "Roles:", "roles.json", bot.user, bot.msg_creator)


async def command_importRoles(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Import JSON roles data from the message, or from a file attachment.

    If a file is attached to the message, the roles will always be imported from the file.
    ---
    group: Roles Commands
    syntax: <data|fileattachment>
    ---
    > `@latexbot importRoles {}` - Clear all roles.
    """
    try:
        data = util.get_attached_json_data(await pyryver.retry_until_available(chat.get_message, msg_id, timeout=5.0), args)
    except ValueError as e:
        await chat.send_message(str(e), bot.msg_creator)
    msg = await pyryver.retry_until_available(chat.get_message, msg_id, timeout=5.0)
    file = msg.get_attached_file()
    if file:
        # Get the actual contents
        try:
            data = (await file.download_data()).decode("utf-8")
        except aiohttp.ClientResponseError as e:
            await chat.send_message(f"Error while trying to GET file attachment: {e}", bot.msg_creator)
            return
        except UnicodeDecodeError as e:
            await chat.send_message(f"File needs to be encoded with utf-8! The following decode error occurred: {e}", bot.msg_creator)
            return
    else:
        data = args
    
    try:
        bot.roles = CaseInsensitiveDict(json.loads(data))
        bot.save_roles()
        await chat.send_message(
            f"Operation successful. Use `@latexbot roles` to view the updated roles.", bot.msg_creator)
    except json.JSONDecodeError as e:
        await chat.send_message(f"Error decoding JSON: {e}", bot.msg_creator)


import latexbot # nopep8 # pylint: disable=unused-import
