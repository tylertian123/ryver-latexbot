# LaTeX Bot

LaTeX Bot is a bot for [Ryver](https://ryver.com/), built for [Team Arctos 6135](https://www.arctos6135.com/)'s organization.

LaTeX Bot introduces many useful features for your organization that Ryver by itself lacks, such as a Roles system with mentions,
Keyword Watches (like Slack's keyword notifications, but more customizable), mass-deleting and moving messages across forums and teams,
and of course, rendering LaTeX (and chemical equations with `mhchem`).

There are a lot of other neat features:

- Google Calendar events integration
- GitHub integration (updates and creating Ryver tasks for Issues and Pull Requests!)
- The Blue Alliance integration (get FRC team/district/event info)
- XKCDs and checkiday.com integration
- Toggleable daily events reminders, new xkcd and holidays checks
- Built-in singleplayer or multiplayer trivia game
- Flexible command access management with Access Levels and Access Rules
- Macros in chat messages

For an (almost) complete list of what LaTeX Bot can do, check out `usage_guide.md`.

LaTeX Bot uses [`pyryver`](https://github.com/tylertian123/pyryver) for interfacing with Ryver.

## Building and Running LaTeX Bot

LaTeX Bot is designed to run inside a Docker container. Currently, the hosting of LaTeX Bot is generously provided by [@mincrmatt12](https://github.com/mincrmatt12).
See `deployment_guide.md` for more info on building, running and deployment.

## Acknowledgements & Attribution

This project is powered by:

- XeTeX/LaTeX/TeX
- Ryver (https://ryver.com/)
- Checkiday (https://www.checkiday.com)
- The Blue Alliance (https://www.thebluealliance.com)
- Open Trivia Database (https://opentdb.com)
- Google Calendar
- GitHub

And uses the following open-source libraries:

- [`aiohttp`](https://pypi.org/project/aiohttp/)
- [`markdownify`](https://pypi.org/project/markdownify/)
- [`python-dateutil`](https://pypi.org/project/python-dateutil/)
- [`google-api-python-client` (+Friends)](https://pypi.org/project/google-api-python-client/)
- [`lark-parser`](https://pypi.org/project/lark-parser/)
- [`marshmallow`](https://pypi.org/project/marshmallow/)
- [`pyryver`](https://pypi.org/project/pyryver/)

Many thanks to the developers of these services, libraries and APIs for making LaTeX Bot possible.

## Feature Showcase

Rendering LaTeX and simple equations:  
![`render` and `renderSimple` commands](https://user-images.githubusercontent.com/32781310/92654019-329b4a00-f2bd-11ea-92f3-5365f0a5ade7.png)

Moving messages between forums:  
![`moveMessages` command](https://user-images.githubusercontent.com/32781310/92656127-7fcceb00-f2c0-11ea-9e4c-1f3d4d8e2dc3.png)

Mass-deletion of messages:  
![Before deleting messages](https://user-images.githubusercontent.com/32781310/92657715-49449f80-f2c3-11ea-9eee-2454df4a9d28.png)
![After deleting messages](https://user-images.githubusercontent.com/32781310/92657775-61b4ba00-f2c3-11ea-8033-65b93eec6480.png)

Role management and mentioning:  
![Viewing and mentioning roles](https://user-images.githubusercontent.com/32781310/92657351-ad1a9880-f2c2-11ea-8a27-95c8a3266516.png)  
The above mention is automatically replaced with the following:  
![Role mentions are replaced automatically](https://user-images.githubusercontent.com/32781310/92657418-ca4f6700-f2c2-11ea-9c1e-3729bd6b1495.png)

Keyword watches:
![Get notified whenever someone mentions a keyword](https://user-images.githubusercontent.com/32781310/93953201-ce46a480-fd18-11ea-802f-eda24c17b83b.png)

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
