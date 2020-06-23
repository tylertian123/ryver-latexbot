# The LaTeX Bot Project

LaTeX Bot is a bot for [Ryver](https://ryver.com/), built for [Team Arctos 6135](https://www.arctos6135.com/)'s organization.

As the name implies, LaTeX Bot's primary function is to render LaTeX (including chemical equations with mhchem).
It also comes with a lot of other neat features:
- Mass-deleting and mass-moving messages for chat moderation
- A Roles system allowing you to mention a group of users at a time
- Google Calendar events integration
- GitHub integration (updates and creating Ryver tasks for Issues and Pull Requests!)
- XKCDs and checkiday.com integration
- Toggleable daily events reminders, new xkcd and holidays checks
- Built-in singleplayer or multiplayer trivia game
- Flexible command access management with Access Levels and Access Rules

For an (almost) complete list of what LaTeX Bot can do, check out `usage_guide.md`.

LaTeX Bot uses [`pyryver`](https://github.com/tylertian123/pyryver) for interfacing with Ryver.

# Building and Running LaTeX Bot

LaTeX Bot is designed to run inside a Docker container. Currently, the hosting of LaTeX Bot is generously provided by [@mincrmatt12](https://github.com/mincrmatt12). 

LaTeX Bot needs access to your organization to run. 
Provide credentials either by creating a `.env` file setting the required environment variables or by directly exporting the variables if you're running it without Docker.
The following env vars are required:
- `LATEXBOT_ORG` - The Ryver organization name, e.g. arctos6135
- `LATEXBOT_USER` - The account to be used by LaTeX Bot
- `LATEXBOT_PASS` - The password for the account

To use Google Calendar integration, LaTeX Bot also needs a `calendar_credentials.json`, which contains the private key for a service account that has access to the calendar.

Use `docker-compose build` to build LaTeX Bot's container, and then use `docker-compose up` to start LaTeX Bot. 
Alternatively, you can also run LaTeX Bot directly using `python3 latexbot.py`.

For more information on setting up LaTeX bot for your own organization, see `deployment_guide.md`.

# Commands
Here is a list of commands supported by LaTeX Bot (auto generated, as of c02100e):

General Commands:
  - `@latexbot render <formula>` - Render a LaTeX formula. 
  - `@latexbot chem <formula>` - Render a chemical formula. 
  - `@latexbot help [command]` - Get a list of all the commands, or details about a command. 
  - `@latexbot ping` - I will respond with 'Pong' if I'm here. 
  - `@latexbot whatDoYouThink <thing>` - Ask my opinion of a thing! 
  - `@latexbot xkcd [number]` - Get the latest xkcd or a specific xkcd by number. 
  - `@latexbot checkiday [date]` - Get a list of today's holidays or holidays for any date. 
  - `@latexbot trivia <sub-command> [args]` - Play a game of trivia. See extended description for details. 

Administrative Commands:
  - `@latexbot deleteMessages [<start>-]<end|count>` - Delete messages.
  - `@latexbot moveMessages [<start>-]<end|count> [(name|nickname|id|jid)=][+]<forum|team>` - Move messages to another forum or team.
  - `@latexbot countMessagesSince <pattern>` - Count the number of messages since the first message that matches a pattern.

Roles Commands:
  - `@latexbot roles [user|role]` - Get information about roles. 
  - `@latexbot addToRole <roles> <people>` - Add people to a role.
  - `@latexbot removeFromRole <roles> <people>` - Remove people from a role.
  - `@latexbot deleteRole <roles>` - Completely delete a role, removing all users from that role.
  - `@latexbot exportRoles` - Export roles data as a JSON. 
  - `@latexbot importRoles <data|fileattachment>` - Import JSON roles data from the message, or from a file attachment.

Events/Google Calendar Commands:
  - `@latexbot events [count]` - Display information about ongoing and upcoming events from Google Calendar. 
  - `@latexbot addEvent <name> <startdate> [starttime] <enddate> [endtime] [description on a new line]` - Add an event to Google Calendar.
  - `@latexbot quickAddEvent <event>` - Add an event to Google Calendar based on a simple text string.
  - `@latexbot deleteEvent <name>` - Delete an event by name from Google Calendar.

Developer Commands:
  - `@latexbot setEnabled true|false` - Enable or disable me.
  - `@latexbot kill` - Kill me (:fearful:).
  - `@latexbot sleep <seconds>` - Put me to sleep.
  - `@latexbot execute <code>` - Execute arbitrary Python code.
  - `@latexbot updateChats` - Update the cached list of forums/teams and users.

Miscellaneous Commands:
  - `@latexbot alias [create|delete] [args]` - Manage aliases.
  - `@latexbot exportConfig` - Export config as a JSON. 
  - `@latexbot importConfig <data>` - Import config from JSON.
  - `@latexbot accessRule [command] [action] [ruletype] [args]` - View or modify access rules.
  - `@latexbot setDailyMessageTime [time]` - Set the time daily messages are sent each day or turn them on/off.
  - `@latexbot dailyMessage` - Send the daily message.


For more details, see `usage_guide.md`.
