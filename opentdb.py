"""
Uses the Open Trivia Database https://opentdb.com/ to retrieve trivia questions.
"""

import aiohttp
import asyncio
import html
import typing

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


async def retrieve_token() -> str:
    """
    Retrieve a session token. 

    Session tokens are used to ensure no duplicate questions are retrieved.
    They expire after 6 hours of inactivity.
    """
    url = "https://opentdb.com/api_token.php?command=request"
    async with aiohttp.request("GET", url) as resp:
        resp.raise_for_status()
        data = await resp.json()
    if data["response_code"] != OpenTDBError.CODE_SUCCESS:
        raise OpenTDBError(f"Bad response code: {data['response_code']}", data["response_code"])
    return data["token"]


async def reset_token(token: str) -> str:
    """
    Reset a session token.
    """
    url = f"https://opentdb.com/api_token.php?command=reset&token={token}"
    async with aiohttp.request("GET", url) as resp:
        resp.raise_for_status()
        data = await resp.json()
    if data["response_code"] != OpenTDBError.CODE_SUCCESS:
        raise OpenTDBError(f"Bad response code: {data['response_code']}", data["response_code"])


async def get_categories() -> typing.List[typing.Dict[str, typing.Any]]:
    """
    Get all the categories and their IDs.
    """
    url = "https://opentdb.com/api_category.php"
    async with aiohttp.request("GET", url) as resp:
        resp.raise_for_status()
        data = await resp.json()
    if data["response_code"] != OpenTDBError.CODE_SUCCESS:
        raise OpenTDBError(f"Bad response code: {data['response_code']}", data["response_code"])
    return data["trivia_categories"]


DIFFICULTY_EASY = "easy"
DIFFICULTY_MEDIUM = "medium"
DIFFICULTY_HARD = "hard"

TYPE_MULTIPLE_CHOICE = "multiple"
TYPE_TRUE_OR_FALSE = "boolean"

async def get_questions(amount: int, category: int = None, difficulty: str = None, type: str = None, token: str = None):
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
    if token is not None:
        token += f"&token={token}"
    async with aiohttp.request("GET", url) as resp:
        resp.raise_for_status()
        data = await resp.json()
    if data["response_code"] != OpenTDBError.CODE_SUCCESS:
        raise OpenTDBError(f"Bad response code: {data['response_code']}", data["response_code"])
    # Unescape
    for result in data["results"]:
        result["question"] = html.unescape(result["question"])
    return data["results"]
