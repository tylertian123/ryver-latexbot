"""
This module contains marshmallow schemas and classes for objects saved to JSON.
"""

import datetime
import dateutil
import logging
import os
import pyryver
import typing
from marshmallow import fields, decorators, Schema, ValidationError
# TODO: remove latexbot or util dependency
from . import analytics as aly, gcalendar, latexbot, util


logger = logging.getLogger("latexbot")


class ChatField(fields.Field):
    """
    A field containing a pyryver Chat.

    The field will be serialized and deserialized as a string in the form
    [(name|nickname|username|email|id|jid)=][+|@]<forum|team|user>, parseable
    with util.parse_chat_name(). The serialized string specifies the chat by ID.
    """

    def _serialize(self, value: pyryver.Chat, attr: str, obj: typing.Any, **kwargs): # pylint: disable=unused-argument
        return None if value is None else "id=" + str(value.get_id())

    def _deserialize(self, value: str, attr: str, data: typing.Any, **kwargs): # pylint: disable=unused-argument
        if value is None:
            return None
        try:
            return util.parse_chat_name(latexbot.bot.ryver, value)
        except ValueError as e:
            raise ValidationError("Invalid chat or chat not found") from e


class Alias:
    """
    An alias.
    """

    __slots__ = ("from_", "to")

    def __init__(self, from_: str, to: str):
        self.from_ = from_
        self.to = to


class AliasSchema(Schema):
    """
    Schema for an Alias object.
    """

    from_ = fields.Str(required=True, data_key="from")
    to = fields.Str(required=True)

    @decorators.post_load
    def make_obj(self, data, **kwargs): # pylint: disable=unused-argument, no-self-use, missing-function-docstring
        return Alias(**data)


class AccessRule:
    """
    Access rules for a command.
    """

    __slots__ = ("level", "allow_users", "disallow_users", "allow_roles", "disallow_roles")

    def __init__(self, level: int = None, allow_users: typing.List[int] = None, disallow_users: typing.List[int] = None,
                 allow_roles: typing.List[str] = None, disallow_roles: typing.List[str] = None):
        self.level = level
        self.allow_users = allow_users
        self.disallow_users = disallow_users
        self.allow_roles = allow_roles
        self.disallow_roles = disallow_roles

    def __bool__(self) -> bool:
        return self.level is not None or self.allow_users is not None or self.disallow_users is not None or \
            self.allow_roles is not None or self.disallow_roles is not None


class AccessRuleSchema(Schema):
    """
    Schema for an AccessRule object.
    """

    level = fields.Int(required=False)
    allow_users = fields.List(fields.Int(), required=False, data_key="allowUser")
    disallow_users = fields.List(fields.Int(), required=False, data_key="disallowUser")
    allow_roles = fields.List(fields.Str(), required=False, data_key="allowRole")
    disallow_roles = fields.List(fields.Str(), required=False, data_key="disallowRole")

    @decorators.post_load
    def make_obj(self, data, **kwargs): # pylint: disable=unused-argument, no-self-use, missing-function-docstring
        return AccessRule(**data)

    @decorators.post_dump
    def remove_none(self, data, **kwargs): # pylint: disable=unused-argument, no-self-use
        """
        Remove fields that are None since they're optional to reduce the final output.
        """
        return {k: v for k, v in data.items() if v is not None}


class Opinion:
    """
    A LaTeX Bot opinion.
    """

    __slots__ = ("thing", "user", "opinion")

    def __init__(self, thing: typing.List[str], opinion: typing.List[str], user: typing.List[str] = None):
        self.thing = thing
        self.opinion = opinion #NOSONAR
        self.user = user


class OpinionSchema(Schema):
    """
    Schema for an Opinion object.
    """

    thing = fields.List(fields.Str(), required=True)
    user = fields.List(fields.Str(), required=False)
    opinion = fields.List(fields.Str(), required=True)

    @decorators.post_load
    def make_obj(self, data, **kwargs): # pylint: disable=unused-argument, no-self-use, missing-function-docstring
        return Opinion(**data)

    @decorators.post_dump
    def remove_none(self, data, **kwargs): # pylint: disable=unused-argument, no-self-use
        """
        Remove fields that are None since they're optional to reduce the final output.
        """
        return {k: v for k, v in data.items() if v is not None}


class Config:
    """
    An object holding LaTeX Bot's config.
    """

    __slots__ = ("admins", "tz_str", "frc_team", "welcome_message",
                 "access_denied_messages", "wdyt_yes_messages", "wdyt_no_messages",
                 "home_chat", "announcements_chat", "messages_chat", "reddit_chat",
                 "gh_updates_chat", "gh_issues_chat", "gh_users_map",
                 "calendar_id", "daily_message_time", "last_xkcd", "subreddit",
                 "aliases", "access_rules", "macros", "opinions", "command_prefixes",
                 "tzinfo", "calendar", "read_only_chats")

    def __init__(self, admins: typing.List[int], tz_str: str, frc_team: int, welcome_message: str, #NOSONAR
                 access_denied_messages: typing.List[str], wdyt_yes_messages: typing.List[str],
                 wdyt_no_messages: typing.List[str], home_chat: pyryver.Chat, announcements_chat: pyryver.Chat,
                 messages_chat: pyryver.Chat, reddit_chat: pyryver.Chat, gh_updates_chat: pyryver.Chat,
                 gh_issues_chat: pyryver.Chat, gh_users_map: typing.Dict[str, str], calendar_id: str,
                 daily_message_time: datetime.time, last_xkcd: int, subreddit: str, aliases: typing.List[Alias],
                 access_rules: typing.Dict[str, AccessRule], macros: typing.Dict[str, str],
                 opinions: typing.List[Opinion], command_prefixes: typing.List[str],
                 read_only_chats: typing.Dict[pyryver.Chat, typing.List[str]]):
        self.admins = admins
        self.tz_str = tz_str
        self.frc_team = frc_team
        self.welcome_message = welcome_message
        self.access_denied_messages = access_denied_messages
        self.wdyt_yes_messages = wdyt_yes_messages
        self.wdyt_no_messages = wdyt_no_messages
        self.home_chat = home_chat
        self.announcements_chat = announcements_chat
        self.messages_chat = messages_chat
        self.reddit_chat = reddit_chat
        self.gh_updates_chat = gh_updates_chat
        self.gh_issues_chat = gh_issues_chat
        self.gh_users_map = gh_users_map
        self.calendar_id = calendar_id
        self.daily_message_time = daily_message_time
        self.last_xkcd = last_xkcd
        self.subreddit = subreddit
        self.aliases = aliases
        self.access_rules = access_rules
        self.macros = macros
        self.opinions = opinions
        self.command_prefixes = command_prefixes
        self.read_only_chats = read_only_chats
        # Fields not directly loaded from JSON
        self.tzinfo = dateutil.tz.gettz(self.tz_str)
        # Handle the case of an empty env var
        cal_cred = os.environ.get("LATEXBOT_CALENDAR_CREDENTIALS") or "calendar_credentials.json"
        if not os.path.exists(cal_cred):
            logger.warning(f"Calendar credentials file does not exist: {cal_cred}")
            self.calendar = None
        else:
            self.calendar = gcalendar.Calendar(cal_cred, self.calendar_id)


class ConfigSchema(Schema):
    """
    Schema for the Config object.
    """
    # Misc config
    admins = fields.List(fields.Int(), missing=[])
    tz_str = fields.Str(missing=None, allow_none=True, data_key="organizationTimeZone")
    frc_team = fields.Int(missing=None, allow_none=True, data_key="frcTeam")
    welcome_message = fields.Str(missing=None, allow_none=True, data_key="welcomeMessage")
    access_denied_messages = fields.List(fields.Str(), missing=None, allow_none=True, data_key="accessDeniedMessages")
    wdyt_yes_messages = fields.List(fields.Str(), missing=None, allow_none=True, data_key="wdytYesMessages")
    wdyt_no_messages = fields.List(fields.Str(), missing=None, allow_none=True, data_key="wdytNoMessages")
    # Chats
    home_chat = ChatField(missing=None, allow_none=True, data_key="homeChat")
    announcements_chat = ChatField(missing=None, allow_none=True, data_key="announcementsChat")
    messages_chat = ChatField(missing=None, allow_none=True, data_key="messagesChat")
    reddit_chat = ChatField(missing=None, allow_none=True, data_key="redditChat")
    # GitHub integration
    gh_updates_chat = ChatField(missing=None, allow_none=True, data_key="ghUpdatesChat")
    gh_issues_chat = ChatField(missing=None, allow_none=True, data_key="ghIssuesChat")
    gh_users_map = fields.Dict(fields.Str(), fields.Str(), missing={}, data_key="ghUsersMap")
    # Google Calendar integration & daily message
    calendar_id = fields.Str(missing=None, allow_none=True, data_key="googleCalendarId")
    daily_message_time = fields.Time(missing=None, allow_none=True, data_key="dailyMessageTime")
    last_xkcd = fields.Int(missing=0, data_key="lastXKCD")
    subreddit = fields.Str(missing=None, allow_none=True)
    # Advanced config
    aliases = fields.List(fields.Nested(AliasSchema), missing=[])
    access_rules = fields.Dict(fields.Str(), fields.Nested(AccessRuleSchema), missing={}, data_key="accessRules")
    macros = fields.Dict(fields.Str(), fields.Str(), missing={})
    opinions = fields.List(fields.Nested(OpinionSchema), missing=[])
    command_prefixes = fields.List(fields.Str(), missing=["@latexbot "], data_key="commandPrefixes")
    read_only_chats = fields.Dict(ChatField, fields.List(fields.Str()), missing={}, data_key="readOnlyChats")

    @decorators.validates("tz_str")
    def validate_tz(self, value: str): # pylint: disable=no-self-use, missing-function-docstring
        if dateutil.tz.gettz(value) is None:
            raise ValidationError("Invalid timezone: " + value)

    @decorators.post_load
    def make_obj(self, data, **kwargs): # pylint: disable=unused-argument, no-self-use, missing-function-docstring
        return Config(**data)


class Keyword:
    """
    An object holding info about a single keyword for a keyword watch.
    """

    __slots__ = ("keyword", "whole_word", "match_case")

    def __init__(self, keyword: str, whole_word: bool, match_case: bool):
        self.keyword = keyword #NOSONAR
        self.whole_word = whole_word
        self.match_case = match_case


class KeywordSchema(Schema):
    """
    Schema for the Keyword object.
    """

    keyword = fields.Str(required=True)
    whole_word = fields.Bool(missing=False, data_key="wholeWord")
    match_case = fields.Bool(missing=False, data_key="matchCase")

    @decorators.post_load
    def make_obj(self, data, **kwargs): # pylint: disable=unused-argument, no-self-use, missing-function-docstring
        return Keyword(**data)


class KeywordWatch:
    """
    An object holding info about a user's keyword watch settings.
    """

    __slots__ = ("on", "activity_timeout", "keywords", "suppressed")

    def __init__(self, on: bool, activity_timeout: float, keywords: typing.List[Keyword], _suppressed: float = None):
        self.on = on
        self.activity_timeout = activity_timeout
        self.keywords = keywords
        self.suppressed = _suppressed


class KeywordWatchSchema(Schema):
    """
    Schema for the KeywordWatch object.
    """

    on = fields.Bool(missing=True)
    activity_timeout = fields.Float(missing=180.0, data_key="activityTimeout")
    keywords = fields.List(fields.Nested(KeywordSchema), missing=[])
    _suppressed = fields.Float(required=False)

    @decorators.post_load
    def make_obj(self, data, **kwargs): # pylint: disable=unused-argument, no-self-use, missing-function-docstring
        return KeywordWatch(**data)


class AnalyticsSchema(Schema):
    """
    Schema for the Analytics object (defined in analytics.py).
    """

    command_usage = fields.Dict(fields.Str(), fields.Dict(fields.Int(), fields.Int()), missing={}, data_key="commandUsage")
    message_activity = fields.Dict(fields.Int(), fields.Int(), missing={}, data_key="messageActivity")
    shutdowns = fields.List(fields.Int(), missing=[])

    @decorators.post_load
    def make_obj(self, data, **kwargs): # pylint: disable=unused-argument, no-self-use, missing-function-docstring
        return aly.Analytics(**data)

config = ConfigSchema()
keyword_watch = KeywordWatchSchema()
analytics = AnalyticsSchema()
