"""
Uses the Open Trivia Database https://opentdb.com/ for a game of trivia.
"""

import aiohttp
import asyncio
import html
import pyryver
import random
import typing


CUSTOM_TRIVIA_QUESTIONS = {}


class OpenTDBError(Exception):
    """
    An exception raised when an error occurs when interfacing OpenTDB.

    The code is one of the CODE_ constants.
    """

    CODE_SUCCESS = 0
    CODE_NO_RESULTS = 1
    CODE_INVALID_PARAM = 2
    CODE_TOKEN_NOT_FOUND = 3
    CODE_TOKEN_EMPTY = 4

    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


class TriviaSession:
    """
    A trivia session for interfacing OpenTDB.
    """

    def __init__(self):
        self._session = aiohttp.ClientSession()
        self._token = None
    
    async def start(self, use_token: bool = True):
        """
        Start the session.

        If use_token is true, a token will be retrieved to avoid duplicate
        questions.
        """
        if use_token:
            self._token = await self.retrieve_token()
    
    async def close(self):
        """
        Close the session.
        """
        await self._session.close()

    async def retrieve_token(self) -> str:
        """
        Retrieve a session token. 

        Session tokens are used to ensure no duplicate questions are retrieved.
        They expire after 6 hours of inactivity.
        """
        url = "https://opentdb.com/api_token.php?command=request"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        if data["response_code"] != OpenTDBError.CODE_SUCCESS:
            raise OpenTDBError(f"Bad response code: {data['response_code']}", data["response_code"])
        return data["token"]

    async def reset_token(self):
        """
        Reset the session token.
        """
        if self._token is None:
            return
        url = f"https://opentdb.com/api_token.php?command=reset&token={self._token}"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        if data["response_code"] != OpenTDBError.CODE_SUCCESS:
            raise OpenTDBError(f"Bad response code: {data['response_code']}", data["response_code"])

    async def get_categories(self) -> typing.List[typing.Dict[str, typing.Any]]:
        """
        Get all the categories and their IDs.
        """
        url = "https://opentdb.com/api_category.php"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        return data["trivia_categories"]

    DIFFICULTY_EASY = "easy"
    DIFFICULTY_MEDIUM = "medium"
    DIFFICULTY_HARD = "hard"

    TYPE_MULTIPLE_CHOICE = "multiple"
    TYPE_TRUE_OR_FALSE = "boolean"

    async def get_questions(self, amount: int, category: int = None, difficulty: str = None, question_type: str = None):
        """
        Get questions.
        """
        url = f"https://opentdb.com/api.php?amount={amount}"
        if category is not None:
            url += f"&category={category}"
        if difficulty is not None:
            url += f"&difficulty={difficulty}"
        if question_type is not None:
            url += f"&type={question_type}"
        if self._token is not None:
            url += f"&token={self._token}"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        if data["response_code"] != OpenTDBError.CODE_SUCCESS:
            raise OpenTDBError(f"Bad response code: {data['response_code']}", data["response_code"])
        # Unescape
        for result in data["results"]:
            result["question"] = html.unescape(result["question"])
        return data["results"]


class CustomTriviaSession:
    """
    A trivia session using only custom questions.
    """
    
    def __init__(self):
        self._questions = []
        self._index = 0
        self._category = None
    
    def start(self, category: str = None):
        """
        Start the session.

        If the category is not specified, all the custom questions will be used.
        """
        try:
            if category is not None:
                self._questions = CUSTOM_TRIVIA_QUESTIONS[category]["questions"]
            else:
                self._questions = []
                for v in CUSTOM_TRIVIA_QUESTIONS.values():
                    self._questions.extend(v["questions"])
        except KeyError:
            raise ValueError("Error trying to load questions")
        self._index = 0
        random.shuffle(self._questions)
    
    def get_question(self, difficulty: str = None, question_type: str = None):
        """
        Get a question.
        """
        while self._index < len(self._questions):
            question = self._questions[self._index]
            self._index += 1
            if difficulty is not None and question["difficulty"] != difficulty:
                continue
            if question_type is not None and question["type"] != question_type:
                continue
            return question
        raise OpenTDBError("Ran out of questions!", OpenTDBError.CODE_TOKEN_EMPTY)


class TriviaGame:
    """
    A game of trivia.
    """

    def __init__(self):
        self._session = None
        self._custom_session = None

        self.category = None
        self.difficulty = None
        self.question_type = None

        self.current_question = None
        self.host = None
        self.scores = {}
    
    async def start(self, host: typing.Any = None):
        """
        Start the game.

        If a host is specified, it will be stored as self.host.
        The host serves no other purpose.
        """
        # Custom category
        if isinstance(self.category, str):
            self._custom_session = CustomTriviaSession()
            if self.category == "custom":
                self._custom_session.start()
            else:
                self._custom_session.start(self.category)
        else:
            self._session = TriviaSession()
            await self._session.start()
        if host is not None:
            self.host = host
    
    async def end(self):
        """
        End the game.
        """
        if self._session:
            await self._session.close()
            self._session = None
        self._custom_session = None
    
    def set_category(self, category: typing.Union[int, str]):
        """
        Set the category.

        If the category is a string, then it is assumed to be a custom category.
        If the category is "custom", then all custom categories will be included.
        """
        self.category = category
    
    def set_difficulty(self, difficulty: str):
        """
        Set the difficulty.
        """
        self.difficulty = difficulty
    
    def set_type(self, question_type: str):
        """
        Set the question type (True/False or Multiple Choice).
        """
        self.question_type = question_type
    
    async def get_categories(self) -> typing.List[typing.Dict[str, typing.Any]]:
        """
        Get all the categories and their IDs.
        """
        return await self._session.get_categories()

    async def next_question(self):
        """
        Move on to the next question.
        
        This changes the value of self.current_question. 
        The current question has the following format:
        - "category": The category (str)
        - "type": The question type (str, one of TriviaSession.TYPE_TRUE_OR_FALSE or TriviaSession.TYPE_MULTIPLE_CHOICE)
        - "difficulty": The question difficulty (str, one of the TriviaSession.DIFFICULTY_ constants)
        - "question": The question (str)
        - "answers": A list of possible answers ([str])
        - "correct_answer": The index of the correct answer in the list (int)
        - "answered": If the question has been answered (bool)
        """
        if isinstance(self.category, str):
            question = self._custom_session.get_question(difficulty=self.difficulty, question_type=self.question_type)
        else:
            question = (await self._session.get_questions(1, category=self.category, difficulty=self.difficulty, question_type=self.question_type))[0]
        
        self.current_question = {
            "category": question["category"],
            "type": question["type"],
            "difficulty": question["difficulty"],
            "question": question["question"],
            "answered": False,
        }
        if question["type"] == TriviaSession.TYPE_TRUE_OR_FALSE:
            self.current_question["answers"] = [
                "True",
                "False"
            ]
            self.current_question["correct_answer"] = 0 if question["correct_answer"] == "True" else 1
        else:
            answers = question["incorrect_answers"]
            random.shuffle(answers)
            # Insert the correct answer at a random index
            index = random.randint(0, len(answers))
            answers.insert(index, question["correct_answer"])
            self.current_question["answers"] = answers
            self.current_question["correct_answer"] = index
    
    def answer(self, answer: int, user: typing.Any = None, points: int = None) -> bool:
        """
        Answer the current question.

        Returns whether the answer was correct.

        If user and points are provided, it will be added to the scoreboard.

        Note that regardless of whether the question was answered correctly,
        the current question will not be changed.
        """
        if answer >= len(self.current_question["answers"]):
            raise ValueError("Answer out of range")
        
        self.current_question["answered"] = True
        if answer == self.current_question["correct_answer"]:
            if user is not None and points is not None:
                if user in self.scores:
                    self.scores[user] += points
                else:
                    self.scores[user] = points
            return True
        else:
            if user is not None and points is not None and user not in self.scores:
                # still record a score of 0 even if it's wrong
                self.scores[user] = 0
            return False


async def get_categories() -> typing.List[typing.Dict[str, typing.Any]]:
    """
    Get all the categories and their IDs.

    Used to get categories without a game or session object.
    """
    url = "https://opentdb.com/api_category.php"
    async with aiohttp.request("GET", url) as resp:
        resp.raise_for_status()
        data = await resp.json()
    return data["trivia_categories"]


def get_custom_categories() -> typing.List[str]:
    """
    Get all the custom trivia question categories.
    """
    return list(CUSTOM_TRIVIA_QUESTIONS.keys())


def set_custom_trivia_questions(questions):
    """
    Set the custom trivia questions.
    """
    global CUSTOM_TRIVIA_QUESTIONS # pylint: disable=global-statement
    CUSTOM_TRIVIA_QUESTIONS = questions


_T = typing.TypeVar("T")
def order_scores(scores: typing.Dict[_T, int]) -> typing.Dict[int, typing.List[_T]]:
    """
    Order a dict of {player: score} to produce a ranking.

    The ranking will be a dict of {rank: (players, score)}. It will be ordered from first place
    to last place and start at 1.
    """
    if not scores:
        return {}
    scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    rank = 0
    last_score = None
    ranks = {}
    for player, score in scores:
        if last_score is None or score < last_score:
            rank += len(ranks[rank]) if rank in ranks else 1
            last_score = score
            ranks[rank] = ([player], score)
        elif score == last_score:
            ranks[rank][0].append(player)
    return ranks


class LatexBotTriviaGame:
    """
    A game of trivia in latexbot. 
    """

    TRIVIA_NUMBER_EMOJIS = ["one", "two", "three", "four", "five", "six", "seven", "eight"]

    TRIVIA_POINTS = {
        TriviaSession.DIFFICULTY_EASY: 10,
        TriviaSession.DIFFICULTY_MEDIUM: 20,
        TriviaSession.DIFFICULTY_HARD: 30,
    }

    ERR_MSGS = {
        OpenTDBError.CODE_NO_RESULTS: "No results!",
        OpenTDBError.CODE_INVALID_PARAM: "Internal error",
        OpenTDBError.CODE_TOKEN_EMPTY: "Ran out of questions! Please end the game using `@latexbot trivia end`.",
        OpenTDBError.CODE_TOKEN_NOT_FOUND: "Invalid game session! Perhaps the game has expired?",
        OpenTDBError.CODE_SUCCESS: "This should never happen.",
    }

    def __init__(self, chat: pyryver.Chat, game: TriviaGame, msg_creator: pyryver.Creator):
        self.game = game
        self.chat = chat
        self.msg_creator = msg_creator
        self.lock = asyncio.Lock()
        self.timeout_task_handle = None # type: asyncio.Future
        self.question_msg = None # type: pyryver.ChatMessage
        self.ended = False

        self.refresh_timeout()

    async def _timeout(self, delay: float):
        """
        A task that waits for an amount of time and then terminates the game.
        """
        try:
            await asyncio.sleep(delay)
            if not self.ended:
                self.ended = True
                await self.chat.send_message(f"The trivia game started by {self.get_user_name(self.game.host)} has ended due to inactivity.", self.msg_creator)
                await self.end()
        except asyncio.CancelledError:
            pass
    
    def refresh_timeout(self, delay: float = 15 * 60):
        if self.timeout_task_handle is not None:
            self.timeout_task_handle.cancel()
        self.timeout_task_handle = asyncio.create_task(self._timeout(delay))
    
    async def _try_get_next(self) -> bool:
        """
        Try to get the next trivia question while handling errors.

        Returns whether the question was obtained successfully.

        This does not acquire the lock.
        """
        try:
            await self.game.next_question()
            return True
        except OpenTDBError as e:
            err = self.ERR_MSGS[e.code]
            await self.chat.send_message(f"Cannot get next question: {err}", self.msg_creator)
            if e.code == OpenTDBError.CODE_TOKEN_NOT_FOUND:
                # End the session
                await self.chat.send_message(f"Ending invalid session...", self.msg_creator)
                await self.end()
            return False

    async def next_question(self):
        """
        Get the next question or repeat the current question and send it to the chat.
        """
        async with self.lock:
            self.refresh_timeout()

            # Only update the question if already answered
            if self.game.current_question["answered"]:
                # Try to get the next question
                if not await self._try_get_next():
                    return
        
            formatted_question = self.format_question(self.game.current_question)
            # Send the message
            # First send an empty message to get the reactions
            mid = await self.chat.send_message("Loading...", self.msg_creator)
            msg = await pyryver.retry_until_available(self.chat.get_message, mid, timeout=5.0, retry_delay=0)
            if self.game.current_question["type"] == TriviaSession.TYPE_MULTIPLE_CHOICE:
                # Iterate the reactions array until all the options are accounted for
                for _, reaction in zip(self.game.current_question["answers"], self.TRIVIA_NUMBER_EMOJIS):
                    await msg.react(reaction)
            else:
                await msg.react("white_check_mark")
                await msg.react("x")
            await msg.react("trophy")
            await msg.react("fast_forward")
            # Now edit the message to show the actual question contents
            await msg.edit(formatted_question)
            self.question_msg = msg
    
    async def send_scores(self):
        """
        Send the scoreboard to the chat.
        """
        async with self.lock:
            self.refresh_timeout()
            scores = order_scores(self.game.scores)
            if not scores:
                await self.chat.send_message("No scores at the moment. Scores are only recorded after you answer a question.", self.msg_creator)
                return
            # The \\ before the . is to make it not a valid markdown list
            # because you can't skip numbers in markdown lists in Ryver
            resp = "\n".join(f"{rank}\\. **{', '.join(self.get_user_name(player) for player in players)}** with a score of {score}!" for rank, (players, score) in scores.items())
            await self.chat.send_message(resp, self.msg_creator)
    
    async def answer(self, answer: int, user: int):
        """
        Answer the current question.
        """
        async with self.lock:
            self.refresh_timeout()
            points = self.TRIVIA_POINTS[self.game.current_question["difficulty"]]
            name = self.get_user_name(user)
            if self.game.answer(answer, user, points):
                await self.chat.send_message(f"Correct answer! **{name}** earned {points} points!", self.msg_creator)
            else:
                await self.chat.send_message(f"Wrong answer! The correct answer was option number {self.game.current_question['correct_answer'] + 1}. **{name}** did not get any points for that.", self.msg_creator)
    
    async def end(self):
        """
        End the game and clean up.
        """
        async with self.lock:
            self.ended = True
            if self.timeout_task_handle is not None:
                self.timeout_task_handle.cancel()
            await self.game.end()
    
    def get_user_name(self, user_id: int) -> str:
        """
        Get the name of a user specified by ID.
        """
        user = self.chat.get_ryver().get_user(id=user_id)
        return user.get_name() if user is not None else "Unknown User"
    
    @classmethod
    def format_question(cls, question: typing.Dict[str, typing.Any]) -> str:
        """
        Format a trivia question.
        """
        result = f":grey_question: Category: *{question['category']}*, Difficulty: **{question['difficulty']}**\n\n"
        if question['type'] == TriviaSession.TYPE_TRUE_OR_FALSE:
            result += "True or False: "
        result += question["question"]
        answers = "\n".join(f"{i + 1}. {answer}" for i, answer in enumerate(question["answers"]))
        result += "\n" + answers
        return result


import latexbot # nopep8 # pylint: disable=unused-import
