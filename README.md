# The LaTeX Bot Project

LaTeX Bot is a bot for [Ryver](https://ryver.com/), built for [Team Arctos 6135](https://www.arctos6135.com/)'s organization.

As the name implies, LaTeX Bot's primary function is to render LaTeX (including chemical equations with mhchem).
It also comes with a lot of other neat features:
- Mass-deleting and mass-moving messages for chat moderation
- A Roles system allowing you to mention a group of users at a time
- Google Calendar events integration
- GitHub integration (updates and creating Ryver tasks for Issues and Pull Requests!)
- The Blue Alliance integration (get FRC team/district/event info)
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

# Acknowledgements & Attribution
This project is powered by:
- XeTeX/LaTeX/TeX
- Ryver (https://ryver.com/)
- Checkiday (https://www.checkiday.com)
- The Blue Alliance (https://www.thebluealliance.com)
- Open Trivia Database (https://opentdb.com)
- ~~QuickLaTeX (https://quicklatex.com/)~~ (Before v0.5.0)
- Google Calendar
- GitHub

And uses the following open-source libraries:
- [`aiohttp`](https://pypi.org/project/aiohttp/)
- [`markdownify`](https://pypi.org/project/markdownify/)
- [`python-dateutil`](https://pypi.org/project/python-dateutil/)
- [`google-api-python-client` (+Friends)](https://pypi.org/project/google-api-python-client/)
- [`pyryver`](https://pypi.org/project/pyryver/)

Many thanks to the developers of these services and APIs for making LaTeX Bot possible.

# Commands
Here is a list of commands supported by LaTeX Bot (auto generated, as of c02100e):

General Commands:
  - `@latexbot render <formula>` - Render a LaTeX formula. 
  - `@latexbot chem <formula>` - Render a chemical formula. 
  - `@latexbot renderSimple <expression>` - Render a "simple" mathematical expression. 
  - `@latexbot help [command]` - Get a list of all the commands, or details about a command. 
  - `@latexbot ping` - I will respond with 'Pong' if I'm here. 
  - `@latexbot whatDoYouThink <thing>` - Ask my opinion of a thing! 
  - `@latexbot xkcd [number]` - Get the latest xkcd or a specific xkcd by number. 
  - `@latexbot checkiday [date]` - Get a list of today's holidays or holidays for any date. 
  - `@latexbot tba <sub-command> [args]` - Query TheBlueAlliance. 
  - `@latexbot trivia <sub-command> [args]` - Play a game of trivia. See extended description for details. 

Administrative Commands:
  - `@latexbot deleteMessages [<start>-]<end|count>` - Delete messages. **Accessible to Forum, Org and Bot Admins only.**
  - `@latexbot moveMessages [<start>-]<end|count> [(name|nickname|username|email|id|jid)=][+|@]<forum|team|user>` - Move messages to another forum or team. **Accessible to Forum, Org and Bot Admins only.**
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
  - `@latexbot exportConfig` - Export config as a JSON. **Accessible to Org and Bot Admins only.**
  - `@latexbot importConfig <data>` - Import config from JSON. **Accessible to Org and Bot Admins only.**
  - `@latexbot accessRule [command] [action] [ruletype] [args]` - View or modify access rules. **Accessible to Org and Bot Admins only.**
  - `@latexbot setDailyMessageTime [time]` - Set the time daily messages are sent each day or turn them on/off. **Accessible to Org and Bot Admins only.**
  - `@latexbot dailyMessage` - Send the daily message. **Accessible to Forum, Org and Bot Admins only.**


For more details, see `usage_guide.md`.

# Feature Showcase
Rendering LaTeX and simple equations:  
![`render` and `renderSimple` commands](https://user-images.githubusercontent.com/32781310/92654019-329b4a00-f2bd-11ea-92f3-5365f0a5ade7.png)

Moving messages between forums:  
![`moveMessages` command](https://user-images.githubusercontent.com/32781310/92656127-7fcceb00-f2c0-11ea-9e4c-1f3d4d8e2dc3.png)

Mass-deletion of messages:  
![Before deleting messages](https://user-images.githubusercontent.com/32781310/92657715-49449f80-f2c3-11ea-9eee-2454df4a9d28.png)
![After deleting messages](https://user-images.githubusercontent.com/32781310/92657775-61b4ba00-f2c3-11ea-8033-65b93eec6480.png)

GitHub integration with chat messages:  
![Push & PR notification](https://user-images.githubusercontent.com/32781310/92654629-19df6400-f2be-11ea-9fb7-f53f92c8baf6.png)

GitHub Issue/PR automatically converts to Ryver Task:  
![GitHub Issue/PR integration](https://user-images.githubusercontent.com/32781310/92654722-41cec780-f2be-11ea-805a-78254b6e8ef2.png)

Google Calendar integration:  
![Querying and creating events](https://user-images.githubusercontent.com/32781310/92655233-11d3f400-f2bf-11ea-988b-6f49d38089fb.png)

Detailed command help messages:  
![Command help](https://user-images.githubusercontent.com/32781310/92657926-a6d8ec00-f2c3-11ea-9258-37b31f480b6f.png)

Playing Trivia with your friends (Powered by the [Open Trivia DB](https://opentdb.com/)):  
![Trivia game](https://user-images.githubusercontent.com/32781310/92655442-6e371380-f2bf-11ea-898b-e18b18b0814b.png)

The Blue Alliance integration (Get live team, event, and district info):  
![TBA integration](https://user-images.githubusercontent.com/32781310/92655595-afc7be80-f2bf-11ea-89bc-0b4f7841dd5b.png)

Web server with analytics dashboard (password protected) and more:  
![Analytics dashboard](https://user-images.githubusercontent.com/32781310/92655927-2664bc00-f2c0-11ea-8194-b8b3088d9448.png)

Daily Checkiday holidays and new XKCDs:  
![Checkiday and XKCD](https://user-images.githubusercontent.com/32781310/92656281-c3275980-f2c0-11ea-8f9e-faa45c107e07.png)

Fully configurable and customizable via a config JSON:  
![Config JSON](https://user-images.githubusercontent.com/32781310/92656742-9162c280-f2c1-11ea-952a-00b0536d60e8.png)

Role management and mentioning:  
![Viewing and mentioning roles](https://user-images.githubusercontent.com/32781310/92657351-ad1a9880-f2c2-11ea-8a27-95c8a3266516.png)  
The above mention is automatically replaced with the following:  
![Role mentions are replaced automatically](https://user-images.githubusercontent.com/32781310/92657418-ca4f6700-f2c2-11ea-9c1e-3729bd6b1495.png)
