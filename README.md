# The LaTeX Bot Project

LaTeX Bot is a bot for [Ryver](https://ryver.com/), built for [Team Arctos 6135](https://www.arctos6135.com/)'s organization.

As the name implies, LaTeX Bot's primary function is to render LaTeX.
It also comes with a bunch of other features, like mass-deleting and moving messages, a Roles system, and Google Calendar integration. 

LaTeX Bot is powered by [`pyryver`](https://github.com/tylertian123/pyryver).

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
Here is a list of commands supported by LaTeX Bot (auto generated):

General Commands:
  - `@latexbot render <formula>` - Render a LaTeX formula. 
  - `@latexbot help [command]` - Get a list of all the commands, or details about a command. 
  - `@latexbot ping` - I will respond with 'Pong' if I'm here. 
  - `@latexbot whatDoYouThink <thing>` - Ask my opinion of a thing! 
  - `@latexbot events [count]` - Display information about ongoing and upcoming events from Google Calendar. 
  - `@latexbot addEvent <name> <startdate> [starttime] <enddate> [endtime]` - Add an event to Google Calendar. **Accessible to Org and Bot Admins only.**
  - `@latexbot quickAddEvent <event>` - Add an event to Google Calendar based on a simple text string. **Accessible to Org and Bot Admins only.**
  - `@latexbot deleteEvent <name>` - Delete an event by name from Google Calendar. **Accessible to Org and Bot Admins only.**

Administrative Commands:
  - `@latexbot deleteMessages [<start>-]<end|count>` - Delete messages. **Accessible to Forum, Org and Bot Admins only.**
  - `@latexbot moveMessages [<start>-]<end|count> [(name|nickname)=]<forum|team>` - Move messages to another forum or team. **Accessible to Forum, Org and Bot Admins only.**
  - `@latexbot countMessagesSince <pattern>` - Count the number of messages since the first message that matches a pattern. **Accessible to Forum, Org and Bot Admins only.**

Roles Commands:
  - `@latexbot getUserRoles <user>` - List all roles of a user. 
  - `@latexbot getAllRoles` - List all roles and users with those roles. 
  - `@latexbot @role <roles> [message]` - @ mention all users with any of the specified roles. 
  - `@latexbot addToRole <roles> <people>` - Add people to a role. **Accessible to Org and Bot Admins only.**
  - `@latexbot removeFromRole <roles> <people>` - Remove people from a role. **Accessible to Org and Bot Admins only.**
  - `@latexbot exportRoles` - Export roles data as a JSON. 
  - `@latexbot importRoles <data>` - Import roles data as a JSON. **Accessible to Org and Bot Admins only.**

Developer Commands:
  - `@latexbot disable` - Disable me. **Accessible to Org and Bot Admins only.**
  - `@latexbot kill` - Kill me (:fearful:). **Accessible to Bot Admins only.**
  - `@latexbot sleep <seconds>` - Put me to sleep. **Accessible to Bot Admins only.**
  - `@latexbot execute <code>` - Execute arbitrary Python code. **Accessible to Bot Admins only.**
  - `@latexbot changeAccess <command> <level>` - Change the access level of a command. **Accessible to Bot Admins only.**
  - `@latexbot makeAdmin <user>` - Make a user a Bot Admin. **Accessible to Bot Admins only.**
  - `@latexbot removeAdmin <user>` - Remove a user from Bot Admins. **Accessible to Bot Admins only.**
  - `@latexbot exportConfig` - Export config as a JSON. 
  - `@latexbot importConfig <data>` - Import config from JSON. **Accessible to Bot Admins only.**

Miscellaneous Commands:
  - `@latexbot updateChats` - Update the cached list of forums/teams and users. **Accessible to Forum, Org and Bot Admins only.**
  - `@latexbot moveTo [(name|nickname)=]<forum|team>` - Move my home to another forum/team. **Accessible to Org and Bot Admins only.**


