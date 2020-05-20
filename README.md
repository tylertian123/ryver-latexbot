# The LaTeX Bot Project

LaTeX Bot is a bot for [Ryver](https://ryver.com/), built for [Team Arctos 6135](https://www.arctos6135.com/)'s organization.

As the name implies, LaTeX Bot's primary function is to render LaTeX.
It also comes with a bunch of other features, like mass-deleting and moving messages, a Roles system, and Google Calendar integration. 

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

# Commands
Here is a list of commands supported by LaTeX Bot (auto generated, as of 6689cee):
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
  - `@latexbot deleteMessages [<start>-]<end|count>` - Delete messages. **Accessible to Forum, Org and Bot Admins only.**
  - `@latexbot moveMessages [<start>-]<end|count> [(name|nickname)=]<forum|team>` - Move messages to another forum or team. **Accessible to Forum, Org and Bot Admins only.**
  - `@latexbot countMessagesSince <pattern>` - Count the number of messages since the first message that matches a pattern. **Accessible to Forum, Org and Bot Admins only.**

Roles Commands:
  - `@latexbot roles [user|role]` - Get information about roles. 
  - `@latexbot addToRole <roles> <people>` - Add people to a role. **Accessible to Org and Bot Admins only.**
  - `@latexbot removeFromRole <roles> <people>` - Remove people from a role. **Accessible to Org and Bot Admins only.**
  - `@latexbot deleteRole <roles>` - Completely delete a role, removing all users from that role. **Accessible to Org and Bot Admins only.**
  - `@latexbot exportRoles` - Export roles data as a JSON. 
  - `@latexbot importRoles <data|fileattachment>` - Import JSON roles data from the message, or from a file attachment. **Accessible to Org and Bot Admins only.**

Events/Google Calendar Commands:
  - `@latexbot events [count]` - Display information about ongoing and upcoming events from Google Calendar. 
  - `@latexbot addEvent <name> <startdate> [starttime] <enddate> [endtime] [description on a new line]` - Add an event to Google Calendar. **Accessible to Org and Bot Admins only.**
  - `@latexbot quickAddEvent <event>` - Add an event to Google Calendar based on a simple text string. **Accessible to Org and Bot Admins only.**
  - `@latexbot deleteEvent <name>` - Delete an event by name from Google Calendar. **Accessible to Org and Bot Admins only.**

Developer Commands:
  - `@latexbot setEnabled true|false` - Enable or disable me. **Accessible to Bot Admins only.**
  - `@latexbot kill` - Kill me (:fearful:). **Accessible to Bot Admins only.**
  - `@latexbot sleep <seconds>` - Put me to sleep. **Accessible to Bot Admins only.**
  - `@latexbot execute <code>` - Execute arbitrary Python code. **Accessible to Bot Admins only.**
  - `@latexbot updateChats` - Update the cached list of forums/teams and users. **Accessible to Forum, Org and Bot Admins only.**

Miscellaneous Commands:
  - `@latexbot alias [create|delete] [args]` - Manage aliases. **Accessible to Org and Bot Admins only.**
  - `@latexbot exportConfig` - Export config as a JSON. 
  - `@latexbot importConfig <data>` - Import config from JSON. **Accessible to Org and Bot Admins only.**
  - `@latexbot setDailyMessageTime <time|off>` - Set the time daily messages are sent each day or turn them on/off. **Accessible to Org and Bot Admins only.**

For more details, see `usage_guide.md`.
