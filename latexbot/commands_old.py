"""
This module contains command definitions for LaTeX Bot.
"""

import asyncio
import io
import json
import org
import aiohttp # This has to be after import org because of a circular dependencies issue
import os
import pyryver
import random
import render
import shlex
import sys
import time
import trivia
import typing
import xkcd
from caseinsensitivedict import CaseInsensitiveDict
from command import Command
from gcalendar import Calendar
from latexbot_util import *
from markdownify import markdownify
from org import creator
from traceback import format_exc


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
    - `importCustomQuestions` - Import custom questions as a JSON. Accessible to Org Admins or higher.
    - `exportCustomQuestions` - Export custom questions as a JSON. Accessible to Org Admins or higher.

    Here's how a game usually goes:
    - The "host" uses `@latexbot trivia categories` to see all categories (optional)
    - The "host" uses `@latexbot trivia start [category] [difficulty] [type]` to start the game
    - Someone uses `@latexbot trivia question` or `@latexbot trivia next` to get each question
    - The participants answer each question by using reactions or `@latexbot trivia answer <answer>`
    - The participants use `@latexbot trivia scores` to check the scores during the game
    - The "host" uses `@latexbot trivia end` to end the game

    Note that there can only be 1 game going on at a time! 
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
    > `@latexbot trivia importCustomQuestions {}` - Import some custom questions as a JSON.
    > `@latexbot trivia exportCustomQuestions` - Export some custom questions as a JSON.
    """
    if args == "":
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

    async def next_question():
        """
        Get the next question or repeat the current question.
        """
        global trivia_question_mid, trivia_chat
        if not trivia_game:
            await chat.send_message("Error: Game not started! Use `@latexbot trivia start [category] [difficulty] [type]` to start a game.", creator)
            return
        refresh_timeout()
        # Only update the question if already answered
        if trivia_game.current_question["answered"]:
            # Try to get the next question
            if not await trivia_try_get_next():
                return
        formatted_question = format_question(trivia_game.current_question)
        mid = await chat.send_message("Loading...", creator)
        msg = await pyryver.retry_until_available(chat.get_message, mid, timeout=5.0)
        if trivia_game.current_question["type"] == trivia.TriviaSession.TYPE_MULTIPLE_CHOICE:
            # Iterate the reactions array until all the options are accounted for
            for _, reaction in zip(trivia_game.current_question["answers"], TRIVIA_NUMBER_EMOJIS):
                await msg.react(reaction)
        else:
            await msg.react("white_check_mark")
            await msg.react("x")
        await msg.react("trophy")
        await msg.react("fast_forward")
        await msg.edit(formatted_question)
        trivia_question_mid = mid
        trivia_chat = chat
    
    async def send_scores():
        """
        Send the scoreboard to the chat.
        """
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

    # Accessed later in the reactions handler
    _trivia.refresh_timeout = refresh_timeout
    _trivia.next_question = next_question
    _trivia.send_scores = send_scores

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
        if await Command.all_commands["trivia exportCustomQuestions"].is_authorized(chat, user):
            data = json.dumps(trivia.CUSTOM_TRIVIA_QUESTIONS, indent=2)
            if len(data) < 1000:
                await chat.send_message(f"```json\n{data}\n```", creator)
            else:
                file = (await chat.get_ryver().upload_file("trivia.json", data, "application/json")).get_file()
                await chat.send_message(f"Custom Questions: [{file.get_name()}]({file.get_url()})", creator)
        else:
            await chat.send_message("You are not authorized to do that.", creator)
        return
    elif cmd == "importCustomQuestions":
        msg = await pyryver.retry_until_available(chat.get_message, msg_id, timeout=5.0)
        if await Command.all_commands["trivia importCustomQuestions"].is_authorized(chat, await msg.get_author()):
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
                data = sub_args
            
            try:
                trivia.set_custom_trivia_questions(json.loads(data))
                with open(org.TRIVIA_FILE, "w") as f:
                    f.write(data)
                await chat.send_message(f"Operation successful.", creator)
            except json.JSONDecodeError as e:
                await chat.send_message(f"Error decoding JSON: {e}", creator)
        else:
            await chat.send_message("You are not authorized to do that.", creator)
        return

    sub_args = shlex.split(sub_args)
    async with trivia_lock:
        if cmd == "categories":
            # Note: The reason we're not starting from 0 here is because of markdown forcing you to start a list at 1
            categories = "\n".join(f"{i + 1}. {category['name']}" for i, category in enumerate(await trivia.get_categories()))
            custom_categories = trivia.get_custom_categories()
            if custom_categories:
                categories += "\n\n# Custom categories:\n"
                categories += "\n".join(f"* {category}" for category in custom_categories)
                categories += "\n\nCustom categories can only be specified by name. Use 'all' for all regular categories (no custom), or 'custom' for all custom categories (no regular)."
            await chat.send_message(f"# Categories:\n{categories}", creator)
        elif cmd == "start":
            if not (0 <= len(sub_args) <= 3):
                await chat.send_message("Invalid syntax. See `@latexbot help trivia` for details.", creator)
                return
            
            if trivia_game is not None:
                await chat.send_message(f"Error: A game is already ongoing! It was started by {chat.get_ryver().get_user(id=trivia_game.host).get_name()}.", creator)
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
                        await chat.send_message("Category ID out of bounds! Please see `@latexbot trivia categories` for all valid categories.", creator)
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
                            await chat.send_message("Invalid category. Please see `@latexbot trivia categories` for all valid categories.", creator)
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
                    await chat.send_message("Invalid difficulty! Allowed difficulties are 'easy', 'medium', 'hard' or 'all'.", creator)
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
                    await chat.send_message("Invalid question type! Allowed types are 'true/false', 'multiple-choice' or 'all'.", creator)
                    return
            else:
                question_type = None
            
            # Start the game!
            trivia_game = trivia.TriviaGame()
            trivia_game.set_category(category)
            trivia_game.set_difficulty(difficulty)
            trivia_game.set_type(question_type)
            await trivia_game.start(user.get_id())

            await chat.send_message("Game started! Use `@latexbot trivia question` to get the question.", creator)
            refresh_timeout()

            # Try to get the next question, but don't send it
            if not await trivia_try_get_next():
                return
        elif cmd == "question" or cmd == "next":
            await next_question()
        elif cmd == "answer":
            if len(sub_args) != 1:
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
                answer = int(sub_args[0]) - 1
            except ValueError:
                # Is this a true/false question?
                if trivia_game.current_question["type"] == trivia.TriviaSession.TYPE_TRUE_OR_FALSE:
                    answer = sub_args[0].lower()
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
            
            points = TRIVIA_POINTS[trivia_game.current_question['difficulty']]
            author_name = chat.get_ryver().get_user(id=user.get_id()).get_name()

            if trivia_game.answer(answer, user.get_id(), points):
                await chat.send_message(f"Correct answer! **{author_name}** earned {points} points!", creator)
            else:
                await chat.send_message(f"Wrong answer! The correct answer was option number {trivia_game.current_question['correct_answer'] + 1}. **{author_name}** did not get any points for that.", creator)
        elif cmd == "scores":
            await send_scores()
        elif cmd == "end":
            if not trivia_game:
                await chat.send_message("Error: Game not started! Use `@latexbot trivia start [category] [difficulty] [type]` to start a game.", creator)
                return
            # Get the message object so we can check if the user is authorized
            if user.get_id() == trivia_game.host or await Command.all_commands["trivia end"].is_authorized(chat, user):
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


async def command_trivia_on_reaction(bot: "latexbot.LatexBot", ryver: pyryver.Ryver, session: pyryver.RyverWS, data: typing.Dict[str, typing.Any]):
    """
    This coro does extra processing for interfacing trivia with reactions.
    """
    # Verify that this is an answer to a trivia question
    if data["type"] == "Entity.ChatMessage" and data["id"] == trivia_question_mid:
        user = ryver.get_user(id=data["userId"])
        if user.get_username() == os.environ["LATEXBOT_USER"]:
            return
        async with trivia_lock:
            if trivia_game is not None:
                # Scoreboard
                if data["reaction"] == "trophy":
                    await _trivia.send_scores()
                    return

                # Next question
                if data["reaction"] == "fast_forward":
                    if trivia_game.current_question["answered"]:
                        await _trivia.next_question()
                    return

                # Answer
                if trivia_game.current_question["answered"]:
                    return
                # Try to decode the reaction into an answer
                if trivia_game.current_question["type"] == trivia.TriviaSession.TYPE_MULTIPLE_CHOICE:
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
                author_name = ryver.get_user(id=data["userId"]).get_name()
                async with session.typing(trivia_chat):
                    if trivia_game.answer(answer, data["userId"], points):
                        await trivia_chat.send_message(f"Correct answer! **{author_name}** earned {points} points!", creator)
                    else:
                        await trivia_chat.send_message(f"Wrong answer! The correct answer was option number {trivia_game.current_question['correct_answer'] + 1}. **{author_name}** did not get any points for that.", creator)



async def command_setEnabled(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Enable or disable me.
    ---
    group: Developer Commands
    syntax: true|false
    """
    # The only way this actually gets called is if the user passed neither "true" nor "false"
    await chat.send_message(f"Invalid option: {args}", creator)


async def command_kill(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
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
        await chat.send_message("Invalid number.", creator)
        return
    await chat.send_message("Good night! :sleeping:", creator)
    time.sleep(secs)
    await chat.send_message("Good morning!", creator)


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
    > `@latexbot execute chat.send_message("Hello from LaTeX Bot")`
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

        await chat.send_message(output, creator)
    except Exception: # pylint: disable=broad-except
        await chat.send_message(
            f"An exception has occurred:\n```\n{format_exc()}\n```", creator)
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
    await chat.get_ryver().load_chats()
    await chat.send_message("Forums/Teams/Users updated.", creator)


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
        if not org.aliases:
            resp = "No aliases have been created."
        else:
            resp = "All aliases:"
            for alias in org.aliases:
                resp += f"\n* `{alias['from']}` \u2192 `{alias['to']}"
        await chat.send_message(resp, creator)
        return

    args = shlex.split(args)
    if args[0] == "create":
        if len(args) != 3:
            await chat.send_message("Invalid syntax. Did you forget the quotes?", creator)
            return
        org.aliases.append({
            "from": args[1],
            "to": args[2],
        })
        generate_help_text(chat.get_ryver())
        org.save_config()
        await chat.send_message(f"Successfully created alias `{args[1]}` \u2192 `{args[2]}`.", creator)
    elif args[0] == "delete":
        if len(args) != 2:
            await chat.send_message("Invalid syntax.", creator)
            return
        
        for i, alias in enumerate(org.aliases):
            if alias["from"] == args[1]:
                del org.aliases[i]
                generate_help_text(chat.get_ryver())
                org.save_config()
                await chat.send_message(f"Successfully deleted alias `{args[1]}`.", creator)
                return
        await chat.send_message(f"Alias not found!", creator)
    else:
        await chat.send_message("Invalid action. Allowed actions are create, delete and no argument (view).", creator)


async def command_exportConfig(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Export config as a JSON.

    If the data is less than 1k characters long, it will be sent as a chat message.
    Otherwise it will be sent as a file attachment.
    ---
    group: Miscellaneous Commands
    syntax:
    """
    data = json.dumps(org.make_config(), indent=2)
    if len(data) < 1000:
        await chat.send_message(f"```json\n{data}\n```", creator)
    else:
        file = (await chat.get_ryver().upload_file("config.json", data, "application/json")).get_file()
        await chat.send_message(f"Config: [{file.get_name()}]({file.get_url()})", creator)


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
    msg = await pyryver.retry_until_available(chat.get_message, msg_id, timeout=5.0)
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
        data = args
    
    try:
        errs = org.init_config(chat.get_ryver(), json.loads(data))
        if errs:
            log("Error loading config:", *errs, sep="\n")
            await chat.send_message("Error loading config:\n" + "\n".join(errs), creator)
        generate_help_text(chat.get_ryver())
        org.save_config()
        await chat.send_message(f"Operation successful.", creator)
    except json.JSONDecodeError as e:
        await chat.send_message(f"Error decoding JSON: {e}", creator)


async def command_setDailyMessageTime(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Set the time daily messages are sent each day or turn them on/off.

    The time must be in the "HH:MM" format (24-hour clock).
    Use the argument "off" to turn daily messages off.
    ---
    group: Miscellaneous Commands
    syntax: <time|off>
    ---
    > `@latexbot setDailyMessageTime 00:00` - Set daily messages to be sent at 12am each day.
    > `@latexbot setDailyMessageTime off` - Turn off daily messages.
    """
    if args.lower() == "off":
        org.daily_message_time = None
    else:
        # Try parse to ensure validity
        try:
            datetime.strptime(args, "%H:%M")
        except ValueError:
            await chat.send_message("Invalid time format.", creator)
            return
        org.daily_message_time = args
    
    # Schedule or unschedule the daily message task
    if org.daily_message_time:
        org.schedule_daily_message()
    else:
        if org.daily_message_task:
            org.daily_message_task.cancel()
    org.save_config()
    if org.daily_message_time:
        await chat.send_message(f"Messages will now be sent at {args} daily.", creator)
    else:
        await chat.send_message(f"Messages have been disabled.", creator)


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
        await chat.send_message("Invalid syntax.", creator)
        return
    chat_id = args[:i]
    msg = args[i + 1:]
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
        if not org.access_rules:
            await chat.send_message("No access rules were created.", creator)
            return
        resp = "\n\n".join(format_access_rules(command, rule) for command, rule in org.access_rules.items())
        await chat.send_message(resp, creator)
        return
    args = shlex.split(args)
    # Only command name is given - show access rules
    if len(args) == 1:
        if args[0] not in Command.all_commands:
            await chat.send_message(f"Error: Invalid command.", creator)
            return
        if args[0] in org.access_rules:
            await chat.send_message(format_access_rules(args[0], org.access_rules[args[0]]), creator)
        else:
            await chat.send_message(f"No access rules for command {args[0]}.", creator)
    # If both command name and action are given, then rule type and args must be given
    elif len(args) < 3:
        await chat.send_message("Invalid syntax! See `@latexbot help accessRule` for details.", creator)
    else:
        # Verify arguments are correct
        if args[0] not in Command.all_commands:
            await chat.send_message(f"Error: Invalid command.", creator)
            return
        if args[1] == "set":
            if args[2] != "level":
                await chat.send_message(f"Error: Invalid rule type for action `set`: {args[2]}. See `@latexbot help accessRule` for details.", creator)
                return
            if len(args) != 4:
                await chat.send_message(f"Error: The `set` action takes exactly 1 argument.", creator)
                return
            try:
                level = int(args[3])
            except ValueError:
                await chat.send_message(f"Error: Invalid access level: {level}. Access levels must be integers. See `@latexbot help accessRule` for details.", creator)
            # Set the rules
            rules = org.access_rules.get(args[0], {})
            rules["level"] = level
            org.access_rules[args[0]] = rules
        # Combine the two because they're similar
        elif args[1] == "add" or args[1] == "remove":
            # Verify rule type
            if args[2] not in ["allowUser", "disallowUser", "allowRole", "disallowRole"]:
                await chat.send_message(f"Error: Invalid rule type for action `{args[1]}`: {args[2]}. See `@latexbot help accessRule` for details.", creator)
                return
            if len(args) < 4:
                await chat.send_message(f"Error: At least one argument must be supplied for action `{args[1]}`. See `@latexbot help accessRule` for details.", creator)
                return
            # Set the rules
            rules = org.access_rules.get(args[0], {})
            if args[1] == "add":
                # If there are already items, merge the lists
                if args[2] in rules:
                    for arg in args[3:]:
                        # Don't allow duplicates
                        if arg in rules[args[2]]:
                            await chat.send_message(f"Warning: {arg} is already in the list for rule {args[2]}.", creator)
                        else:
                            rules[args[2]].append(arg)
                # Otherwise directly assign
                else:
                    rules[args[2]] = args[3:]
            else:
                if args[2] not in rules:
                    await chat.send_message(f"Error: Rule {args[2]} is not set for command {args[0]}.", creator)
                    return
                # Remove each one
                for arg in args[3:]:
                    if arg not in rules[args[2]]:
                        await chat.send_message(f"Warning: {arg} is not in the list for rule {args[2]}.", creator)
                    else:
                        rules[args[2]].remove(arg)
                # Don't leave empty arrays
                if not rules[args[2]]:
                    rules.pop(args[2])
            # Set the field
            # This is needed in case get() returned the empty dict
            org.access_rules[args[0]] = rules
            # Don't leave empty dicts
            if not org.access_rules[args[0]]:
                org.access_rules.pop(args[0])
        elif args[1] == "delete":
            if len(args) != 3:
                await chat.send_message(f"Error: The `delete` action does not take any arguments.", creator)
                return
            try:
                org.access_rules[args[0]].pop(args[2])
                # Don't leave empty dicts
                if not org.access_rules[args[0]]:
                    org.access_rules.pop(args[0])
            except KeyError:
                await chat.send_message(f"Error: Command {args[0]} does not have rule {args[2]} set.", creator)
                return
        else:
            await chat.send_message(f"Error: Invalid action: {args[1]}. See `@latexbot help accessRule` for details.", creator)
            return
        
        generate_help_text(chat.get_ryver())
        org.save_config()
        await chat.send_message("Operation successful.", creator)


# Define commands
Command("trivia", _trivia, Command.ACCESS_LEVEL_EVERYONE)
# Note: These sub-commands will never get processed normally
# They're here for checking access
Command("trivia importCustomQuestions", None, Command.ACCESS_LEVEL_ORG_ADMIN)
Command("trivia exportCustomQuestions", None, Command.ACCESS_LEVEL_ORG_ADMIN)
Command("trivia end", None, Command.ACCESS_LEVEL_FORUM_ADMIN)

Command("events", _events, Command.ACCESS_LEVEL_EVERYONE)
Command("addEvent", _addEvent, Command.ACCESS_LEVEL_ORG_ADMIN)
Command("quickAddEvent", _quickAddEvent, Command.ACCESS_LEVEL_ORG_ADMIN)
Command("deleteEvent", _deleteEvent, Command.ACCESS_LEVEL_ORG_ADMIN)

Command("setEnabled", _setEnabled, Command.ACCESS_LEVEL_BOT_ADMIN)
Command("kill", _kill, Command.ACCESS_LEVEL_BOT_ADMIN)
Command("sleep", _sleep, Command.ACCESS_LEVEL_BOT_ADMIN)
Command("execute", _execute, Command.ACCESS_LEVEL_BOT_ADMIN)
Command("updateChats", _updateChats, Command.ACCESS_LEVEL_FORUM_ADMIN)

Command("alias", _alias, Command.ACCESS_LEVEL_ORG_ADMIN)
Command("exportConfig", _exportConfig, Command.ACCESS_LEVEL_EVERYONE)
Command("importConfig", _importConfig, Command.ACCESS_LEVEL_ORG_ADMIN)
Command("setDailyMessageTime", _setDailyMessageTime, Command.ACCESS_LEVEL_ORG_ADMIN)
Command("accessRule", _accessRule, Command.ACCESS_LEVEL_ORG_ADMIN)

Command("message", _message, Command.ACCESS_LEVEL_ORG_ADMIN)


# Auto generated
help_text = ""
extended_help_text = {}


def generate_help_text(ryver: pyryver.Ryver):
    global help_text
    help_text = ""
    commands = {}
    for name, command in Command.all_commands.items():
        if command.get_processor() is None:
            # Don't generate a warning for commands with no processors
            continue

        if command.get_processor().__doc__ == "":
            log(f"Warning: Command {name} has no documentation, skipped")
            continue

        try:
            properties = parse_doc(command.get_processor().__doc__)
            if properties.get("hidden", False) == "true":
                # skip hidden commands
                continue

            # Generate syntax string
            syntax = f"`@latexbot {name} {properties['syntax']}`" if properties["syntax"] else f"`@latexbot {name}`"
            # Generate short description
            access_level = Command.ACCESS_LEVEL_STRS.get(command.get_level(), f"**Unknown Access Level: {command.get_level()}.**")
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
            log(f"Error while parsing doc for {name}: {e}")

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
    help_text += "\nClick [here](https://github.com/tylertian123/ryver-latexbot/blob/master/usage_guide.md) for a usage guide."
    if org.aliases:
        help_text += "\n\nCurrent Aliases:\n"
        help_text += "\n".join(f"* `{alias['from']}` \u2192 `{alias['to']}`" for alias in org.aliases)
