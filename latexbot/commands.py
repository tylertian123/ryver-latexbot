"""
This module contains command definitions for LaTeX Bot.
"""
import aiohttp
import config
import io
import json
import pyryver
import random
import re
import render
import shlex
import sys
import time
import trivia
import typing
import util
import xkcd
from caseinsensitivedict import CaseInsensitiveDict
from datetime import datetime
from dateutil import tz
from gcalendar import Calendar
from markdownify import markdownify
from traceback import format_exc


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


YES_MSGS = [
    "Yes.",
    "I like it!",
    "Brilliant!",
    "Genius!",
    "Do it!",
    "It's good.",
    ":thumbsup:",
]
NO_MSGS = [
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
    msgs = NO_MSGS if hash(args) % 2 == 0 else YES_MSGS
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
    url = f"https://www.checkiday.com/api/3/?d={args or util.current_time().strftime('%Y/%m/%d')}"
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


async def command_trivia(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Play a game of trivia. See extended description for details. 
    
    Powered by [Open Trivia Database](https://opentdb.com/).
    
    The trivia command has several sub-commands. Here are each one of them:
    - `categories` - Get all the categories and their IDs, which are used later to start a game.
    - `start [category] [difficulty] [type]` - Start a game with an optional category, difficulty and type. The category can be an ID, a name from the `categories` command, 'all' (all regular questions, no custom), or 'custom' (all custom questions, no regular). If the name contains a space, it must be surrounded with quotes. The difficulty can be "easy", "medium" or "hard". The type can be either "true/false" or "multiple-choice". You can also specify "all" for any of the categories.
    - `question`, `next` - Get the next question or repeat the current question. You can also react to a question with :fast_forward: to get the next question after it's been answered.
    - `answer <answer>` - Answer a question. <answer> can always be an option number. It can also be "true" or "false" for true/false questions. You can also use reactions to answer a question.
    - `scores` - View the current scores. Easy questions are worth 10 points, medium questions are worth 20, and hard questions are worth 30 each. You can also react to a question with :trophy: to see the scores.
    - `end` - End the game (can only be used by the "host" (the one who started the game) or Forum Admins or higher).
    - `games` - See all ongoing games.
    - `importCustomQuestions` - Import custom questions as a JSON. Accessible to Org Admins or higher.
    - `exportCustomQuestions` - Export custom questions as a JSON. Accessible to Org Admins or higher.

    Here's how a game usually goes:
    - The "host" uses `@latexbot trivia categories` to see all categories (optional)
    - The "host" uses `@latexbot trivia start [category] [difficulty] [type]` to start the game
    - Someone uses `@latexbot trivia question` or `@latexbot trivia next` to get each question
    - The participants answer each question by using reactions or `@latexbot trivia answer <answer>`
    - The participants use `@latexbot trivia scores` to check the scores during the game
    - The "host" uses `@latexbot trivia end` to end the game

    Since LaTeX Bot v0.6.0, there can be multiple games per organization. 
    However, there can still only be one game per chat. This also includes your private messages with LaTeX Bot.
    After 15 minutes of inactivity, the game will end automatically.

    Note: The `importCustomQuestions`, `exportCustomQuestions`, and `end` sub-commands can have access rules.
    Use the names `trivia importCustomQuestions`, `trivia exportCustomQuestions` and `trivia end` respectively to refer to them in the accessRule command.
    ---
    group: General Commands
    syntax: <sub-command> [args]
    ---
    > `@latexbot trivia categories` - See all categories.
    > `@latexbot trivia start "Science: Computers" all true/false` - Start a game with the category "Science: Computers", all difficulties, and only true/false questions.
    > `@latexbot trivia question` - Get the question, or repeat the question.
    > `@latexbot trivia next` - Same as `@latexbot trivia question`
    > `@latexbot trivia answer 1` - Answer the question with option 1.
    > `@latexbot trivia scores` - See the current scores.
    > `@latexbot trivia end` - End the game.
    > `@latexbot trivia games` - See all ongoing games.
    > `@latexbot trivia importCustomQuestions {}` - Import some custom questions as a JSON.
    > `@latexbot trivia exportCustomQuestions` - Export some custom questions as a JSON.
    """
    if args == "":
        await chat.send_message("Error: Please specify a sub-command! See `@latexbot help trivia` for details.", bot.msg_creator)
        return

    # Purge old games
    for chat_id, game in bot.trivia_games.items():
        if game.ended:
            bot.trivia_games.pop(chat_id)

    # Find the first whitespace
    space = None
    for i, c in enumerate(args):
        if c.isspace():
            space = i
            break
    if space:
        cmd = args[:space]
        sub_args = args[space + 1:]
    else:
        cmd = args
        sub_args = ""
    
    if cmd == "exportCustomQuestions":
        if await bot.commands.commands["trivia exportCustomQuestions"].is_authorized(bot, chat, user):
            await util.send_json_data(chat, trivia.CUSTOM_TRIVIA_QUESTIONS, "Custom Questions:", 
                                      "trivia.json", bot.user, bot.msg_creator)
        else:
            await chat.send_message("You are not authorized to do that.", bot.msg_creator)
        return
    elif cmd == "importCustomQuestions":
        if await bot.commands.commands["trivia importCustomQuestions"].is_authorized(bot, chat, user):
            msg = await pyryver.retry_until_available(chat.get_message, msg_id, timeout=5.0)
            try:
                trivia.set_custom_trivia_questions(await util.get_attached_json_data(msg, sub_args))
                await chat.send_message("Operation successful.", bot.msg_creator)
            except ValueError as e:
                await chat.send_message(str(e), bot.msg_creator)
        else:
            await chat.send_message("You are not authorized to do that.", bot.msg_creator)
        return

    sub_args = shlex.split(sub_args)
    if cmd == "games":
        if not bot.trivia_games:
            await chat.send_message("No games are ongoing.", bot.msg_creator)
            return
        resp = "Current games:\n"
        resp += "\n".join(f"- Game started by {game.get_user_name(game.game.host)} in {bot.ryver.get_chat(id=chat).get_name()}." for chat, game in bot.trivia_games.items())
        await chat.send_message(resp, bot.msg_creator)
    elif cmd == "categories":
        # Note: The reason we're not starting from 0 here is because of markdown forcing you to start a list at 1
        categories = "\n".join(f"{i + 1}. {category['name']}" for i, category in enumerate(await trivia.get_categories()))
        custom_categories = trivia.get_custom_categories()
        if custom_categories:
            categories += "\n\n# Custom categories:\n"
            categories += "\n".join(f"* {category}" for category in custom_categories)
            categories += "\n\nCustom categories can only be specified by name. Use 'all' for all regular categories (no custom), or 'custom' for all custom categories (no regular)."
        await chat.send_message(f"# Categories:\n{categories}", bot.msg_creator)
    elif cmd == "start":
        if not (0 <= len(sub_args) <= 3):
            await chat.send_message("Invalid syntax. See `@latexbot help trivia` for details.", bot.msg_creator)
            return
        
        if chat.get_id() in bot.trivia_games:
            game = bot.trivia_games[chat.get_id()]
            await chat.send_message(f"Error: A game started by {game.get_user_name(game.game.host)} already exists in this chat.", bot.msg_creator)
            return
        
        # Try parsing the category
        if len(sub_args) >= 1:
            try:
                # Subtract 1 for correct indexing
                category = int(sub_args[0]) - 1
            except ValueError:
                category = sub_args[0]
            categories = await trivia.get_categories()
            if isinstance(category, int):
                if category < 0 or category >= len(categories):
                    await chat.send_message("Category ID out of bounds! Please see `@latexbot trivia categories` for all valid categories.", bot.msg_creator)
                    return
                # Get the actual category ID
                category = categories[category]["id"]
            # String-based category
            else:
                category = category.lower()
                if category == "all":
                    category = None
                elif category == "custom":
                    category = "custom"
                else:
                    found = False
                    for c in categories:
                        # Case-insensitive search
                        if c["name"].lower() == category:
                            found = True
                            category = c["id"]
                            break
                    if not found:
                        for c in trivia.get_custom_categories():
                            if c.lower() == category:
                                found = True
                                category = c
                                break
                    if not found:
                        await chat.send_message("Invalid category. Please see `@latexbot trivia categories` for all valid categories.", bot.msg_creator)
                        return
        else:
            category = None
            difficulty = None
            question_type = None
        
        # Try parsing the difficulty
        if len(sub_args) >= 2:
            try:
                difficulty = {
                    "easy": trivia.TriviaSession.DIFFICULTY_EASY,
                    "medium": trivia.TriviaSession.DIFFICULTY_MEDIUM,
                    "hard": trivia.TriviaSession.DIFFICULTY_HARD,
                    "all": None,
                }[sub_args[1].lower()]
            except KeyError:
                await chat.send_message("Invalid difficulty! Allowed difficulties are 'easy', 'medium', 'hard' or 'all'.", bot.msg_creator)
                return
        else:
            difficulty = None
            question_type = None
        
        # Try parsing the type
        if len(sub_args) >= 3:
            try:
                question_type = {
                    "true/false": trivia.TriviaSession.TYPE_TRUE_OR_FALSE,
                    "multiple-choice": trivia.TriviaSession.TYPE_MULTIPLE_CHOICE,
                    "all": None,
                }[sub_args[2].lower()]
            except KeyError:
                await chat.send_message("Invalid question type! Allowed types are 'true/false', 'multiple-choice' or 'all'.", bot.msg_creator)
                return
        else:
            question_type = None
        
        # Start the game!
        game = trivia.TriviaGame()
        game.set_category(category)
        game.set_difficulty(difficulty)
        game.set_type(question_type)
        await game.start(user.get_id())
        trivia_game = trivia.LatexBotTriviaGame(chat, game, bot.msg_creator)
        bot.trivia_games[chat.get_id()] = trivia_game
        await trivia_game._try_get_next()

        await chat.send_message("Game started! Use `@latexbot trivia question` to get the question.", bot.msg_creator)
    elif cmd == "question" or cmd == "next":
        if chat.get_id() not in bot.trivia_games:
            await chat.send_message("Error: Game not started! Use `@latexbot trivia start [category] [difficulty] [type]` to start a game.", bot.msg_creator)
            return
        await bot.trivia_games[chat.get_id()].next_question()
    elif cmd == "answer":
        if len(sub_args) != 1:
            await chat.send_message("Invalid syntax. See `@latexbot help trivia` for details.", bot.msg_creator)
            return
        
        if chat.get_id() not in bot.trivia_games:
            await chat.send_message("Error: Game not started! Use `@latexbot trivia start [category] [difficulty] [type]` to start a game.", bot.msg_creator)
            return
        
        game = bot.trivia_games[chat.get_id()]
        if game.game.current_question["answered"]:
            await chat.send_message("Error: The current question has already been answered. Use `@latexbot trivia question` to get the next question.", bot.msg_creator)
            return
        
        try:
            # Subtract 1 for correct indexing
            answer = int(sub_args[0]) - 1
        except ValueError:
            # Is this a true/false question?
            if game.game.current_question["type"] == trivia.TriviaSession.TYPE_TRUE_OR_FALSE:
                answer = sub_args[0].lower()
                # Special handling for true/false text
                if answer == "true":
                    answer = 0
                elif answer == "false":
                    answer = 1
                else:
                    await chat.send_message("Please answer 'true' or 'false' or an option number!", bot.msg_creator)
                    return
            else:
                await chat.send_message("Answer must be an option number, not text!", bot.msg_creator)
                return
        
        if answer < 0 or answer >= len(game.game.current_question["answers"]):
            await chat.send_message("Invalid answer number!", bot.msg_creator)
            return
        
        await game.answer(answer, user.get_id())
    elif cmd == "scores":
        if chat.get_id() not in bot.trivia_games:
            await chat.send_message("Error: Game not started! Use `@latexbot trivia start [category] [difficulty] [type]` to start a game.", bot.msg_creator)
            return
        await bot.trivia_games[chat.get_id()].send_scores()
    elif cmd == "end":
        if chat.get_id() not in bot.trivia_games:
            await chat.send_message("Error: Game not started! Use `@latexbot trivia start [category] [difficulty] [type]` to start a game.", bot.msg_creator)
            return
        game = bot.trivia_games[chat.get_id()]
        # Get the message object so we can check if the user is authorized
        if user.get_id() == game.game.host or await bot.commands.commands["trivia end"].is_authorized(bot, chat, user):
            # Display the scores
            scores = trivia.order_scores(game.game.scores)
            if not scores:
                await chat.send_message("Game ended. No questions were answered, so there are no scores to display.", bot.msg_creator)
            else:
                resp = "The game has ended. "
                # Single winner
                if len(scores[1][0]) == 1:
                    resp += f"**{game.get_user_name(scores[1][0][0])}** is the winner with a score of **{scores[1][1]}**!\n\nFull scoreboard:\n"
                # Multiple winners
                else:
                    resp += f"**{', '.join(game.get_user_name(winner) for winner in scores[1][0])}** are the winners, tying with a score of **{scores[1][1]}**!\n\nFull scoreboard:\n"
                await chat.send_message(resp, bot.msg_creator)
                await game.send_scores()
            await game.end()
            del bot.trivia_games[chat.get_id()]
        else:
            await chat.send_message("Error: Only the one who started the game or a Forum Admin or higher may end the game!", bot.msg_creator)
    else:
        await chat.send_message("Invalid sub-command! Please see `@latexbot help trivia` for all valid sub-commands.", bot.msg_creator)


async def reaction_trivia(bot: "latexbot.LatexBot", ryver: pyryver.Ryver, session: pyryver.RyverWS, data: typing.Dict[str, typing.Any]): # pylint: disable=unused-argument
    """
    This coro does extra processing for interfacing trivia with reactions.
    """
    # Verify that this is an answer to a trivia question
    if data["type"] != "Entity.ChatMessage":
        return
    for game in bot.trivia_games.values():
        if game.question_msg is None:
            return
        if data["id"] == game.question_msg.get_id():
            user = ryver.get_user(id=data["userId"])
            if user == bot.user:
                return
                
            # Scoreboard
            if data["reaction"] == "trophy":
                await game.send_scores()
                return

            # Next question
            if data["reaction"] == "fast_forward":
                if game.game.current_question["answered"]:
                    await game.next_question()
                return

            # Answer
            if game.game.current_question["answered"]:
                return
            # Try to decode the reaction into an answer
            if game.game.current_question["type"] == trivia.TriviaSession.TYPE_MULTIPLE_CHOICE:
                try:
                    answer = trivia.LatexBotTriviaGame.TRIVIA_NUMBER_EMOJIS.index(data["reaction"])
                    # Give up if it's invalid
                    if answer >= len(game.game.current_question["answers"]):
                        return
                except ValueError:
                    return
            else:
                if data["reaction"] == "white_check_mark":
                    answer = 0
                elif data["reaction"] == "x":
                    answer = 1
                else:
                    return
            
            await game.answer(answer, data["userId"])
            break


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

    If the data is less than 1000 characters long, it will be sent as a chat message.
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
        data = await util.get_attached_json_data(await pyryver.retry_until_available(chat.get_message, msg_id, timeout=5.0), args)
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


async def command_events(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
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
        count = int(args) if args else 3
        if count < 1:
            raise ValueError
    except ValueError:
        await chat.send_message(f"Error: Invalid number.", bot.msg_creatorbot.msg_creator)
        return
    
    events = bot.calendar.get_upcoming_events(count)

    now = util.current_time()
    ongoing = []
    upcoming = []
    
    # Process all the events
    for event in events:
        start = Calendar.parse_time(event["start"])
        end = Calendar.parse_time(event["end"])
        # See if the event has started
        # If the date has no timezone info, make it the organization timezone for comparisons
        if not start.tzinfo:
            start = start.replace(tzinfo=config.timezone)
            # No timezone info means this was created as an all-day event
            has_time = False
        else:
            has_time = True
        if now > start:
            ongoing.append((event, start, end, has_time))
        else:
            upcoming.append((event, start, end, has_time))

    if len(ongoing) > 0:
        resp = "---------- Ongoing Events ----------"
        for evt in ongoing:
            event, start, end, has_time = evt
            # The day number of the event
            day = util.caldays_diff(now, start) + 1
            # If the event does not have a time, then don't include the time
            start_str = datetime.strftime(start, util.DATETIME_DISPLAY_FORMAT if has_time else util.DATE_DISPLAY_FORMAT)
            end_str = datetime.strftime(end, util.DATETIME_DISPLAY_FORMAT if has_time else util.DATE_DISPLAY_FORMAT)
            resp += f"\n# Day *{day}* of {event['summary']} (*{start_str}* to *{end_str}*)"
            if "description" in event and event["description"] != "":
                # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
                resp += f"\u200B:\n{markdownify(event['description'])}"
        resp += "\n\n"
    else:
        resp = ""
    if len(upcoming) > 0:
        resp += "---------- Upcoming Events ----------"
        for evt in upcoming:
            event, start, end, has_time = evt
            # days until the event
            day = util.caldays_diff(start, now)
            # If the event does not have a time, then don't include the time
            start_str = datetime.strftime(start, util.DATETIME_DISPLAY_FORMAT if has_time else util.DATE_DISPLAY_FORMAT)
            end_str = datetime.strftime(end, util.DATETIME_DISPLAY_FORMAT if has_time else util.DATE_DISPLAY_FORMAT)
            resp += f"\n# *{day}* day(s) until {event['summary']} (*{start_str}* to *{end_str}*)"
            if "description" in event and event["description"] != "":
                # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
                resp += f"\u200B:\n{markdownify(event['description'])}"
    else:
        resp += "***No upcoming events at the moment.***"

    await chat.send_message(resp, bot.msg_creator)


async def command_quickAddEvent(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
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
    event = bot.calendar.quick_add(args)
    start = Calendar.parse_time(event["start"])
    end = Calendar.parse_time(event["end"])
    # Correctly format based on whether the event is an all-day event
    # All day events don't come with timezone info
    start_str = datetime.strftime(start, util.DATETIME_DISPLAY_FORMAT if start.tzinfo else util.DATE_DISPLAY_FORMAT)
    end_str = datetime.strftime(end, util.DATETIME_DISPLAY_FORMAT if end.tzinfo else util.DATE_DISPLAY_FORMAT)
    await chat.send_message(f"Created event {event['summary']} (**{start_str}** to **{end_str}**).\nLink: {event['htmlLink']}", bot.msg_creator)


async def command_addEvent(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
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
    if "\n" in args:
        i = args.index("\n")
        desc = args[i + 1:]
        args = args[:i]
    else:
        desc = None
    try:
        args = shlex.split(args)
    except ValueError as e:
        await chat.send_message(f"Invalid syntax: {e}", bot.msg_creator)
        return  
    if len(args) != 3 and len(args) != 5:
        await chat.send_message("Error: Invalid syntax. Check `@latexbot help addEvent` for help. You may have to use quotes if any of the parameters contain spaces.", bot.msg_creator)
        return
    
    # No times specified
    if len(args) == 3:
        start = util.tryparse_datetime(args[1], util.ALL_DATE_FORMATS)
        if not start:
            await chat.send_message(f"Error: The date {args[1]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", bot.msg_creator)
            return
        end = util.tryparse_datetime(args[2], util.ALL_DATE_FORMATS)
        if not end:
            await chat.send_message(f"Error: The date {args[2]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", bot.msg_creator)
            return
        event_body = {
            "start": {
                "date": datetime.strftime(start, util.CALENDAR_DATE_FORMAT),
            },
            "end": {
                "date": datetime.strftime(end, util.CALENDAR_DATE_FORMAT),
            }
        }
    else:
        start_date = util.tryparse_datetime(args[1], util.ALL_DATE_FORMATS)
        if not start_date:
            await chat.send_message(f"Error: The date {args[1]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", bot.msg_creator)
            return
        start_time = util.tryparse_datetime(args[2], util.ALL_TIME_FORMATS)
        if not start_time:
            await chat.send_message(f"Error: The time {args[2]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", bot.msg_creator)
            return

        end_date = util.tryparse_datetime(args[3], util.ALL_DATE_FORMATS)
        if not end_date:
            await chat.send_message(f"Error: The date {args[3]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", bot.msg_creator)
            return
        end_time = util.tryparse_datetime(args[4], util.ALL_TIME_FORMATS)
        if not end_time:
            await chat.send_message(f"Error: The time {args[4]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", bot.msg_creator)
            return
        
        # Merge to get datetimes
        start = datetime.combine(start_date, start_time.time())
        end = datetime.combine(end_date, end_time.time())
        event_body = {
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": bot.timezone,
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": bot.timezone,
            }
        }
    event_body["summary"] = args[0]
    if desc:
        event_body["description"] = desc
    event = bot.calendar.add_event(event_body)
    start_str = datetime.strftime(start, util.DATETIME_DISPLAY_FORMAT if len(args) == 5 else util.DATE_DISPLAY_FORMAT)
    end_str = datetime.strftime(end, util.DATETIME_DISPLAY_FORMAT if len(args) == 5 else util.DATE_DISPLAY_FORMAT)
    if not desc:
        await chat.send_message(f"Created event {event['summary']} (**{start_str}** to **{end_str}**).\nLink: {event['htmlLink']}", bot.msg_creator)
    else:
        # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
        await chat.send_message(f"Created event {event['summary']} (**{start_str}** to **{end_str}**)\u200B:\n{markdownify(event['description'])}\n\nLink: {event['htmlLink']}", bot.msg_creator)


async def command_deleteEvent(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
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
    args = args.lower()
    events = bot.calendar.get_upcoming_events()
    matched_event = None
    
    for event in events:
        # Found a match
        if args in event["summary"].lower():
            matched_event = event
            break
    
    if matched_event:
        bot.calendar.remove_event(matched_event["id"])
        # Format the start and end of the event into strings
        start = Calendar.parse_time(matched_event["start"])
        end = Calendar.parse_time(matched_event["end"])
        start_str = datetime.strftime(start, util.DATETIME_DISPLAY_FORMAT if start.tzinfo else util.DATE_DISPLAY_FORMAT)
        end_str = datetime.strftime(end, util.DATETIME_DISPLAY_FORMAT if end.tzinfo else util.DATE_DISPLAY_FORMAT)
        await chat.send_message(f"Deleted event {matched_event['summary']} (**{start_str}** to **{end_str}**).", bot.msg_creator)
    else:
        await chat.send_message(f"Error: No event matches that name.", bot.msg_creator)


async def command_setEnabled(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Enable or disable me.
    ---
    group: Developer Commands
    syntax: true|false
    """
    # The only way this actually gets called is if the user passed neither "true" nor "false"
    await chat.send_message(f"Invalid option: {args}", bot.msg_creator)


KILL_MSGS = [
    "Goodbye, world.",
    "Bleh I'm dead",
    "x_x",
    "Goodbye cruel world",
]


async def command_kill(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Kill me (:fearful:).

    With the current settings, I will restart a few minutes after being killed.
    Consider using the disable or sleep commands if you intend to disable me.
    ---
    group: Developer Commands
    syntax:
    """
    await chat.send_message(KILL_MSGS[random.randrange(0, len(KILL_MSGS))], bot.msg_creator)
    exit()


async def command_sleep(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
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
        secs = float(args)
    except ValueError:
        await chat.send_message("Invalid number.", bot.msg_creator)
        return
    # TODO: Change this
    await chat.send_message("Good night! :sleeping:", bot.msg_creator)
    time.sleep(secs)
    await chat.send_message("Good morning!", bot.msg_creator)


async def command_execute(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
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
    """
    # Temporarily replace stdout and stderr
    stdout = sys.stdout
    stderr = sys.stderr
    # Merge stdout and stderr
    try:
        sys.stdout = io.StringIO()
        sys.stderr = sys.stdout
        exec(args, globals(), locals()) # pylint: disable=exec-used
        output = sys.stdout.getvalue()

        await chat.send_message(output, bot.msg_creator)
    except Exception: # pylint: disable=broad-except
        await chat.send_message(
            f"An exception has occurred:\n```\n{format_exc()}\n```", bot.msg_creator)
    finally:
        sys.stdout = stdout
        sys.stderr = stderr


async def command_updateChats(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Update the cached list of forums/teams and users.

    As getting organization data takes time, LaTeX Bot caches this information,
    so when org data is updated, such as when a new user joins, or when a new forum is created,
    LaTeX Bot might fail to recognize it. Run this command to fix it.
    ---
    group: Developer Commands
    syntax:
    """
    await bot.ryver.load_chats()
    await chat.send_message("Forums/Teams/Users updated.", bot.msg_creator)


async def command_alias(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Manage aliases.

    Aliases allow you to save typing time on a commonly used command.
    They're expanded as if they were a command; therefore, they cannot contain whitespace.

    E.g. If there is an alias `answer` \u2192 `trivia answer`, the command
    `@latexbot answer 1` will expand to `@latexbot trivia answer 1`.
    However, the `answer` in `@latexbot trivia answer` will not be expanded.
    Note that alias expansion happens before command evaluation.

    Aliases can refer to other aliases. However, recursive aliases cannot be evaluated.
    E.g. If `A` \u2192 `B` and `B` \u2192 `C`, both `A` and `B` will expand to `C`.
    However, if `B` \u2192 `A`, both `A` and `B` will fail to evaluate.

    The alias command has 3 actions (sub-commands). They are as follows:
    - No argument: View all aliases.
    - `create [from] [to]` - Create an alias. If the expansion has spaces, it should be surrounded by quotes.
    - `delete [alias]` - Delete an alias.
    ---
    group: Miscellaneous Commands
    syntax: [create|delete] [args]
    ---
    > `@latexbot alias` - View all aliases.
    > `@latexbot alias create "answer" "trivia answer"` - Create an alias `answer` that expands to `trivia answer`.
    > `@latexbot alias delete "answer"` - Delete the alias `answer`.
    """
    if args == "":
        if not config.aliases:
            resp = "No aliases have been created."
        else:
            resp = "All aliases:"
            for alias in config.aliases:
                resp += f"\n* `{alias['from']}` \u2192 `{alias['to']}"
        await chat.send_message(resp, bot.msg_creator)
        return

    args = shlex.split(args)
    if args[0] == "create":
        if len(args) != 3:
            await chat.send_message("Invalid syntax. Did you forget the quotes?", bot.msg_creator)
            return
        config.aliases.append({
            "from": args[1],
            "to": args[2],
        })
        bot.update_help()
        bot.save_config()
        await chat.send_message(f"Successfully created alias `{args[1]}` \u2192 `{args[2]}`.", bot.msg_creator)
    elif args[0] == "delete":
        if len(args) != 2:
            await chat.send_message("Invalid syntax.", bot.msg_creator)
            return
        
        for i, alias in enumerate(config.aliases):
            if alias["from"] == args[1]:
                del config.aliases[i]
                bot.update_help()
                bot.save_config()
                await chat.send_message(f"Successfully deleted alias `{args[1]}`.", bot.msg_creator)
                return
        await chat.send_message(f"Alias not found!", bot.msg_creator)
    else:
        await chat.send_message("Invalid action. Allowed actions are create, delete and no argument (view).", bot.msg_creator)


async def command_exportConfig(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Export config as a JSON.

    If the data is less than 1000 characters long, it will be sent as a chat message.
    Otherwise it will be sent as a file attachment.
    ---
    group: Miscellaneous Commands
    syntax:
    """
    data, err = config.dump()
    if err:
        await chat.send_message(err, bot.msg_creator)
    await util.send_json_data(chat, data, "Config:", "config.json", bot.user, bot.msg_creator)


async def command_importConfig(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Import config from JSON.

    Note that although it is encouraged, the config JSON does not have to contain all fields.
    If a field is not specified, it will just be left unchanged.

    If a file is attached to this message, the config will always be imported from the file.
    ---
    group: Miscellaneous Commands
    syntax: <data>
    """
    try:
        errs = config.load(await util.get_attached_json_data(await pyryver.retry_until_available(
            chat.get_message, msg_id, timeout=5.0), args))
        if errs:
            util.log("Error loading config:", errs)
        bot.reload_config()
        bot.update_help()
        bot.save_config()
        if errs:
            await chat.send_message(errs, bot.msg_creator)
        else:
            await chat.send_message("Operation successful.", bot.msg_creator)
    except ValueError as e:
        await chat.send_message(str(e), bot.msg_creator)


async def command_accessRule(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    View or modify access rules.

    Access rules are a powerful and flexible way of controlling access to commands.
    They work together with access levels to grant and restrict access.

    Each command may have a number of access rules associated with it. 
    Here are all the types of access rules:
    - `level`: Override the access level of the command. Each access level is represented by a number. See [the usage guide](https://github.com/tylertian123/ryver-latexbot/blob/master/usage_guide.md#access-levels) for more details.
    - `allowUser`: Allow a user to access the command regardless of their access level.
    - `disallowUser`: Disallow a user to access the command regardless of their access level.
    - `allowRole`: Allow users with a role to access the command regardless of their access level.
    - `disallowRole`: Disallow users with a role to access the command regardless of their access level.

    If there is a conflict between two rules, the more specific rule will come on top;
    i.e. rules about specific users are the most powerful, followed by rules about specific roles, and then followed by general access level rules.
    Rules that disallow access are also more powerful than rules that allow access.
    E.g. "disallowRole" overrides "allowRole", but "allowUser" still overrides them both as it's more specific.

    To use this command, you need to specify a command, an action, a rule type and argument(s).
    If none of these arguments are given, this command will print out all access rules for every command.
    If only a command name is given, this command will print out the access rules for that command.

    The command is simply the command for which you want to modify or view the access rules.
    The action can be one of these:
    - `set` - Set the value; **only supported by the `level` rule type and only takes 1 argument**.
    - `add` - Add a value to the list; **not supported by the `level` rule type**.
    - `remove` - Remove a value from the list; **not supported by the `level` rule type**.
    - `delete` - Remove a rule entirely; **does not take any arguments**.

    The rule type is one of the 5 access rule types mentioned above (`level`, `allowUser`, etc).
    The argument(s) are one or more values for the operation, e.g. users to add to the allow list.
    Note that the `set` action can only take one argument.
    
    See the examples below.
    ---
    group: Miscellaneous Commands
    syntax: [command] [action] [ruletype] [args]
    ---
    > `@latexbot accessRule` - View all access rules for every command.
    > `@latexbot accessRule ping` - View access rules for the "ping" command.
    > `@latexbot accessRule ping set level 1` - Set the access level for "ping" to 1 (Forum Admins).
    > `@latexbot accessRule ping delete level` - Undo the command above.
    > `@latexbot accessRule ping add allowUser tylertian foo` - Allow users tylertian and foo to access the ping command regardless of his access level.
    > `@latexbot accessRule ping remove allowUser tylertian foo` - Undo the command above.
    > `@latexbot accessRule ping add allowRole Pingers` - Allow the "pingers" role to access the ping command regardless of their access level.
    > `@latexbot accessRule ping add disallowUser tylertian` - Disallow tylertian from accessing the ping command regardless of his access level.
    """
    if args == "":
        if not config.access_rules:
            await chat.send_message("No access rules were created.", bot.msg_creator)
            return
        resp = "\n\n".join(util.format_access_rules(command, rule) for command, rule in config.access_rules.items())
        await chat.send_message(resp, bot.msg_creator)
        return
    args = shlex.split(args)
    # Only command name is given - show access rules
    if len(args) == 1:
        if args[0] not in bot.commands.commands:
            await chat.send_message(f"Error: Invalid command.", bot.msg_creator)
            return
        if args[0] in config.access_rules:
            await chat.send_message(util.format_access_rules(args[0], config.access_rules[args[0]]), bot.msg_creator)
        else:
            await chat.send_message(f"No access rules for command {args[0]}.", bot.msg_creator)
    # If both command name and action are given, then rule type and args must be given
    elif len(args) < 3:
        await chat.send_message("Invalid syntax! See `@latexbot help accessRule` for details.", bot.msg_creator)
    else:
        # Verify arguments are correct
        if args[0] not in bot.commands.commands:
            await chat.send_message(f"Error: Invalid command.", bot.msg_creator)
            return
        if args[1] == "set":
            if args[2] != "level":
                await chat.send_message(f"Error: Invalid rule type for action `set`: {args[2]}. See `@latexbot help accessRule` for details.", bot.msg_creator)
                return
            if len(args) != 4:
                await chat.send_message(f"Error: The `set` action takes exactly 1 argument.", bot.msg_creator)
                return
            try:
                level = int(args[3])
            except ValueError:
                await chat.send_message(f"Error: Invalid access level: {level}. Access levels must be integers. See `@latexbot help accessRule` for details.", bot.msg_creator)
            # Set the rules
            rules = config.access_rules.get(args[0], {})
            rules["level"] = level
            config.access_rules[args[0]] = rules
        # Combine the two because they're similar
        elif args[1] == "add" or args[1] == "remove":
            # Verify rule type
            if args[2] not in ["allowUser", "disallowUser", "allowRole", "disallowRole"]:
                await chat.send_message(f"Error: Invalid rule type for action `{args[1]}`: {args[2]}. See `@latexbot help accessRule` for details.", bot.msg_creator)
                return
            if len(args) < 4:
                await chat.send_message(f"Error: At least one argument must be supplied for action `{args[1]}`. See `@latexbot help accessRule` for details.", bot.msg_creator)
                return
            # Set the rules
            rules = config.access_rules.get(args[0], {})
            if args[1] == "add":
                # If there are already items, merge the lists
                if args[2] in rules:
                    for arg in args[3:]:
                        # Don't allow duplicates
                        if arg in rules[args[2]]:
                            await chat.send_message(f"Warning: {arg} is already in the list for rule {args[2]}.", bot.msg_creator)
                        else:
                            rules[args[2]].append(arg)
                # Otherwise directly assign
                else:
                    rules[args[2]] = args[3:]
            else:
                if args[2] not in rules:
                    await chat.send_message(f"Error: Rule {args[2]} is not set for command {args[0]}.", bot.msg_creator)
                    return
                # Remove each one
                for arg in args[3:]:
                    if arg not in rules[args[2]]:
                        await chat.send_message(f"Warning: {arg} is not in the list for rule {args[2]}.", bot.msg_creator)
                    else:
                        rules[args[2]].remove(arg)
                # Don't leave empty arrays
                if not rules[args[2]]:
                    rules.pop(args[2])
            # Set the field
            # This is needed in case get() returned the empty dict
            config.access_rules[args[0]] = rules
            # Don't leave empty dicts
            if not config.access_rules[args[0]]:
                config.access_rules.pop(args[0])
        elif args[1] == "delete":
            if len(args) != 3:
                await chat.send_message(f"Error: The `delete` action does not take any arguments.", bot.msg_creator)
                return
            try:
                config.access_rules[args[0]].pop(args[2])
                # Don't leave empty dicts
                if not config.access_rules[args[0]]:
                    config.access_rules.pop(args[0])
            except KeyError:
                await chat.send_message(f"Error: Command {args[0]} does not have rule {args[2]} set.", bot.msg_creator)
                return
        else:
            await chat.send_message(f"Error: Invalid action: {args[1]}. See `@latexbot help accessRule` for details.", bot.msg_creator)
            return
        
        bot.update_help()
        bot.save_config()
        await chat.send_message("Operation successful.", bot.msg_creator)


async def command_setDailyMessageTime(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Set the time daily messages are sent each day or turn them on/off.

    The time must be in the "HH:MM" format (24-hour clock).
    Leave the argument blank to turn daily messages off.
    ---
    group: Miscellaneous Commands
    syntax: [time]
    ---
    > `@latexbot setDailyMessageTime 00:00` - Set daily messages to be sent at 12am each day.
    > `@latexbot setDailyMessageTime` - Turn off daily messages.
    """
    if args == "" or args.lower() == "off":
        config.daily_msg_time = None
    else:
        # Try parse to ensure validity
        try:
            config.daily_msg_time = datetime.strptime(args, "%H:%M")
        except ValueError:
            await chat.send_message("Invalid time format.", bot.msg_creator)
            return
    
    # Schedule or unschedule the daily message task
    bot.schedule_daily_message()
    
    bot.save_config()
    if config.daily_msg_time:
        await chat.send_message(f"Messages will now be sent at {args} daily.", bot.msg_creator)
    else:
        await chat.send_message(f"Messages have been disabled.", bot.msg_creator)


async def command_dailyMessage(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Send the daily message.

    The daily message is sent automatically each day at a set time if it is turned on
    (through `setDailyMessageTime`). This command can be used to trigger it manually.

    Note that the daily message will be sent to the chats in the config, not the chat
    that this command was invoked from.
    ---
    group: Miscellaneous Commands
    syntax:
    ---
    > `@latexbot dailyMessage` - Send the daily message.
    """
    now = util.current_time()
    events = bot.calendar.get_today_events(now)
    if events:
        resp = "Reminder: These events are happening today:"
        for event in events:
            start = Calendar.parse_time(event["start"])
            end = Calendar.parse_time(event["end"])

            # The event has a time, and it starts today (not already started)
            if start.tzinfo and start > now:
                resp += f"\n# {event['summary']} today at *{start.strftime(util.TIME_DISPLAY_FORMAT)}*"
            else:
                # Otherwise format like normal
                start_str = start.strftime(util.DATETIME_DISPLAY_FORMAT if start.tzinfo else util.DATE_DISPLAY_FORMAT)
                end_str = end.strftime(util.DATETIME_DISPLAY_FORMAT if end.tzinfo else util.DATE_DISPLAY_FORMAT)
                resp += f"\n# {event['summary']} (*{start_str}* to *{end_str}*)"

            # Add description if there is one
            if "description" in event and event["description"] != "":
                # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
                resp += f"\u200B:\n{markdownify(event['description'])}"
        await bot.announcements_chat.send_message(resp, bot.msg_creator)
    
    url = f"https://www.checkiday.com/api/3/?d={now.strftime('%Y/%m/%d')}"
    async with aiohttp.request("GET", url) as resp:
        if resp.status != 200:
            util.log(f"HTTP error while trying to get holidays: {resp}")
            data = {
                "error": f"HTTP error while trying to get holidays: {resp}",
            }
        else:
            data = await resp.json()
    if data["error"] != "none":
        await bot.messages_chat.send_message(f"Error while trying to check today's holidays: {data['error']}", bot.msg_creator)
    else:
        if data.get("holidays", None):
            msg = f"Here is a list of all the holidays today:\n"
            msg += "\n".join(f"* [{holiday['name']}]({holiday['url']})" for holiday in data["holidays"])
            await bot.messages_chat.send_message(msg, bot.msg_creator)
    comic = await xkcd.get_comic()
    if comic['num'] <= config.last_xkcd:
        util.log(f"No new xkcd found (latest is {comic['num']}).")
    else:
        util.log(f"New comic found! (#{comic['num']})")
        xkcd_creator = pyryver.Creator(bot.msg_creator.name, util.XKCD_PROFILE)
        await bot.messages_chat.send_message(f"New xkcd!\n\n{xkcd.comic_to_str(comic)}", xkcd_creator)
        # Update xkcd number
        config.last_xkcd = comic['num']
        bot.save_config()


async def command_message(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Send a message to a chat by ID.
    ---
    group: Hidden Commands
    syntax: <id> <message>
    hidden: true
    """
    try:
        i = args.index(" ")
    except ValueError:
        await chat.send_message("Invalid syntax.", bot.msg_creator)
        return
    chat_id = args[:i]
    msg = args[i + 1:]
    try:
        chat_id = int(chat_id)
    except ValueError:
        await chat.send_message("Invalid chat ID.", bot.msg_creator)
        return
    to = chat.get_ryver().get_chat(id=chat_id)
    if to is None:
        await chat.send_message("Chat not found.", bot.msg_creator)
        return
    await to.send_message(msg, bot.msg_creator)


import latexbot # nopep8 # pylint: disable=unused-import
