import dateutil.parser
import typing
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

class Calendar:
    """
    A class to help with working with Google Calendar.
    """

    def __init__(self, cred_file: str):
        self.cred = service_account.Credentials.from_service_account_file(cred_file, scopes=SCOPES)
        self.service = build("calendar", "v3", credentials=self.cred)
    
    def get_upcoming_events(self, calendar_id: str, maxResults=None) -> typing.List:
        """
        Get a list of ongoing and upcoming events.
        """
        now = datetime.utcnow()
        timeMin = now.isoformat() + "Z"
        results = self.service.events().list(calendarId=calendar_id, timeMin=timeMin, maxResults=maxResults, singleEvents=True, orderBy='startTime').execute()
        return results.get("items", [])
    
    def get_today_events(self, calendar_id: str, now: datetime, maxResults=None) -> typing.List:
        """
        Get a list of events currently ongoing or starting today.

        now must contain timezone info.
        """
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        next_day = today + timedelta(days=1)
        # Timezone info already exists, so no need to add "Z"
        timeMin = today.isoformat()
        timeMax = next_day.isoformat()
        results = self.service.events().list(calendarId=calendar_id, timeMin=timeMin, timeMax=timeMax, maxResults=maxResults, singleEvents=True, orderBy='startTime').execute()
        return results.get("items", [])
    
    def quick_add(self, calendar_id: str, text) -> typing.Dict:
        """
        Use quickAdd to add an event based on a simple text string.
        """
        return self.service.events().quickAdd(calendarId=calendar_id, text=text).execute()
    
    def add_event(self, calendar_id: str, event) -> typing.Dict:
        """
        Add an event.
        """
        return self.service.events().insert(calendarId=calendar_id, body=event).execute()
    
    def remove_event(self, calendar_id: str, event_id: str):
        """
        Remove an event.
        """
        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

    
    @staticmethod
    def parse_time(t: typing.Dict) -> datetime:
        if "date" in t:
            return datetime.strptime(t["date"], "%Y-%m-%d")
        else:
            return dateutil.parser.parse(t["dateTime"])
