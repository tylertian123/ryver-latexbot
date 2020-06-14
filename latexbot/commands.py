"""
This module contains command definitions for LaTeX Bot.
"""
import aiohttp
import config
import pyryver
import random
import render
import util
import xkcd


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
        file = (await chat.get_ryver().upload_file("equation.png", img_data, "image/png")).get_file()
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


import latexbot # nopep8 # pylint: disable=unused-import
