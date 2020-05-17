import asyncio
import io
import json
import org
import aiohttp # DON'T MOVE THIS!
import os
import pyryver
import render
import shlex
import sys
import time
import trivia
import typing
import xkcd
from caseinsensitivedict import CaseInsensitiveDict
from datetime import datetime, timedelta
from latexbot_util import *
from markdownify import markdownify
from gcalendar import Calendar
from traceback import format_exc

# Make print() flush immediately
# Otherwise the logs won't show up in real time in Docker
old_print = print


def print(*args, **kwargs):
    kwargs["flush"] = True
    # Add timestamp
    old_print(current_time().strftime("%Y-%m-%d %H:%M:%S"), *args, **kwargs)


################################ GLOBAL VARIABLES AND CONSTANTS ################################

VERSION = "v0.5.0-dev"

creator = pyryver.Creator(f"LaTeX Bot {VERSION}", "")

enabled = True

# Auto generated later
help_text = ""
extended_help_text = {}

daily_message_task = None # type: asyncio.Future

trivia_game = None # type: trivia.TriviaGame
trivia_lock = asyncio.Lock()
trivia_timeout = None # type: asyncio.Future
trivia_question_mid = None # type: str
trivia_chat = None # type: pyryver.Chat
TRIVIA_NUMBER_EMOJIS = ["one", "two", "three", "four", "five", "six", "seven", "eight"]
TRIVIA_POINTS = {
    trivia.TriviaSession.DIFFICULTY_EASY: 10,
    trivia.TriviaSession.DIFFICULTY_MEDIUM: 20,
    trivia.TriviaSession.DIFFICULTY_HARD: 30,
}

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
            access_level = ACCESS_LEVEL_STRS.get(command[1], f"**Unknown Access Level: {command[1]}.**")
            description = f"{syntax} - {properties['short_desc']} {access_level}"

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
    if org.aliases:
        help_text += "\n\nCurrent Aliases:\n"
        help_text += "\n".join(f"* `{alias['from']}` \u2192 `{alias['to']}`" for alias in org.aliases)


def preprocess_command(command: str, is_dm: bool):
    """
    Preprocess a command.

    Separate the command into the command name and args and resolve aliases 
    if it is a command. Otherwise return None.

    If it encouters a recursive alias, it raises ValueError.
    """
    is_command = False
    for prefix in org.command_prefixes:
        # Check for a valid command prefix
        if command.startswith(prefix) and len(command) > len(prefix):
            is_command = True
            # Remove the prefix
            command = command[len(prefix):]
    
    # DMs don't require command prefixes
    if not is_command and not is_dm:
        return None
    
    # Repeat until all aliases are expanded
    used_aliases = set()
    while True:
        # Separate command from args
        # Find the first whitespace
        command = command.strip()
        space = None
        # Keep track of this for alias expansion
        space_char = ""
        for i, c in enumerate(command):
            if c.isspace():
                space = i
                space_char = c
                break
        
        if space:
            cmd = command[:space]
            args = command[space + 1:]
        else:
            cmd = command
            args = ""

        # Expand aliases
        command = None
        for alias in org.aliases:
            if alias["from"] == cmd:
                # Check for recursion
                if alias["from"] in used_aliases:
                    raise ValueError(f"Recursive alias: '{alias['from']}'!")
                used_aliases.add(alias["from"])
                # Expand the alias
                command = alias["to"] + space_char + args
                break
        # No aliases were expanded - return
        if not command:
            return (cmd.strip(), args.strip())
        # Otherwise go again until no more expansion happens


################################ COMMAND PROCESSORS ################################


async def _render(chat: pyryver.Chat, msg_id: str, formula: str):
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
    if len(formula) > 0:
        try:
            img_data = await render.render(formula, color="gray", transparent=True)
        except ValueError as e:
            await chat.send_message(f"Error while rendering formula:\n```\n{e}\n```")
            return
        file = (await chat.get_ryver().upload_file("equation.png", img_data, "image/png")).get_file()
        await chat.send_message(f"Formula: `{formula}`\n![{formula}]({file.get_url()})", creator)
    else:
        await chat.send_message("Formula can't be empty.", creator)


async def _chem(chat: pyryver.Chat, msg_id: str, s: str):
    """
    Render a chemical formula.

    The formula is rendered with the mhchem package with LaTeX.
    ---
    group: General Commands
    syntax: <formula>
    ---
    > `@latexbot chem HCl_{(aq)} + NaOH_{(aq)} -> H2O_{(l)} + NaCl_{(aq)}`
    """
    if len(s) > 0:
        try:
            img_data = await render.render(f"\\ce{{{s}}}", color="gray", transparent=True, extra_packages=["mhchem"])
        except ValueError as e:
            await chat.send_message(f"Error while rendering formula:\n```\n{e}\n```\n\nDid you forget to put spaces on both sides of the reaction arrow?")
            return
        file = (await chat.get_ryver().upload_file("formula.png", img_data, "image/png")).get_file()
        await chat.send_message(f"Formula: `{s}`\n![{s}]({file.get_url()})", creator)
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
        if s in extended_help_text:
            text = extended_help_text[s]
            author = await (await pyryver.retry_until_available(chat.get_message_from_id, msg_id, timeout=5))[0].get_author()
            if await is_authorized(chat, author, command_processors[s][1]):
                text += "\n\n:white_check_mark: **You have access to this command.**"
            else:
                text += "\n\n:no_entry: **You do not have access to this command.**"
            await chat.send_message(text, creator)
        else:
            await chat.send_message(default, creator)


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


async def _whatDoYouThink(chat: pyryver.Chat, msg_id: str, s: str):
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


async def _checkiday(chat: pyryver.Chat, msg_id: str, s: str):
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
    url = f"https://www.checkiday.com/api/3/?d={s or current_time().strftime('%Y/%m/%d')}"
    async with aiohttp.request("GET", url) as resp:
        if resp.status != 200:
            await chat.send_message(f"HTTP error while trying to get holidays: {resp}", creator)
            return
        data = await resp.json()
    if data["error"] != "none":
        await chat.send_message(f"Error: {data['error']}", creator)
        return
    if not data.get("holidays", None):
        await chat.send_message(f"No holidays on {data['date']}.")
        return
    else:
        msg = f"Here is a list of all the holidays on {data['date']}:\n"
        msg += "\n".join(f"* [{holiday['name']}]({holiday['url']})" for holiday in data["holidays"])
        await chat.send_message(msg, creator)


async def _trivia(chat: pyryver.Chat, msg_id: str, s: str):
    """
    Play a game of trivia. See extended description for details. Powered by [Open Trivia Database](https://opentdb.com/).
    
    The trivia command has several sub-commands. Here are each one of them:
    - `categories` - Get all the categories and their IDs, which are used later to start a game.
    - `start [category] [difficulty] [type]` - Start a game with an optional category, difficulty and type. The category can be an ID, or a name from the `categories` command. If the name contains a space, it must be surrounded with quotes. The difficulty can be "easy", "medium" or "hard". The type can be either "true/false" or "multiple-choice". You can also specify "all" for any of the categories.
    - `question`, `next` - Get the next question or repeat the current question.
    - `answer <answer>` - Answer a question. <answer> can always be an option number. It can also be "true" or "false" for true/false questions. You can also use reactions to answer a question.
    - `scores` - View the current scores. Easy questions are worth 10 points, medium questions are worth 20, and hard questions are worth 30 each.
    - `end` - End the game (can only be used by the "host" (the one who started the game) or Forum Admins or higher).

    Here's how a game usually goes:
    - The "host" uses `@latexbot trivia categories` to see all categories (optional)
    - The "host" uses `@latexbot trivia start [category] [difficulty] [type]` to start the game
    - Someone uses `@latexbot trivia question` or `@latexbot trivia next` to get each question
    - The participants answer each question by using reactions or `@latexbot trivia answer <answer>`
    - The participants use `@latexbot trivia scores` to check the scores during the game
    - The "host" uses `@latexbot trivia end` to end the game

    Note that there can only be 1 game going on at a time! 
    After 15 minutes of inactivity, the game will end automatically.
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
    """
    if s == "":
        await chat.send_message("Error: Please specify a sub-command! See `@latexbot help trivia` for details.", creator)
        return
    
    global trivia_game, trivia_timeout, trivia_question_mid, trivia_chat

    # Helper functions and coros
    async def trivia_try_get_next() -> bool:
        """
        Try to get the next trivia question while handling errors.
        """
        global trivia_game
        try:
            await trivia_game.next_question()
            return True
        except trivia.OpenTDBError as e:
            err = {
                trivia.OpenTDBError.CODE_NO_RESULTS: "No results!",
                trivia.OpenTDBError.CODE_INVALID_PARAM: "Internal error",
                trivia.OpenTDBError.CODE_TOKEN_EMPTY: "Ran out of questions! Please end the game using `@latexbot trivia end`.",
                trivia.OpenTDBError.CODE_TOKEN_NOT_FOUND: "Invalid game session! Perhaps the game has expired?",
                trivia.OpenTDBError.CODE_SUCCESS: "This should never happen.",
            }[e.code]
            await chat.send_message(f"Cannot get next question: {err}", creator)
            if e.code == trivia.OpenTDBError.CODE_TOKEN_NOT_FOUND:
                # End the session
                await chat.send_message(f"Ending invalid session...")
                await end_game()
            return False
    
    def format_question(question) -> str:
        """
        Format a trivia question.
        """
        result = f":grey_question: Category: *{question['category']}*, Difficulty: **{question['difficulty']}**\n\n"
        if question['type'] == trivia.TriviaSession.TYPE_TRUE_OR_FALSE:
            result += "True or False: "
        result += question["question"]
        answers = "\n".join(f"{i + 1}. {answer}" for i, answer in enumerate(question["answers"]))
        result += "\n" + answers
        return result

    async def end_game():
        """
        End the game and clean up.
        """
        global trivia_game, trivia_timeout, trivia_question_mid, trivia_chat
        # Stop the timeout task
        if trivia_timeout:
            trivia_timeout.cancel()
            trivia_timeout = None
        # End the game
        await trivia_game.end()
        trivia_game = None
        # Other things
        trivia_question_mid = None
        trivia_chat = None

    
    async def trivia_timeout_task(timeout: float):
        """
        This task waits for a number of seconds, and then ends the current trivia game if there is one.
        """
        try:
            await asyncio.sleep(timeout)

            async with trivia_lock:
                global trivia_game
                if trivia_game is not None:
                    await chat.send_message(f"The trivia game started by {chat.get_ryver().get_user(id=trivia_game.host).get_name()} has ended due to inactivity.", creator)
                    await end_game()
        except asyncio.CancelledError:
            pass
    
    def refresh_timeout():
        """
        Refresh the game auto-end timeout.
        """
        global trivia_timeout
        if trivia_timeout:
            trivia_timeout.cancel()
        trivia_timeout = asyncio.ensure_future(trivia_timeout_task(15 * 60))
    # Accessed later in the reactions handler
    _trivia.refresh_timeout = refresh_timeout

    s = shlex.split(s)
    async with trivia_lock:
        if s[0] == "categories":
            # Note: The reason we're not starting from 0 here is because of markdown forcing you to start a list at 1
            categories = "\n".join(f"{i + 1}. {category['name']}" for i, category in enumerate(await trivia.get_categories()))
            await chat.send_message(f"Categories:\n{categories}", creator)
        elif s[0] == "start":
            if not (1 <= len(s) <= 4):
                await chat.send_message("Invalid syntax. See `@latexbot help trivia` for details.", creator)
                return
            
            if trivia_game is not None:
                await chat.send_message(f"Error: A game is already ongoing! It was started by {chat.get_ryver().get_user(id=trivia_game.host).get_name()}.", creator)
                return
            
            # Try parsing the category
            if len(s) >= 2:
                try:
                    # Subtract 1 for correct indexing
                    category = int(s[1]) - 1
                except ValueError:
                    category = s[1]
                categories = await trivia.get_categories()
                if isinstance(category, int):
                    if category < 0 or category >= len(categories):
                        await chat.send_message("Category ID out of bounds! Please see `@latexbot trivia categories` for all valid categories.", creator)
                        return
                    # Get the actual category ID
                    category = categories[category]["id"]
                # String-based category
                else:
                    category = category.lower()
                    if category == "all":
                        category = None
                    else:
                        found = False
                        for c in categories:
                            # Case-insensitive search
                            if c["name"].lower() == category:
                                found = True
                                category = c["id"]
                                break
                        if not found:
                            await chat.send_message("Invalid category. Please see `@latexbot trivia categories` for all valid categories.", creator)
                            return
            else:
                category = None
                difficulty = None
                question_type = None
            
            # Try parsing the difficulty
            if len(s) >= 3:
                try:
                    difficulty = {
                        "easy": trivia.TriviaSession.DIFFICULTY_EASY,
                        "medium": trivia.TriviaSession.DIFFICULTY_MEDIUM,
                        "hard": trivia.TriviaSession.DIFFICULTY_HARD,
                        "all": None,
                    }[s[2].lower()]
                except KeyError:
                    await chat.send_message("Invalid difficulty! Allowed difficulties are 'easy', 'medium', 'hard' or 'all'.", creator)
                    return
            else:
                difficulty = None
                question_type = None
            
            # Try parsing the type
            if len(s) >= 4:
                try:
                    question_type = {
                        "true/false": trivia.TriviaSession.TYPE_TRUE_OR_FALSE,
                        "multiple-choice": trivia.TriviaSession.TYPE_MULTIPLE_CHOICE,
                        "all": None,
                    }[s[3].lower()]
                except KeyError:
                    await chat.send_message("Invalid question type! Allowed types are 'true/false', 'multiple-choice' or 'all'.", creator)
                    return
            else:
                question_type = None
            
            # Start the game!
            trivia_game = trivia.TriviaGame()
            trivia_game.set_category(category)
            trivia_game.set_difficulty(difficulty)
            trivia_game.set_type(question_type)
            msg = (await pyryver.retry_until_available(chat.get_message_from_id, msg_id, timeout=5.0))[0]
            await trivia_game.start(msg.get_author_id())

            await chat.send_message("Game started! Use `@latexbot trivia question` to get the question.", creator)
            refresh_timeout()

            # Try to get the next question, but don't send it
            if not await trivia_try_get_next():
                return
        elif s[0] == "question" or s[0] == "next":
            if not trivia_game:
                await chat.send_message("Error: Game not started! Use `@latexbot trivia start [category] [difficulty] [type]` to start a game.", creator)
                return
            
            refresh_timeout()
            # Only update the question if already answered
            if trivia_game.current_question["answered"]:
                # Try to get the next question
                if not await trivia_try_get_next():
                    return
            
            # Skip sending the request to get the message object
            mid = await chat.send_message(format_question(trivia_game.current_question), creator)
            msg = (await pyryver.retry_until_available(chat.get_message_from_id, mid, timeout=5.0))[0] # type: pyryver.ChatMessage
            if trivia_game.current_question["type"] == trivia.TriviaSession.TYPE_MULTIPLE_CHOICE:
                # Iterate the reactions array until all the options are accounted for
                for i, reaction in zip(range(len(trivia_game.current_question["answers"])), TRIVIA_NUMBER_EMOJIS):
                    await msg.react(reaction)
            else:
                await msg.react("white_check_mark")
                await msg.react("x")
            trivia_question_mid = mid
            trivia_chat = chat
        elif s[0] == "answer":
            if len(s) != 2:
                await chat.send_message("Invalid syntax. See `@latexbot help trivia` for details.", creator)
                return
            
            if not trivia_game:
                await chat.send_message("Error: Game not started! Use `@latexbot trivia start [category] [difficulty] [type]` to start a game.", creator)
                return
            
            refresh_timeout()

            if trivia_game.current_question["answered"]:
                await chat.send_message("Error: The current question has already been answered. Use `@latexbot trivia question` to get the next question.", creator)
                return
            
            try:
                # Subtract 1 for correct indexing
                answer = int(s[1]) - 1
            except ValueError:
                # Is this a true/false question?
                if trivia_game.current_question["type"] == trivia.TriviaSession.TYPE_TRUE_OR_FALSE:
                    answer = s[1].lower()
                    # Special handling for true/false text
                    if answer == "true":
                        answer = 0
                    elif answer == "false":
                        answer = 1
                    else:
                        await chat.send_message("Please answer 'true' or 'false' or an option number!", creator)
                        return
                else:
                    await chat.send_message("Answer must be an option number, not text!", creator)
                    return
            
            if answer < 0 or answer >= len(trivia_game.current_question["answers"]):
                await chat.send_message("Invalid answer number!", creator)
                return
            
            # Get the message object so we know who sent it
            msg = (await pyryver.retry_until_available(chat.get_message_from_id, msg_id, timeout=5.0))[0]
            points = TRIVIA_POINTS[trivia_game.current_question['difficulty']]

            if trivia_game.answer(answer, msg.get_author_id(), points):
                await chat.send_message(f"Correct answer! You earned {points} points!", creator)
            else:
                await chat.send_message(f"Wrong answer! The correct answer was option number {trivia_game.current_question['correct_answer'] + 1}.", creator)
        elif s[0] == "scores":
            if not trivia_game:
                await chat.send_message("Error: Game not started! Use `@latexbot trivia start [category] [difficulty] [type]` to start a game.", creator)
                return
            refresh_timeout()

            scores = sorted(trivia_game.scores.items(), key=lambda x: x[1], reverse=True)
            if not scores:
                await chat.send_message("No scores at the moment. Scores are only recorded after you answer a question.", creator)
                return
            resp = "\n".join(f"{i + 1}. **{chat.get_ryver().get_user(id=user).get_name()}** with a score of **{score}**!" for i, (user, score) in enumerate(scores))
            await chat.send_message(resp, creator)
        elif s[0] == "end":
            if not trivia_game:
                await chat.send_message("Error: Game not started! Use `@latexbot trivia start [category] [difficulty] [type]` to start a game.", creator)
                return
            # Get the message object so we can check if the user is authorized
            msg = (await pyryver.retry_until_available(chat.get_message_from_id, msg_id, timeout=5.0))[0]
            if msg.get_author_id() == trivia_game.host or await is_authorized(chat, await msg.get_author(), ACCESS_LEVEL_FORUM_ADMIN):
                # Display the scores
                scores = sorted(trivia_game.scores.items(), key=lambda x: x[1], reverse=True)
                if not scores:
                    await chat.send_message("Game ended. No questions were answered, so there are no scores to display.", creator)
                    # Clean up
                    await end_game()
                    return

                # Handle multiple people with the same score
                winners = []
                winning_score = scores[0][1]
                # Find all users with the same score as the winner
                for user, score in scores:
                    if score == winning_score:
                        winners.append(user)
                    else:
                        break
                resp = "The game has ended. "
                # Single winner
                if len(winners) == 1:
                    resp += f"**{chat.get_ryver().get_user(id=winners[0]).get_name()}** is the winner with a score of **{winning_score}**!\n\nFull scoreboard:\n"
                # Multiple winners
                else:
                    resp += f"**{', '.join(chat.get_ryver().get_user(id=winner).get_name() for winner in winners)}** are the winners, tying with a score of **{winning_score}**!\n\nFull scoreboard:\n"
                resp += "\n".join(f"{i + 1}. **{chat.get_ryver().get_user(id=user).get_name()}** with a score of **{score}**!" for i, (user, score) in enumerate(scores))
                await chat.send_message(resp, creator)
                # Clean up
                await end_game()
            else:
                await chat.send_message("Error: Only the one who started the game or a Forum Admin or higher may end the game!", creator)
        else:
            await chat.send_message("Invalid sub-command! Please see `@latexbot help trivia` for all valid sub-commands.", creator)


async def _deleteMessages(chat: pyryver.Chat, msg_id: str, s: str):
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
    await (await pyryver.retry_until_available(chat.get_message_from_id, msg_id, timeout=5.0))[0].delete()


async def _moveMessages(chat: pyryver.Chat, msg_id: str, s: str):
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


async def _countMessagesSince(chat: pyryver.Chat, msg_id: str, s: str):
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


async def _roles(chat: pyryver.Chat, msg_id: str, s: str):
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
    if not org.roles:
        await chat.send_message(f"There are currently no roles.", creator)
    if s == "":
        if org.roles:
            roles_str = "\n".join(
                f"**{role}**: {', '.join(usernames)}" for role, usernames in org.roles.items())
            await chat.send_message(f"All roles:\n{roles_str}", creator)
    else:
        # A mention
        if s.startswith("@"):
            s = s[1:]
        # A role
        if s in org.roles:
            users = "\n".join(org.roles[s])
            await chat.send_message(f"These users have the role '{s}':\n{users}", creator)
        # Check if it's a username
        elif chat.get_ryver().get_user(username=s):
            roles = "\n".join(role for role, usernames in org.roles.items() if s in usernames)
            if roles:
                await chat.send_message(
                    f"User '{s}' has the following roles:\n{roles}", creator)
            else:
                await chat.send_message(f"User '{s}' has no roles.", creator)
        else:
            await chat.send_message(f"'{s}' is not a valid username or role name.", creator)


async def _addToRole(chat: pyryver.Chat, msg_id: str, s: str):
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
    args = s.split()
    if len(args) < 2:
        await chat.send_message("Invalid syntax.", creator)
        return

    roles = [r.strip() for r in args[0].split(",")]
    usernames = [username[1:] if username.startswith(
        "@") else username for username in args[1:]]

    for role in roles:
        if " " in role or "," in role:
            await chat.send_message(
                f"Invalid role: {role}. Role names must not contain spaces or commas. Skipping...", creator)
            continue
        # Role already exists
        if role in org.roles:
            for username in usernames:
                if username in org.roles[role]:
                    await chat.send_message(
                        f"Warning: User '{username}' already has role '{role}'.", creator)
                else:
                    org.roles[role].append(username)
        else:
            org.roles[role] = usernames
    org.save_roles()

    await chat.send_message("Operation successful.", creator)


async def _removeFromRole(chat: pyryver.Chat, msg_id: str, s: str):
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
        await chat.send_message("Invalid syntax.", creator)
        return

    roles = [r.strip() for r in args[0].split(",")]
    usernames = [username[1:] if username.startswith(
        "@") else username for username in args[1:]]

    for role in roles:
        if not role in org.roles:
            await chat.send_message(
                f"Error: The role {role} does not exist. Skipping...", creator)
            continue
        
        for username in usernames:
            if not username in org.roles[role]:
                await chat.send_message(
                    f"Warning: User {username} does not have the role {role}.", creator)
                continue
            org.roles[role].remove(username)

        # Delete empty roles
        if len(org.roles[role]) == 0:
            org.roles.pop(role)
    org.save_roles()

    await chat.send_message("Operation successful.", creator)


async def _deleteRole(chat: pyryver.Chat, msg_id: str, s: str):
    """
    Completely delete a role, removing all users from that role.

    Roles are in a comma-separated list, e.g. Foo,Bar,Baz.
    ---
    group: Roles Commands
    syntax: <roles>
    ---
    > `@latexbot deleteRole Foo` - Remove everyone from the role Foo and delete it.
    """
    if s == "":
        await chat.send_message("Error: Please specify at least one role!", creator)
        return
    roles = [r.strip() for r in s.split(",")]
    for role in roles:
        try:
            org.roles.pop(role)
        except KeyError:
            await chat.send_message(f"Error: The role {role} does not exist. Skipping...", creator)
    org.save_roles()

    await chat.send_message("Operation successful.", creator)


async def _exportRoles(chat: pyryver.Chat, msg_id: str, s: str):
    """
    Export roles data as a JSON. 

    If the data is less than 1k characters long, it will be sent as a chat message.
    Otherwise it will be sent as a file attachment.
    ---
    group: Roles Commands
    syntax:
    """
    data = json.dumps(org.roles.to_dict(), indent=2)
    if len(data) < 1000:
        await chat.send_message(f"```json\n{data}\n```", creator)
    else:
        file = (await chat.get_ryver().upload_file("roles.json", data, "application/json")).get_file()
        await chat.send_message(f"Roles: [{file.get_name()}]({file.get_url()})", creator)


async def _importRoles(chat: pyryver.Chat, msg_id: str, s: str):
    """
    Import JSON roles data from the message, or from a file attachment.

    If a file is attached to the message, the roles will always be imported from the file.
    ---
    group: Roles Commands
    syntax: <data|fileattachment>
    ---
    > `@latexbot importRoles {}` - Clear all roles.
    """
    msg = (await pyryver.retry_until_available(chat.get_message_from_id, msg_id, timeout=5.0))[0]
    file = msg.get_attached_file()
    if file:
        # Get the actual contents
        try:
            data = (await file.download_data()).decode("utf-8")
        except aiohttp.ClientResponseError as e:
            await chat.send_message(f"Error while trying to GET file attachment: {e}", creator)
            return
        except UnicodeDecodeError as e:
            await chat.send_message(f"File needs to be encoded with utf-8! The following decode error occurred: {e}", creator)
            return
    else:
        data = s
    
    try:
        org.roles = CaseInsensitiveDict(json.loads(data))
        org.save_roles()
        await chat.send_message(
            f"Operation successful. Use `@latexbot roles` to view the updated roles.", creator)
    except json.JSONDecodeError as e:
        await chat.send_message(f"Error decoding JSON: {e}", creator)


async def _events(chat: pyryver.Chat, msg_id: str, s: str):
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
        await chat.send_message(f"Error: Invalid number.", creator)
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
        resp = "---------- Ongoing Events ----------"
        for evt in ongoing:
            event, start, end, has_time = evt
            # The day number of the event
            day = caldays_diff(now, start) + 1
            # If the event does not have a time, then don't include the time
            start_str = datetime.strftime(start, DATETIME_DISPLAY_FORMAT if has_time else DATE_DISPLAY_FORMAT)
            end_str = datetime.strftime(end, DATETIME_DISPLAY_FORMAT if has_time else DATE_DISPLAY_FORMAT)
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
            day = caldays_diff(start, now)
            # If the event does not have a time, then don't include the time
            start_str = datetime.strftime(start, DATETIME_DISPLAY_FORMAT if has_time else DATE_DISPLAY_FORMAT)
            end_str = datetime.strftime(end, DATETIME_DISPLAY_FORMAT if has_time else DATE_DISPLAY_FORMAT)
            resp += f"\n# *{day}* day(s) until {event['summary']} (*{start_str}* to *{end_str}*)"
            if "description" in event and event["description"] != "":
                # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
                resp += f"\u200B:\n{markdownify(event['description'])}"
    else:
        resp += "***No upcoming events at the moment.***"

    await chat.send_message(resp, creator)


async def _quickAddEvent(chat: pyryver.Chat, msg_id: str, s: str):
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
    await chat.send_message(f"Created event {event['summary']} (**{start_str}** to **{end_str}**).\nLink: {event['htmlLink']}", creator)


async def _addEvent(chat: pyryver.Chat, msg_id: str, s: str):
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
        await chat.send_message(f"Invalid syntax: {e}", creator)
        return  
    if len(s) != 3 and len(s) != 5:
        await chat.send_message("Error: Invalid syntax. Check `@latexbot help addEvent` for help. You may have to use quotes if any of the parameters contain spaces.", creator)
        return
    
    # No times specified
    if len(s) == 3:
        start = tryparse_datetime(s[1], ALL_DATE_FORMATS)
        if not start:
            await chat.send_message(f"Error: The date {s[1]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", creator)
            return
        end = tryparse_datetime(s[2], ALL_DATE_FORMATS)
        if not end:
            await chat.send_message(f"Error: The date {s[2]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", creator)
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
            await chat.send_message(f"Error: The date {s[1]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", creator)
            return
        start_time = tryparse_datetime(s[2], ALL_TIME_FORMATS)
        if not start_time:
            await chat.send_message(f"Error: The time {s[2]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", creator)
            return

        end_date = tryparse_datetime(s[3], ALL_DATE_FORMATS)
        if not end_date:
            await chat.send_message(f"Error: The date {s[3]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", creator)
            return
        end_time = tryparse_datetime(s[4], ALL_TIME_FORMATS)
        if not end_time:
            await chat.send_message(f"Error: The time {s[4]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", creator)
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
        await chat.send_message(f"Created event {event['summary']} (**{start_str}** to **{end_str}**).\nLink: {event['htmlLink']}", creator)
    else:
        # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
        await chat.send_message(f"Created event {event['summary']} (**{start_str}** to **{end_str}**)\u200B:\n{markdownify(event['description'])}\n\nLink: {event['htmlLink']}", creator)


async def _deleteEvent(chat: pyryver.Chat, msg_id: str, s: str):
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
        await chat.send_message(f"Deleted event {matched_event['summary']} (**{start_str}** to **{end_str}**).", creator)
    else:
        await chat.send_message(f"Error: No event matches that name.", creator)


async def _setDailyMessageTime(chat: pyryver.Chat, msg_id: str, s: str):
    """
    Set the time daily messages are sent each day or turn them on/off.

    The time must be in the "HH:MM" format (24-hour clock).
    Use the argument "off" to turn daily messages off.
    ---
    group: Events/Google Calendar Commands
    syntax: <time|off>
    ---
    > `@latexbot setDailyMessageTime 00:00` - Set daily messages to be sent at 12am each day.
    > `@latexbot setDailyMessageTime off` - Turn off daily messages.
    """
    if s.lower() == "off":
        org.daily_message_time = None
    else:
        # Try parse to ensure validity
        try:
            datetime.strptime(s, "%H:%M")
        except ValueError:
            await chat.send_message("Invalid time format.", creator)
            return
        org.daily_message_time = s
    
    # Schedule or unschedule the daily message task
    if org.daily_message_time:
        schedule_daily_message()
    else:
        if daily_message_task:
            daily_message_task.cancel()
    org.save_config()
    if org.daily_message_time:
        await chat.send_message(f"Messages will now be sent at {s} daily.", creator)
    else:
        await chat.send_message(f"Messages have been disabled.", creator)


async def _setEnabled(chat: pyryver.Chat, msg_id: str, s: str):
    """
    Enable or disable me.
    ---
    group: Developer Commands
    syntax: true|false
    """
    # The only way this actually gets called is if the user passed neither "true" nor "false"
    await chat.send_message(f"Invalid option: {s}", creator)


async def _kill(chat: pyryver.Chat, msg_id: str, s: str):
    """
    Kill me (:fearful:).

    With the current settings, I will restart a few minutes after being killed.
    Consider using the disable or sleep commands if you intend to disable me.
    ---
    group: Developer Commands
    syntax:
    """
    await chat.send_message("Goodbye, world.", creator)
    exit()


async def _sleep(chat: pyryver.Chat, msg_id: str, s: str):
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
        await chat.send_message("Invalid number.", creator)
        return
    await chat.send_message("Good night! :sleeping:", creator)
    time.sleep(secs)
    await chat.send_message("Good morning!", creator)


async def _execute(chat: pyryver.Chat, msg_id: str, s: str):
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
    # Fix print
    global print
    new_print = print
    print = old_print
    # Merge stdout and stderr
    try:
        sys.stdout = io.StringIO()
        sys.stderr = sys.stdout
        exec(s, globals(), locals())
        output = sys.stdout.getvalue()

        await chat.send_message(output, creator)
    except Exception as e:
        await chat.send_message(
            f"An exception has occurred:\n```\n{format_exc()}\n```", creator)
    finally:
        sys.stdout = stdout
        sys.stderr = stderr
        print = new_print


async def _exportConfig(chat: pyryver.Chat, msg_id: str, s: str):
    """
    Export config as a JSON.

    If the data is less than 1k characters long, it will be sent as a chat message.
    Otherwise it will be sent as a file attachment.
    ---
    group: Developer Commands
    syntax:
    """
    data = json.dumps(org.make_config(), indent=2)
    if len(data) < 1000:
        await chat.send_message(f"```json\n{data}\n```", creator)
    else:
        file = (await org.ryver.upload_file("config.json", data, pyryver.File.MIME_TYPE_JSON)).get_file()
        await chat.send_message(f"Config: [{file.get_name()}]({file.get_url()})", creator)


async def _importConfig(chat: pyryver.Chat, msg_id: str, s: str):
    """
    Import config from JSON.

    Note that although it is encouraged, the config JSON does not have to contain all fields.
    If a field is not specified, it will just be left unchanged.

    If a file is attached to this message, the config will always be imported from the file.
    ---
    group: Developer Commands
    syntax: <data>
    """
    msg = (await pyryver.retry_until_available(chat.get_message_from_id, msg_id, timeout=5.0))[0]
    file = msg.get_attached_file()
    if file:
        # Get the actual contents
        try:
            data = (await file.download_data()).decode("utf-8")
        except aiohttp.ClientResponseError as e:
            await chat.send_message(f"Error while trying to GET file attachment: {e}", creator)
            return
        except UnicodeDecodeError as e:
            await chat.send_message(f"File needs to be encoded with utf-8! The following decode error occurred: {e}", creator)
            return
    else:
        data = s
    
    try:
        org.init_config(chat.get_ryver(), json.loads(data))
        generate_help_text(chat.get_ryver())
        org.save_config()
        await chat.send_message(f"Operation successful.", creator)
    except json.JSONDecodeError as e:
        await chat.send_message(f"Error decoding JSON: {e}", creator)


async def _updateChats(chat: pyryver.Chat, msg_id: str, s: str):
    """
    Update the cached list of forums/teams and users.

    As getting organization data takes time, LaTeX Bot caches this information,
    so when org data is updated, such as when a new user joins, or when a new forum is created,
    LaTeX Bot might fail to recognize it. Run this command to fix it.
    ---
    group: Developer Commands
    syntax:
    """
    await chat.get_ryver().load_chats()
    await chat.send_message("Forums/Teams/Users updated.", creator)


async def _alias(chat: pyryver.Chat, msg_id: str, s: str):
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
    if s == "":
        if not org.aliases:
            resp = "No aliases have been created."
        else:
            resp = "All aliases:\n"
            resp += "\n".join(f"* `{alias['from']}` \u2192 `{alias['to']}`" for alias in org.aliases)
        await chat.send_message(resp, creator)
        return

    s = shlex.split(s)
    if s[0] == "create":
        if len(s) != 3:
            await chat.send_message("Invalid syntax. Did you forget the quotes?", creator)
            return
        org.aliases.append({
            "from": s[1],
            "to": s[2],
        })
        generate_help_text(chat.get_ryver())
        org.save_config()
        await chat.send_message(f"Successfully created alias `{s[1]}` \u2192 `{s[2]}`.", creator)
    elif s[0] == "delete":
        if len(s) != 2:
            await chat.send_message("Invalid syntax.", creator)
            return
        
        for i, alias in enumerate(org.aliases):
            if alias["from"] == s[1]:
                del org.aliases[i]
                generate_help_text(chat.get_ryver())
                org.save_config()
                await chat.send_message(f"Successfully deleted alias `{s[1]}`.", creator)
                return
        await chat.send_message(f"Alias not found!", creator)
    else:
        await chat.send_message("Invalid action. Allowed actions are create, delete and no argument (view).", creator)


async def _message(chat: pyryver.Chat, msg_id: str, s: str):
    """
    Send a message to a chat by ID.
    ---
    group: Hidden Commands
    syntax: <id> <message>
    hidden: true
    """
    try:
        i = s.index(" ")
    except ValueError:
        await chat.send_message("Invalid syntax.", creator)
        return
    chat_id = s[:i]
    msg = s[i + 1:]
    try:
        chat_id = int(chat_id)
    except ValueError:
        await chat.send_message("Invalid chat ID.", creator)
        return
    to = chat.get_ryver().get_chat(id=chat_id)
    if to is None:
        await chat.send_message("Chat not found.", creator)
        return
    await to.send_message(msg, creator)


command_processors = {
    "render": [_render, ACCESS_LEVEL_EVERYONE],
    "chem": [_chem, ACCESS_LEVEL_EVERYONE],
    "help": [_help, ACCESS_LEVEL_EVERYONE],
    "ping": [_ping, ACCESS_LEVEL_EVERYONE],
    "whatDoYouThink": [_whatDoYouThink, ACCESS_LEVEL_EVERYONE],
    "xkcd": [_xkcd, ACCESS_LEVEL_EVERYONE],
    "checkiday": [_checkiday, ACCESS_LEVEL_EVERYONE],
    "trivia": [_trivia, ACCESS_LEVEL_EVERYONE],

    "deleteMessages": [_deleteMessages, ACCESS_LEVEL_FORUM_ADMIN],
    "moveMessages": [_moveMessages, ACCESS_LEVEL_FORUM_ADMIN],
    "countMessagesSince": [_countMessagesSince, ACCESS_LEVEL_FORUM_ADMIN],

    "roles": [_roles, ACCESS_LEVEL_EVERYONE],
    "addToRole": [_addToRole, ACCESS_LEVEL_ORG_ADMIN],
    "removeFromRole": [_removeFromRole, ACCESS_LEVEL_ORG_ADMIN],
    "deleteRole": [_deleteRole, ACCESS_LEVEL_ORG_ADMIN],
    "exportRoles": [_exportRoles, ACCESS_LEVEL_EVERYONE],
    "importRoles": [_importRoles, ACCESS_LEVEL_ORG_ADMIN],

    "events": [_events, ACCESS_LEVEL_EVERYONE],
    "addEvent": [_addEvent, ACCESS_LEVEL_ORG_ADMIN],
    "quickAddEvent": [_quickAddEvent, ACCESS_LEVEL_ORG_ADMIN],
    "deleteEvent": [_deleteEvent, ACCESS_LEVEL_ORG_ADMIN],
    "setDailyMessageTime": [_setDailyMessageTime, ACCESS_LEVEL_ORG_ADMIN],

    "setEnabled": [_setEnabled, ACCESS_LEVEL_BOT_ADMIN],
    "kill": [_kill, ACCESS_LEVEL_BOT_ADMIN],
    "sleep": [_sleep, ACCESS_LEVEL_BOT_ADMIN],
    "execute": [_execute, ACCESS_LEVEL_BOT_ADMIN],
    "exportConfig": [_exportConfig, ACCESS_LEVEL_EVERYONE],
    "importConfig": [_importConfig, ACCESS_LEVEL_BOT_ADMIN],
    "updateChats": [_updateChats, ACCESS_LEVEL_FORUM_ADMIN],

    "alias": [_alias, ACCESS_LEVEL_ORG_ADMIN],

    "message": [_message, ACCESS_LEVEL_BOT_ADMIN],
}


################################ OTHER FUNCTIONS ################################


async def daily_message(init_delay: float = 0):
    """
    Send the daily message.
    """
    try:
        await asyncio.sleep(init_delay)
        while True:
            print("Checking today's events...")
            now = current_time()
            events = org.calendar.get_today_events(org.calendar_id, now)
            if not events:
                print("No events today!")
            else:
                resp = "Reminder: These events are happening today:"
                for event in events:
                    start = Calendar.parse_time(event["start"])
                    end = Calendar.parse_time(event["end"])

                    # The event has a time, and it starts today (not already started)
                    if start.tzinfo and start > now:
                        resp += f"\n# {event['summary']} today at *{start.strftime(TIME_DISPLAY_FORMAT)}*"
                    else:
                        # Otherwise format like normal
                        start_str = start.strftime(DATETIME_DISPLAY_FORMAT if start.tzinfo else DATE_DISPLAY_FORMAT)
                        end_str = end.strftime(DATETIME_DISPLAY_FORMAT if end.tzinfo else DATE_DISPLAY_FORMAT)
                        resp += f"\n# {event['summary']} (*{start_str}* to *{end_str}*)"

                    # Add description if there is one
                    if "description" in event and event["description"] != "":
                        # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
                        resp += f"\u200B:{markdownify(event['description'])}"
                await org.announcements_chat.send_message(resp, creator)
                print("Events reminder sent!")
            
            print("Checking for holidays...")
            url = f"https://www.checkiday.com/api/3/?d={current_time().strftime('%Y/%m/%d')}"
            async with aiohttp.request("GET", url) as resp:
                if resp.status != 200:
                    print(f"HTTP error while trying to get holidays: {resp}")
                    data = {
                        "error": f"HTTP error while trying to get holidays: {resp}",
                    }
                else:
                    data = await resp.json()
            if data["error"] != "none":
                await org.messages_chat.send_message(f"Error while trying to check today's holidays: {data['error']}", creator)
            else:
                if data.get("holidays", None):
                    msg = f"Here is a list of all the holidays today:\n"
                    msg += "\n".join(f"* [{holiday['name']}]({holiday['url']})" for holiday in data["holidays"])
                    await org.messages_chat.send_message(msg, creator)
            print("Done checking for holidays.")
            print("Checking for a new xkcd...")
            comic = await xkcd.get_comic()
            if comic['num'] <= org.last_xkcd:
                print(f"No new xkcd found (latest is {comic['num']}).")
            else:
                print(f"New comic found! (#{comic['num']})")
                xkcd_creator = pyryver.Creator(creator.name, XKCD_PROFILE)
                await org.messages_chat.send_message(f"New xkcd!\n\n{xkcd.comic_to_str(comic)}", xkcd_creator)
                # Update xkcd number
                org.last_xkcd = comic['num']
                org.save_config()
            print("Daily message sent.")
            # Sleep for an entire day
            await asyncio.sleep(60 * 60 * 24)
    except asyncio.CancelledError:
        pass


def schedule_daily_message():
    """
    Start the daily message task with the correct delay.
    """
    # Cancel the existing task
    global daily_message_task
    if daily_message_task:
        daily_message_task.cancel()
    
    if not org.daily_message_time:
        print("Daily message not scheduled because time isn't defined.")
        return
    t = datetime.strptime(org.daily_message_time, "%H:%M")
    now = current_time()
    # Get that time, today
    t = datetime.combine(now, t.time(), tzinfo=tz.gettz(org.org_tz))
    # If already passed, get that time the next day
    if t < now:
        t += timedelta(days=1)
    init_delay = (t - now).total_seconds()
    print(f"Daily message re-scheduled, starting after {init_delay} seconds.")
    daily_message_task = asyncio.ensure_future(daily_message(init_delay))


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
                await session.close()
            
            @session.on_chat
            async def _on_chat(msg: typing.Dict[str, str]):
                text = msg["text"]
                # Check the sender
                from_user = ryver.get_user(jid=msg["from"])
                # Ignore messages sent by us
                if from_user.get_username() == os.environ["LATEXBOT_USER"]:
                    return
                
                # Check if this is a DM
                to = ryver.get_chat(jid=msg["to"])
                if isinstance(to, pyryver.User):
                    # For DMs special processing is required
                    # Since we don't want to reply to ourselves, reply to the sender directly instead
                    to = from_user
                    is_dm = True
                else:
                    is_dm = False

                global enabled
                try:
                    preprocessed = preprocess_command(text, is_dm)
                except ValueError as e:
                    # Skip if not enabled
                    if enabled:
                        await to.send_message(f"Cannot process command: {e}", creator)
                    return
                
                if preprocessed:
                    command, args = preprocessed
                    # Processing for re-enabling after disable
                    if command == "setEnabled" and args == "true":
                        # Send the presence change anyways in case it gets messed up
                        await session.send_presence_change(pyryver.RyverWS.PRESENCE_AVAILABLE)
                        if not enabled:
                            enabled = True
                            print(f"Re-enabled by user {from_user.get_name()}!")
                            await to.send_message("I have been re-enabled!", creator)
                        else:
                            await to.send_message("I'm already enabled.", creator)
                        return
                    elif command == "setEnabled" and args == "false" and enabled:
                        enabled = False
                        print(f"Disabled by user {from_user.get_name()}.")
                        await to.send_message("I have been disabled.", creator)
                        await session.send_presence_change(pyryver.RyverWS.PRESENCE_AWAY)
                        return

                    if not enabled:
                        return
                    if is_dm:
                        print(f"DM received from {from_user.get_name()}: {text}")
                    else:
                        print(f"Command received from {from_user.get_name()} to {to.get_name()}: {text}")

                    async with session.typing(to):
                        if command in command_processors:
                            # Check the access level
                            if not await is_authorized(to, from_user, command_processors[command][1]):
                                await to.send_message(get_access_denied_message(), creator)
                                print("Access was denied.")
                            else:
                                try:
                                    result = await command_processors[command][0](to, msg['key'], args)
                                except Exception as e:
                                    print(f"Exception raised:\n{format_exc()}")
                                    await to.send_message(f"An exception occurred while processing the command:\n```{format_exc()}\n```\n\nPlease try again.", creator)
                                print("Command processed.")
                        else:
                            print("Invalid command.")
                            await to.send_message(f"Sorry, I didn't understand what you were asking me to do.", creator)
                # Not a command
                else:
                    # Check for roles
                    if MENTION_REGEX.search(text):
                        # Replace roles and re-send
                        def replace_func(match):
                            group1 = match.group(1)
                            name = match.group(2)
                            if name in org.roles:
                                name = " @".join(org.roles[name])
                            return group1 + name
                        new_text = MENTION_REGEX.sub(replace_func, text)
                        if new_text != text:
                            # Get the message object
                            to = ryver.get_chat(jid=msg["to"])
                            print(f"Role mention received from {from_user.get_name()} to {to.get_name()}: {text}")
                            async with session.typing(to):
                                # Pretend to be the creator
                                msg_creator = pyryver.Creator(
                                    from_user.get_name(), org.user_avatars.get(from_user.get_id(), ""))
                                await to.send_message(new_text, msg_creator)
                                # Can't delete the other person's messages in DMs, so skip
                                if not is_dm:
                                    msg = (await to.get_message_from_id(msg["key"]))[0]
                                    await msg.delete()
            
            @session.on_chat_updated
            async def _on_chat_updated(msg: typing.Dict[str, str]):
                # Sometimes updates are sent for things other than message edits
                if "text" not in msg:
                    return
                await _on_chat(msg)
            
            @session.on_event(pyryver.RyverWS.EVENT_REACTION_ADDED)
            async def _on_reaction_added(msg: typing.Dict[str, str]):
                data = msg["data"]
                # Verify that this is an answer to a trivia question
                if data["type"] == "Entity.ChatMessage" and data["id"] == trivia_question_mid:
                    async with trivia_lock:
                        if trivia_game is not None and not trivia_game.current_question["answered"]:
                            if trivia_game.current_question["type"] == trivia.TriviaSession.TYPE_MULTIPLE_CHOICE:
                                # Try to decode the reaction
                                try:
                                    answer = TRIVIA_NUMBER_EMOJIS.index(data["reaction"])
                                    # Give up if it's invalid
                                    if answer >= len(trivia_game.current_question["answers"]):
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

                            # Refresh the trivia timeout
                            _trivia.refresh_timeout()

                            # Answer the question
                            points = TRIVIA_POINTS[trivia_game.current_question['difficulty']]
                            async with session.typing(trivia_chat):
                                if trivia_game.answer(answer, data["userId"], points):
                                    await trivia_chat.send_message(f"Correct answer! You earned {points} points!", creator)
                                else:
                                    await trivia_chat.send_message(f"Wrong answer! The correct answer was option number {trivia_game.current_question['correct_answer'] + 1}.", creator)
                            

            print("LaTeX Bot is running!")
            await org.home_chat.send_message(f"LaTeX Bot {VERSION} is online! **I now respond to messages in real time!**\n\n{help_text}", creator)

            await session.run_forever()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
