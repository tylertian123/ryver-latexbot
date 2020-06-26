import aiohttp
import typing


JSONObj = typing.Dict[str, typing.Any]
JSONObjList = typing.List[JSONObj]


class TheBlueAlliance:
    """
    A class for accessing The Blue Alliance's API with aiohttp.
    """

    TEAM_URL = "https://www.thebluealliance.com/team/"
    
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

    async def _get_json(self, endpoint: str) -> typing.Union[JSONObj, JSONObjList]:
        """
        Get JSON data from an endpoint.
        """
        async with self._session.get(self._url_prefix + endpoint) as resp:
            return await resp.json()
    
    async def get_team(self, num: int) -> JSONObj:
        """
        Get basic team info.
        """
        return await self._get_json("team/frc" + str(num))
    
    async def get_team_events(self, num: int, year: int = None) -> typing.List[JSONObj]:
        """
        Get a team's events for a year or all years.
        """
        endpoint = f"team/frc{num}/events"
        if year is not None:
            endpoint += f"/{year}"
        return await self._get_json(endpoint)
    
    async def get_team_events_statuses(self, num: int, year: int) -> JSONObj:
        """
        Get a team's events statuses for a year.
        """
        return await self._get_json(f"team/frc{num}/events/{year}/statuses")
    
    async def get_districts(self, year: int) -> JSONObjList:
        """
        Get the districts for a given year.
        """
        return await self._get_json(f"districts/{year}")
    
    async def get_district_rankings(self, district: str) -> JSONObjList:
        """
        Get the rankings for a district for a given year.
        """
        return await self._get_json(f"district/{district}/rankings")
    
    async def get_district_teams(self, district: str) -> JSONObjList:
        """
        Get the teams for a district for a given year.
        """
        return await self._get_json(f"district/{district}/teams")
        
    @classmethod
    def format_addr(cls, addr: JSONObj) -> str:
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
    def format_team(cls, team: JSONObj) -> str:
        """
        Format basic info about a team into a Markdown message.
        """
        msg = f"# [Team {team['team_number']}]({cls.TEAM_URL}{team['team_number']}) ({team['nickname']})\n"
        msg += f"Aka *{team['name']}*  \nFrom {cls.format_addr(team)}  \nSchool: {team['school_name']}"
        if team["website"]:
            msg += f"  \nWebsite: {team['website']}"
        return msg
    
    @classmethod
    def format_event(cls, event: JSONObj) -> str:
        """
        Format info about an event into a Markdown message.
        """
        msg = f"# {event['name']} ({event['short_name']}/{event['first_event_code']}/{event['key']})\n"
        week = f"Week {event['week'] + 1}" if event["week"] is not None else "Offseason"
        msg += f"At {TheBlueAlliance.format_addr(event)} on **{event['start_date']} ({week})**.  \n"
        msg += f"This is a(n) **{event['event_type_string']}** event"
        if event.get("district"):
            msg += f" in the {event['district']['display_name']} district."
        else:
            msg += "."
        return msg
