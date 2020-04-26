import dateutil.parser
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

class Calendar:
    """
    A class to help with working with Google Calendar.
    """

    def __init__(self, cred_file):
        self.cred = service_account.Credentials.from_service_account_file(cred_file, scopes=SCOPES)
        self.service = build("calendar", "v3", credentials=self.cred)
    
    def get_upcoming_events(self, calendar_id, maxResults=None):
        """
        Get a list of ongoing and upcoming events.
        """
        now = datetime.utcnow()
        timeMin = now.isoformat() + "Z"
        results = self.service.events().list(calendarId=calendar_id, timeMin=timeMin, maxResults=maxResults, singleEvents=True, orderBy='startTime').execute()
        return results.get("items", None)
    
    def quick_add(self, calendar_id, text):
        """
        Use quickAdd to add an event based on a simple text string.
        """
        return self.service.events().quickAdd(calendarId=calendar_id, text=text).execute()
    
    def add_event(self, calendar_id, event):
        """
        Add an event.
        """
        return self.service.events().insert(calendarId=calendar_id, body=event).execute()

    
    @staticmethod
    def parse_time(t):
        if "date" in t:
            return datetime.strptime(t["date"], "%Y-%m-%d")
        else:
            return dateutil.parser.parse(t["dateTime"])
