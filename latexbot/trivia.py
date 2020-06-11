"""
Uses the Open Trivia Database https://opentdb.com/ for a game of trivia.
"""

import aiohttp
import html
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

    async def get_questions(self, amount: int, category: int = None, difficulty: str = None, type: str = None):
        """
        Get questions.
        """
        url = f"https://opentdb.com/api.php?amount={amount}"
        if category is not None:
            url += f"&category={category}"
        if difficulty is not None:
            url += f"&difficulty={difficulty}"
        if type is not None:
            url += f"&type={type}"
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
    
    def get_question(self, difficulty: str = None, type: str = None):
        """
        Get a question.
        """
        while self._index < len(self._questions):
            question = self._questions[self._index]
            self._index += 1
            if difficulty is not None and question["difficulty"] != difficulty:
                continue
            if type is not None and question["type"] != type:
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
        self.type = None

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
    
    def set_type(self, type: str):
        """
        Set the question type (True/False or Multiple Choice).
        """
        self.type = type
    
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
            question = self._custom_session.get_question(difficulty=self.difficulty, type=self.type)
        else:
            question = (await self._session.get_questions(1, category=self.category, difficulty=self.difficulty, type=self.type))[0]
        
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
    global CUSTOM_TRIVIA_QUESTIONS
    CUSTOM_TRIVIA_QUESTIONS = questions
