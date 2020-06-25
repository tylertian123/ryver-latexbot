import aiohttp
import typing


JSONDict = typing.Dict[str, typing.Any]


class TheBlueAlliance:
    """
    A class for accessing The Blue Alliance's API with aiohttp.
    """
    
    def __init__(self, read_key: str):
        """
        Construct a new session.

        The read_key is the X-TBA-Auth-Key generated in your account.
        """
        headers = {
            "X-TBA-Auth-Key": read_key
        }
        self._session = aiohttp.ClientSession(headers=headers, raise_for_status=True)
        self._url_prefix = "https://www.thebluealliance.com/api/v3/"
    
    async def close(self):
        """
        Close this session.
        """
        await self._session.close()
    
    async def get_team(self, num: int) -> JSONDict:
        """
        Get basic team info.
        """
        async with self._session.get(f"{self._url_prefix}team/frc{num}") as resp:
            return await resp.json()
    
    async def get_team_events(self, num: int, year: int = None) -> typing.List[JSONDict]:
        """
        Get a team's events for a year or all years.
        """
        url = f"{self._url_prefix}team/frc{num}/events"
        if year is not None:
            url += f"/{year}"
        async with self._session.get(url) as resp:
            return await resp.json()
    
    async def get_team_events_statuses(self, num: int, year: int) -> JSONDict:
        """
        Get a team's events statuses for a year.
        """
        async with self._session.get(f"{self._url_prefix}team/frc{num}/events/{year}/statuses") as resp:
            return await resp.json()
    
    @classmethod
    def format_addr(cls, addr: JSONDict) -> str:
        """
        Format an address.
        """
        addr_str = ""
        if addr.get("address"):
            return addr["address"]
        if addr.get("city"):
            addr_str += addr["city"] + ", "
        if addr.get("state_prov"):
            addr_str += addr["state_prov"] + ", "
        if addr.get("country"):
            addr_str += addr["country"] + ", "
        if addr.get("postal_code"):
            addr_str += addr["postal_code"]
        if addr_str.endswith(", "):
            addr_str = addr_str[:-2]
        return addr_str

    @classmethod
    def format_team(cls, team: JSONDict) -> str:
        """
        Format basic info about a team into a Markdown message.
        """
        msg = f"# Team {team['team_number']} ({team['nickname']})\nAka *{team['name']}*  \n"
        msg += f"From {cls.format_addr(team)}  \nSchool: {team['school_name']}"
        if team["website"]:
            msg += f"  \nWebsite: {team['website']}"
        return msg
    
    @classmethod
    def format_event(cls, event: JSONDict) -> str:
        """
        Format info about an event into a Markdown message.
        """
        msg = f"# {event['name']} ({event['short_name']}, Code: {event['first_event_code']})\n"
        week = f"Week {event['week'] + 1}" if event["week"] is not None else "Offseason"
        msg += f"At {TheBlueAlliance.format_addr(event)} on **{event['start_date']} ({week})**.  \n"
        msg += f"This is a(n) **{event['event_type_string']}** event"
        if event.get("district"):
            msg += f" in the {event['district']['display_name']} district."
        else:
            msg += "."
        return msg
