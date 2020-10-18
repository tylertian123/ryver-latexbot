"""
This module contains command definitions for LaTeX Bot.
"""
import aiohttp
import asyncio
import command
import config
import io
import json
import lark
import pyryver
import random
import re
import render
import shlex
import simplelatex
import sys
import textwrap
import time
import trivia
import typing
import util
import xkcd
from cid import CaseInsensitiveDict
from datetime import datetime
from gcalendar import Calendar
from markdownify import markdownify
from tba import TheBlueAlliance
from traceback import format_exc


@command.command(access_level=command.Command.ACCESS_LEVEL_EVERYONE)
async def command_render(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Render a LaTeX formula.

    `\\displaystyle` is automatically put before the equation.

    Thank you to Matthew Mirvish for making this work!
    ---
    group: General Commands
    syntax: <formula>
    ---
    > `@latexbot render f(x) = \\sum_{i=0}^{n} \\frac{a_i}{1+x}`
    """
    if args:
        try:
            img_data = await render.render(args, color="gray", transparent=True)
        except ValueError as e:
            await chat.send_message(f"Error while rendering formula:\n```\n{e}\n```", bot.msg_creator)
            return
        file = (await chat.get_ryver().upload_file("formula.png", img_data, "image/png")).get_file()
        await chat.send_message(f"Formula: `{args}`\n![{args}]({file.get_url()})", bot.msg_creator)
    else:
        await chat.send_message("Formula can't be empty.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_EVERYONE)
async def command_chem(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Render a chemical formula.

    The formula is rendered with the mhchem package with LaTeX.
    ---
    group: General Commands
    syntax: <formula>
    ---
    > `@latexbot chem HCl_{(aq)} + NaOH_{(aq)} -> H2O_{(l)} + NaCl_{(aq)}`
    """
    if args:
        try:
            img_data = await render.render(f"\\ce{{{args}}}", color="gray", transparent=True, extra_packages=["mhchem"])
        except ValueError as e:
            await chat.send_message(f"Error while rendering formula:\n```\n{e}\n```\n\nDid you forget to put spaces on both sides of the reaction arrow?", bot.msg_creator)
            return
        file = (await chat.get_ryver().upload_file("formula.png", img_data, "image/png")).get_file()
        await chat.send_message(f"Formula: `{args}`\n![{args}]({file.get_url()})", bot.msg_creator)
    else:
        await chat.send_message("Formula can't be empty.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_EVERYONE)
async def command_render_simple(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    r"""
    Render a "simple" mathematical expression.

    Simple math expressions are designed to be easy to read and type, especially when compared to the
    verbosity of LaTeX. For example, the expression `sin(sqrt(e^x + a) / 2)` is much easier to read than
    `\sin\left(\frac{\sqrt{e^{x}+a}}{2}\right)`. Most of the supported operations are pretty intuitive,
    such as entering a basic expression with brackets and arithmetic operations. Some things that may not 
    be immediately obvious are outlined below.

    Divisions are automatically converted into fractions and will follow order of operations.
    Use brackets if you wish to make a large fraction, e.g. `(sinx+cos^2x)^2/(y+1)`.
    
    In expressions where brackets are unnecessary, such as fractions, powers, subscripts, etc, the outermost
    brackets will be stripped away if there is a pair. This means that in many cases you can add brackets to 
    clarify exactly what you mean, without having those brackets clutter up the final output. 

    The `%` operator is a modulo. The `**` operator can be used for exponentiation in place of `^`.
    There are also comparison operators, including `=`, `!=` (not equal), `>`, `<`, `>=` (greater than or
    equal to) and `<=` (less than or equal to).

    To do a function call, simply write out the function name and argument(s). Brackets are not necessary; e.g.
    both `sin x`, and `sin(x)` are valid. Common functions will be automatically recognized, e.g. sin, cos, log,
    etc. To use a custom function name, surround it with double quotes like `"func"(x)`. Function names will be
    rendered with a different font (`\operatorname` in LaTeX) compared to variables. You can also put powers and
    subscripts on them, e.g. `sin^2x`. Note that here because of order of operations only the 2 is in the power,
    and the x is left as the argument to sin.

    When implicitly multiplying a variable and a function, there needs to be a space between them. E.g. `x sinx`
    and not `xsinx`, as the latter will get parsed as a single variable. There does not need to be a space 
    between the function name and its argument, even when not using brackets.

    To do a square root, cube root, or nth root use `sqrt x`, `cbrt x`, and `root[n] x` respectively.
    Note that these operations only take a single value! Use brackets if you want to take the root
    of an entire expression, e.g. `sqrt(1+1)`.

    To do an integral, limit, summation or product, use one of the following:
    - `int`, `iint`, `iiint`, `iiiint` - Integral, double integral, triple integral and quadruple integral
    - `oint` - Contour integral
    - `sum` - Summation
    - `prod` - Product
    The bounds can be specified with `_lower^upper`, e.g. `int_0^(x+1)` is an integral from 0 to x+1.

    There is also a list of various single- and double-length arrows, such as `->`, `==>`, and two-directional
    arrows such as `<->`. Note that the fat left arrow is `<<=` and not `<=`, because the latter is the
    less-than-or-equal-to sign.

    You can insert subscripts explicitly with `_`, e.g. `x_i`, or automatically by putting a number right
    after a letter, e.g. `x1`.

    You can use `inf` or `oo` for an infinity symbol and `...` for an ellipsis. 

    Factorials (`!`), primes (`'`, `''`, ...) are also supported, along with square braces, curly braces and
    absolute values.

    To insert LaTeX directly into the output, surround it with $, e.g. `$\vec{v}$`.
    To insert a single LaTeX command directly into the output, enter it directly with the backslash,
    e.g. `sin\theta`.

    *It should be noted that because of grammar ambiguities, expression parsing can take a long time for large
    expressions or expressions with many possible interpretations. For this reason, if the conversion from 
    simple expression to LaTeX expression does not finish in 20 seconds, it will time out.*
    ---
    group: General Commands
    syntax: <expression>
    ---
    > `@latexbot renderSimple sin(sqrt(e^x + a) / 2)`
    > `@latexbot renderSimple 5x^2/sinx`
    > `@latexbot renderSimple d/(dx) f(x) = lim_(h->0) ((f(x+h)-f(x))/h)`
    > `@latexbot renderSimple $\mathcal{L}${f(t)} = F(s) = int_0^inf f(t)e^(-st) dt`
    """
    def convert():
        return simplelatex.str_to_latex(args)
    try:
        latex = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, convert), 20.0)
        try:
            img_data = await render.render(latex, color="gray", transparent=True)
        except ValueError as e:
            await chat.send_message(f"Internal Error: Invalid LaTeX generated! Error:\n```\n{e}\n```", bot.msg_creator)
            return
        file = (await chat.get_ryver().upload_file("expression.png", img_data, "image/png")).get_file()
        await chat.send_message(f"Simple expression: `{args}`  \nLaTeX: `{latex}`\n![{args}]({file.get_url()})", bot.msg_creator)
    except lark.LarkError as e:
        await chat.send_message(f"Error during expression parsing:\n```\n{e}\n```", bot.msg_creator)
    except asyncio.TimeoutError:
        await chat.send_message("Error: Operation timed out! Try entering a smaller expression or using LaTeX directly.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_EVERYONE)
async def command_help(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Get a list of commands or details about a specific command.

    Use this command without any arguments to get an overview of all the commands you can use,
    or give the name of the command you would like to know more about. You can also use "all" to
    list all the commands, regardless of whether they're accessible to you.
    ---
    group: General Commands
    syntax: [command]
    ---
    > `@latexbot help` - Get general help
    > `@latexbot help render` - Get help about the "render" command.
    """
    args = args.strip()
    if args == "" or args.lower() == "all":
        all_cmds = args.lower() == "all"
        if not all_cmds:
            level = await command.Command.get_access_level(chat, user)
            resp = "Showing commands that you have access to."
        else:
            resp = "Showing all commands."
        for group, commands in bot.help.items():
            group_desc = group + ":"
            empty = True
            for (name, description) in commands:
                if all_cmds or await bot.commands.commands[name].is_authorized(bot, chat, user, level):
                    group_desc += f"\n - {description}"
                    empty = False
            if not empty:
                resp += f"\n\n{group_desc}"
        if config.aliases:
            resp += "\n\nCurrent Aliases:\n"
            resp += "\n".join(f"* `{alias['from']}` \u2192 `{alias['to']}`" for alias in config.aliases)
        if all_cmds:
            admins = ", ".join([bot.ryver.get_user(id=uid).get_name() for uid in config.admins])
            if admins:
                resp += f"\n\nCurrent Bot Admins are: {admins}."
            else:
                resp += "\n\nNo Bot Admins are in the configuration."
        resp += "\n\nFor more details about a command, try `@latexbot help <command>`. "
        resp += "Click [here](https://github.com/tylertian123/ryver-latexbot/blob/master/usage_guide.md) for a usage guide."
        await chat.send_message(resp, bot.msg_creator)
    else:
        default = f"Error: {args} is not a valid command, or does not have an extended description."
        if args in bot.command_help:
            text = bot.command_help[args]
            if await bot.commands.commands[args].is_authorized(bot, chat, user):
                text += "\n\n:white_check_mark: **You have access to this command.**"
            else:
                text += "\n\n:no_entry: **You do not have access to this command.**"
            await chat.send_message(text, bot.msg_creator)
        else:
            await chat.send_message(default, bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_EVERYONE)
async def command_ping(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    I will respond with 'Pong' if I'm here.
    ---
    group: General Commands
    syntax:
    """
    await chat.send_message("Pong", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_EVERYONE)
async def command_tba(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Query TheBlueAlliance.

    This command has several sub-commands. Here are each one of them:
    - `team <team>` - Get basic info about a team.
    - `teamEvents <team> [year]` - Get info about a team's events in a year, or the current year if unspecified.
    - `districts [year]` - Get a list of districts for a given year, or the current year if unspecified.
    - `districtRankings <district> [year] [range]` - Get the rankings for a district for a given year, or
    the current year if unspecified. An optional range of results can be specified. See below.
    - `districtEvents <district> [year] [week(s)]` - Get the events for a district for a given year, or the
    current year if unspecified. The syntax for the weeks is identical to the range syntax (see below),
    *except if only a single number is given, only events for that week will be retrieved*.
    - `event <event> [year]` - Get info about an event for a given year, or the current year if unspecified.
    - `eventRankings <event> [year] [range]` - Get the rankings for an event for a given year, or the current
    year if unspecified. An optional range of results can be specified. See below.

    Note that districts and events are specified by code and not name, e.g. "ONT", "ONOSH" (case-insensitive).

    For all commands, the word "team" can be abbreviated as "t", "district(s)" can be abbreviated as "d",
    "event(s)" can be abbreviated as "e", and "ranking(s)" can be abbreviated as "r". They are also 
    case-insensitive.
    E.g. `districtEvents` can be abbreviated as `dEvents`, `districtE` or `dE`. 

    Some of these commands make use of *ranges*. A range can be one of the following:
    - A single number, e.g. "10" for the top 10 results.
    - Two numbers separated by a dash, e.g. "10-20" for the 10th result to the 20th result (inclusive).
    - A number followed by a plus, e.g. "10+", for everything after and including the 10th result.

    Additionally, if configured, LaTeX Bot will highlight the rows containing information about the team
    when displaying ranking tables.
    ---
    group: General Commands
    syntax: <sub-command> [args]
    ---
    > `@latexbot tba team 6135` - Get basic info about team 6135.
    > `@latexbot tba teamEvents 6135 2020` - Get info about team 6135's events in 2020.
    > `@latexbot tba districts` - Get the districts for the current year.
    > `@latexbot tba districtRankings ONT 2020 30` - Get the top 30 ranked teams in the ONT district in 2020.
    > `@latexbot tba districtEvents ONT` - Get the events in the ONT district for the current year.
    > `@latexbot tba districtEvents ONT 2020 2` - Get all week 2 events in the ONT district in 2020. 
    > `@latexbot tba event ONOSH 2020` - Get info about the ONOSH event in 2020.
    > `@latexbot tba eventRankings ONOSH` - Get the rankings for the ONOSH event for the current year.
    """
    try:
        args = shlex.split(args)
    except ValueError as e:
        await chat.send_message(f"Invalid syntax: {e}", bot.msg_creator)
        return
    if not args:
        await chat.send_message("Please specify a sub-command! See `@latexbot help tba` for details.", bot.msg_creator)
        return
    # Abbreviations
    args[0] = args[0].lower().replace("team", "t").replace("district", "d").replace("event", "e").replace("ranking", "r")

    try:
        if args[0] == "t":
            try:
                # pylint: disable=unbalanced-tuple-unpacking
                team, = util.parse_args(args[1:], ("team number", int))
            except ValueError as e:
                await chat.send_message(str(e), bot.msg_creator)
                return
            await chat.send_message(TheBlueAlliance.format_team(await bot.tba.get_team(team)), bot.msg_creator)
        elif args[0] == "te" or args[0] == "tes":
            try:
                # pylint: disable=unbalanced-tuple-unpacking
                team, year = util.parse_args(args[1:], ("team number", int), ("year", int, util.current_time().year))
            except ValueError as e:
                await chat.send_message(str(e), bot.msg_creator)
                return
            events = await bot.tba.get_team_events(team, year)
            results = await bot.tba.get_team_events_statuses(team, year)
            formatted_events = []
            for event in events:
                desc = TheBlueAlliance.format_event(event)
                if results.get(event["key"]):
                    desc += "\n\n" + markdownify(results[event["key"]]["overall_status_str"])
                else:
                    desc += "\n\n**Could not obtain info for this team's performance during this event.**"
                formatted_events.append(desc)
            await chat.send_message("\n\n".join(formatted_events), bot.msg_creator)
        elif args[0] == "ds" or args[0] == "d":
            try:
                # pylint: disable=unbalanced-tuple-unpacking
                year, = util.parse_args(args[1:], ("year", int, util.current_time().year))
            except ValueError as e:
                await chat.send_message(str(e), bot.msg_creator)
                return
            districts = await bot.tba.get_districts(year)
            resp = f"# Districts for year {year}\n"
            resp += "\n".join(f"- {district['display_name']} (**{district['abbreviation'].upper()}**)" for district in districts)
            await chat.send_message(resp, bot.msg_creator)
        elif args[0] == "dr" or args[0] == "drs":
            try:
                # pylint: disable=unbalanced-tuple-unpacking
                dist, year, rng = util.parse_args(args[1:], ("district code", None), ("year", int, util.current_time().year), ("range", None, None))
            except ValueError as e:
                await chat.send_message(str(e), bot.msg_creator)
                return
            key = str(year) + dist.lower()
            rankings = await bot.tba.get_district_rankings(key)
            dis_teams = await bot.tba.get_district_teams(key)
            teams = {team["key"]: team for team in dis_teams}
            if not rankings:
                await chat.send_message("No results.", bot.msg_creator)
                return
            # Get the ranking for the organization team
            team_rank = None
            if config.frc_team is not None:
                team_key = "frc" + str(config.frc_team)
                for r in rankings:
                    if team_key == r["team_key"]:
                        team_rank = r
                        break
            # Parse the range
            if rng:
                try:
                    rankings = util.slice_range(rankings, rng)
                except ValueError:
                    await chat.send_message("Invalid range.", bot.msg_creator)
                    return
            if not rankings:
                await chat.send_message("No results.", bot.msg_creator)
                return
            title = f"# Rankings for district {args[1]} in {year}:\n"
            if team_rank is not None:
                title += f"++Team {config.frc_team} ({teams[team_rank['team_key']]['nickname']}) ranked "
                title += f"**{util.ordinal(team_rank['rank'])}** out of {len(teams)} teams"
                if not rankings[0]["rank"] <= team_rank["rank"] <= rankings[-1]["rank"]:
                    title += " (not included in the table below)"
                title += ".++\n"
            header = "Rank|Total Points|Event 1|Event 2|District Championship|Rookie Bonus|Team Number|Team Name\n---|---|---|---|---|---|---|---\n"
            def rankings_gen():
                for r in rankings:
                    team = teams[r["team_key"]]
                    event1 = r["event_points"][0]["total"] if r["event_points"] else "Not Played"
                    event2 = r["event_points"][1]["total"] if len(r["event_points"]) >= 2 else "Not Played"
                    dcmp = r["event_points"][2]["total"] if len(r["event_points"]) >= 3 else "Not Played"
                    if len(r["event_points"]) >= 4:
                        dcmp += r["event_points"][3]["total"]
                    row = f"{r['rank']}|{r['point_total']}|{event1}|{event2}|{dcmp}|{r['rookie_bonus']}|"
                    row += f"{team['team_number']}|[{team['nickname']}]({TheBlueAlliance.TEAM_URL}{team['team_number']})"
                    if team["team_number"] == config.frc_team:
                        row = "|".join(f"=={val}==" for val in row.split("|"))
                    yield row
            for page in util.paginate(rankings_gen(), title, header):
                await chat.send_message(page, bot.msg_creator)
        elif args[0] == "de" or args[0] == "des":
            try:
                # pylint: disable=unbalanced-tuple-unpacking
                dist, year, rng = util.parse_args(args[1:], ("district code", None), ("year", int, util.current_time().year), ("range", None, None))
            except ValueError as e:
                await chat.send_message(str(e), bot.msg_creator)
                return
            key = str(year) + dist.lower()
            # Order by week
            events = sorted(await bot.tba.get_district_events(key), key=lambda x: x["week"])
            if not events:
                await chat.send_message("No results.", bot.msg_creator)
                return
            # Parse the range
            if rng:
                try:
                    try:
                        # See if the input can be parsed as a single int
                        # since it has a different behavior as the usual slicing
                        weeks = [int(rng)]
                    except ValueError:
                        # Slice to get the weeks that we want
                        # Account for 1-based indexing
                        weeks = util.slice_range(range(1, events[-1]["week"] + 2), rng)
                    events = [event for event in events if event["week"] + 1 in weeks]
                except ValueError:
                    await chat.send_message("Invalid range.", bot.msg_creator)
                    return
            if not events:
                await chat.send_message("No results.", bot.msg_creator)
                return
            def events_gen():
                for event in events:
                    yield TheBlueAlliance.format_event(event)
            for page in util.paginate(events_gen(), "", ""):
                await chat.send_message(page, bot.msg_creator)
        elif args[0] == "e":
            try:
                # pylint: disable=unbalanced-tuple-unpacking
                event_code, year = util.parse_args(args[1:], ("event code", None), ("year", int, util.current_time().year))
            except ValueError as e:
                await chat.send_message(str(e), bot.msg_creator)
                return
            event = await bot.tba.get_event(str(year) + event_code.lower())
            await chat.send_message(TheBlueAlliance.format_event(event), bot.msg_creator)
        elif args[0] == "er" or args[0] == "ers":
            try:
                # pylint: disable=unbalanced-tuple-unpacking
                event_code, year, rng = util.parse_args(args[1:], ("event code", None), ("year", int, util.current_time().year), ("range", None, None))
            except ValueError as e:
                await chat.send_message(str(e), bot.msg_creator)
                return
            key = str(year) + event_code.lower()
            rankings = await bot.tba.get_event_rankings(key)
            if not rankings:
                await chat.send_message("No results.", bot.msg_creator)
                return
            # Get the ranking for the organization team
            team_rank = None
            if config.frc_team is not None:
                team_key = "frc" + str(config.frc_team)
                for r in rankings["rankings"]:
                    if team_key == r["team_key"]:
                        team_rank = r
                        break
            if rng:
                try:
                    team_rankings = util.slice_range(rankings["rankings"], rng)
                except ValueError:
                    await chat.send_message("Invalid range.", bot.msg_creator)
                    return
            else:
                team_rankings = rankings["rankings"]
            if not rankings:
                await chat.send_message("No results.", bot.msg_creator)
                return
            title = f"# Rankings for event [{args[1]}]({TheBlueAlliance.EVENT_URL}{key}#rankings) in {year}:\n"
            if team_rank is not None:
                title += f"++Team {config.frc_team} ranked **{util.ordinal(team_rank['rank'])}** out of {len(rankings['rankings'])} teams"
                if not team_rankings[0]["rank"] <= team_rank["rank"] <= team_rankings[-1]["rank"]:
                    title += " (not included in the table below)"
                title += ".++\n"
            header = "Rank|Team|" + "|".join(i["name"] for i in rankings["sort_order_info"])
            header += "|Record (W-L-T)|DQ|Matches Played|" + "|".join(i["name"] for i in rankings["extra_stats_info"]) + "\n"
            header += "|".join("---" * (len(rankings["extra_stats_info"]) + len(rankings["sort_order_info"]) + 5))
            header += "\n"
            def rankings_gen():
                for r in team_rankings:
                    # The zip is used because sometimes sort_orders contain more values than names in sort_order_info
                    row = f"{r['rank']}|[{r['team_key'][3:]}]({TheBlueAlliance.TEAM_URL}{r['team_key'][3:]})|"
                    row += "|".join(str(stat) for stat, _ in zip(r["sort_orders"], rankings["sort_order_info"]))
                    row += f"|{r['record']['wins']}-{r['record']['losses']}-{r['record']['ties']}|{r['dq']}|{r['matches_played']}|"
                    row += "|".join(str(stat) for stat in r["extra_stats"])
                    if int(r["team_key"][3:]) == config.frc_team:
                        row = "|".join(f"=={val}==" for val in row.split("|"))
                    yield row
            for page in util.paginate(rankings_gen(), title, header):
                await chat.send_message(page, bot.msg_creator)
        else:
            await chat.send_message("Invalid sub-command. Check `@latexbot help tba` to see valid commands.", bot.msg_creator)
    except aiohttp.ClientResponseError as e:
        if e.status == 404:
            await chat.send_message("The requested info does not exist.", bot.msg_creator)
        else:
            await chat.send_message(f"HTTP Error: {e}. Please try again.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_EVERYONE)
async def command_watch(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Configure your keyword watches.

    Keyword watches are unique for each user. When you set up a keyword watch, LaTeX Bot will
    search every message sent for the string you specified. When a message containing your keyword
    is sent, you will be notified through a private message. With this system, you could mute a
    forum/team but still receive notifications when a topic you're interested in is being
    discussed.

    *Keywords could contain any number of characters and could be of any length.* You can configure
    them to be case-sensitive and/or match whole words only (by default they're neither).

    **You will not receive keyword watch notifications if any of the following are true:**
    - Your status is Available (indicated by a green dot; you can change this by clicking on your
    profile in the top left corner)
    - The message was sent to a forum or team you are not in
    - You turned keyword notifications off using `@latexbot watch off`
    - You are considered "active" by LaTeX Bot, i.e. you sent a message recently (by default in the
    last 3 minutes, configurable via `@latexbot watch activityTimeout <seconds>`).
    - Keyword watches have been suppressed explicitly through `watch suppress <seconds>`.

    To manage your keyword watches, use the following sub-commands (see examples below):
    - (No arguments) - List all your keyword watches and settings.
    - `add <keyword> [match-case] [match-whole-word]` - Add a keyword watch. **The keyword must be
    in quotes if it contains a space, e.g. "3d printer".** `match-case` and `match-whole-word`
    specify whether the keyword is case-sensitive and should match whole words only, and can be
    "true"/"false" or "yes"/"no". Both are false by default.
    - `delete <keyword-number>` - Delete a keyword *by number*. Keyword numbers can be obtained by
    listing them through `@latexbot watch`. 
    - `delete all` - Delete *all* of your keyword watches.
    - `on`, `off` - Turn keyword watch notifications on or off.
    - `activityTimeout <seconds>` - Set your activity timeout. This is the duration in seconds that
    you're considered "active" for after sending a message. When you are considered "active", you
    will not receive watch notifications. By default this is set to 3 minutes, i.e. you will not
    receive notifications for 3 minutes after sending a message. Set to 0 to disable.
    - `suppress <seconds>` - Temporarily suppress (turn off) keyword watch notifications for a
    number of seconds. To undo a suppression without having to wait, simply suppress with a
    duration of 0, i.e. `@latexbot watch suppress 0`.
    ---
    group: General Commands
    syntax: [sub-command] [args]
    ---
    > `@latexbot watch` - View your keyword watches and settings.
    > `@latexbot watch add "programming"` - Add a watch for the keyword "programming" (case insensitive).
    > `@latexbot watch add "3d printer" false true` - Add a watch for the keyword "3d printer" (case insensitive, whole words only).
    > `@latexbot watch add "CAD" yes yes` - Add a watch for the keyword "CAD" (case sensitive, whole words only).
    > `@latexbot watch delete 1` - Delete the watch with number 1.
    > `@latexbot watch delete all` - Delete all your watches.
    > `@latexbot watch off` - Turn off watch notifications.
    > `@latexbot watch activityTimeout 60` - Set your activity timeout to 1 minute, i.e. you will not receive watch notifications for 1 minute after sending a message.
    > `@latexbot watch activityTimeout 0` - Disable your activity timeout, i.e. sending messages will not affect watch notifications.
    """
    def get_default_settings_dict():
        return {
            "on": True,
            "activityTimeout": 180.0,
            "keywords": [],
        }

    try:
        args = shlex.split(args)
    except ValueError as e:
        await chat.send_message(f"Invalid syntax: {e}", bot.msg_creator)
        return
    user_id = str(user.get_id())
    if not args:
        if user_id in bot.keyword_watches:
            watch = bot.keyword_watches[user_id]
            if watch["on"]:
                resp = "Your keyword watches notifications are turned **on**."
            else:
                resp = "Your keyword watches notifications are turned **off**."
            if time.time() < watch.get("_suppressed", 0):
                resp += f"\nNotifications are suppressed for the next **{watch['_suppressed'] - time.time():.2f}** seconds."
            if watch["activityTimeout"] != 0:
                resp += f"\nYour activity timeout is set to {watch['activityTimeout']} seconds.\n\n"
            else:
                resp += "\nActivity timeout is disabled.\n\n"
            if watch["keywords"]:
                resp += "Your keyword watches are:"
                for i, watch in enumerate(watch["keywords"]):
                    resp += f"\n{i + 1}. \"{watch['keyword']}\" (match case: {watch['matchCase']}, whole word: {watch['wholeWord']})"
            else:
                resp += "You do not have any keyword watches."
        else:
            resp = "You have not set up keyword watches."
        await chat.send_message(resp, bot.msg_creator)
        return

    if args[0] == "add":
        if not 2 <= len(args) <= 4:
            await chat.send_message("Invalid number of arguments. See `@latexbot help watch` for help.", bot.msg_creator)
            return
        
        if len(args) >= 3:
            arg = args[2].lower()
            if arg == "true" or arg == "yes":
                match_case = True
            elif arg == "false" or arg == "no":
                match_case = False
            else:
                await chat.send_message("Invalid argument for match case option. See `@latexbot help watch` for help.", bot.msg_creator)
                return
        else:
            match_case = False
        if len(args) >= 4:
            arg = args[3].lower()
            if arg == "true" or arg == "yes":
                whole_word = True
            elif arg == "false" or arg == "no":
                whole_word = False
            else:
                await chat.send_message("Invalid argument for whole word option. See `@latexbot help watch` for help.", bot.msg_creator)
                return
        else:
            whole_word = False
        
        if not args[1]:
            await chat.send_message("Error: Empty keywords are not allowed.", bot.msg_creator)
            return
        if user_id not in bot.keyword_watches:
            bot.keyword_watches[user_id] = get_default_settings_dict()
        bot.keyword_watches[user_id]["keywords"].append({
            "keyword": args[1],
            "wholeWord": whole_word,
            "matchCase": match_case,
        })
        bot.save_watches()
        bot.rebuild_automaton() # Could be optimized
        resp = f"Added watch for keyword \"{args[1]}\" (match case: {match_case}, whole word: {whole_word})."
        if not bot.keyword_watches[user_id]["on"]:
            resp += " Note: Your keyword watch notifications are currently off."
        await chat.send_message(resp, bot.msg_creator)
    elif args[0] == "delete":
        if len(args) != 2:
            await chat.send_message("Invalid number of arguments. See `@latexbot help watch` for help.", bot.msg_creator)
            return
        if user_id not in bot.keyword_watches or not bot.keyword_watches[user_id]["keywords"]:
            await chat.send_message("You have no watches configured.", bot.msg_creator)
            return
        if args[1].lower() == "all":
            bot.keyword_watches[user_id]["keywords"] = []
            bot.save_watches()
            await chat.send_message("Cleared all your keyword watches.", bot.msg_creator)
        else:
            try:
                n = int(args[1]) - 1
                if n < 0 or n >= len(bot.keyword_watches[user_id]["keywords"]):
                    raise ValueError
            except ValueError:
                await chat.send_message("Invalid number.", bot.msg_creator)
            watch = bot.keyword_watches[user_id]["keywords"].pop(n)
            bot.save_watches()
            await chat.send_message(f"Removed watch #{n + 1} for keyword \"{watch['keyword']}\" (match case: {watch['matchCase']}, whole word: {watch['wholeWord']}).", bot.msg_creator)
        bot.rebuild_automaton() # Could be optimized
    elif args[0] == "on" or args[0] == "off":
        if len(args) != 1:
            await chat.send_message("Invalid number of arguments. See `@latexbot help watch` for help.", bot.msg_creator)
            return
        if user_id not in bot.keyword_watches:
            bot.keyword_watches[user_id] = get_default_settings_dict()
        bot.keyword_watches[user_id]["on"] = True if args[0] == "on" else False
        bot.save_watches()
        bot.rebuild_automaton()
        await chat.send_message(f"Turned keyword watch notifications **{args[0]}**.", bot.msg_creator)
    elif args[0] == "activityTimeout":
        if len(args) != 2:
            await chat.send_message("Invalid number of arguments. See `@latexbot help watch` for help.", bot.msg_creator)
            return
        try:
            timeout = float(args[1])
        except ValueError:
            await chat.send_message("Invalid number. Set this to 0 if you want to disable activity timeout.", bot.msg_creator)
            return
        if user_id not in bot.keyword_watches:
            bot.keyword_watches[user_id] = get_default_settings_dict()
        bot.keyword_watches[user_id]["activityTimeout"] = timeout
        bot.save_watches()
        await chat.send_message("Activity timeout has been " + (f"set to {timeout} seconds." if timeout > 0 else "disabled."), bot.msg_creator)
    elif args[0] == "suppress":
        if len(args) != 2:
            await chat.send_message("Invalid number of arguments. See `@latexbot help watch` for help.", bot.msg_creator)
            return
        try:
            duration = float(args[1])
        except ValueError:
            await chat.send_message("Invalid number. Set this to 0 if you want to disable activity timeout.", bot.msg_creator)
            return
        if user_id not in bot.keyword_watches:
            bot.keyword_watches[user_id] = get_default_settings_dict()
        bot.keyword_watches[user_id]["_suppressed"] = time.time() + duration
        bot.save_watches()
        await chat.send_message(f"Keyword watches suppressed for {duration} seconds.", bot.msg_creator)
    else:
        await chat.send_message("Invalid sub-command. See `@latexbot help watch` for help.", bot.msg_creator)


YES_MSGS = [
    "Yes.",
    "I like it!",
    "Brilliant!",
    "Genius!",
    "Do it!",
    "It's good.",
    ":thumbsup:",
]
NO_MSGS = [
    "No.",
    ":thumbsdown:",
    "I hate it.",
    "Please no.",
    "It's bad.",
    "It's stupid.",
]


@command.command(access_level=command.Command.ACCESS_LEVEL_EVERYONE)
async def command_what_do_you_think(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Ask my opinion of a thing!

    Disclaimer: These are my own opinions, Tyler is not responsible for anything said.
    ---
    group: Entertainment Commands
    syntax: <thing>
    ---
    > `@latexbot whatDoYouThink <insert controversial topic here>`
    """
    args = args.lower()
    # Match configured opinions
    for opinion in config.opinions:
        if args in opinion["thing"]:
            # Match user if required
            if "user" in opinion:
                if user.get_username() in opinion["user"]:
                    await chat.send_message(random.choice(opinion["opinion"]), bot.msg_creator)
                    return
            else:
                await chat.send_message(random.choice(opinion["opinion"]), bot.msg_creator)
                return
    msgs = NO_MSGS if hash(args) % 2 == 0 else YES_MSGS
    await chat.send_message(random.choice(msgs), bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_EVERYONE)
async def command_xkcd(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Get the latest xkcd or a specific xkcd by number.
    ---
    group: Entertainment Commands
    syntax: [number]
    ---
    > `@latexbot xkcd` - Get the latest xkcd.
    > `@latexbot xkcd 149` - Get xkcd #149.
    """
    xkcd_creator = pyryver.Creator(bot.msg_creator.name, util.XKCD_PROFILE)
    if args:
        try:
            number = int(args)
        except ValueError:
            await chat.send_message("Invalid number.", xkcd_creator)
            return
    else:
        number = None
    
    try:
        comic = await xkcd.get_comic(number)
        if not comic:
            await chat.send_message("Error: This comic does not exist (404). Have this image of a turtle instead.\n\n![A turtle](https://cdn.britannica.com/66/195966-138-F9E7A828/facts-turtles.jpg)", xkcd_creator)
            return
        
        await chat.send_message(xkcd.comic_to_str(comic), xkcd_creator)
    except aiohttp.ClientResponseError as e:
        await chat.send_message(f"An error occurred: {e}", xkcd_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_EVERYONE)
async def command_checkiday(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Get a list of today's holidays or holidays for any date.

    This command uses the https://www.checkiday.com/ API.

    The date is optional; if specified, it must be in the YYYY/MM/DD format.
    ---
    group: Entertainment Commands
    syntax: [date]
    ---
    > `@latexbot checkiday` - Get today's holidays.
    > `@latexbot checkiday 2020/05/12` - Get the holidays on May 12, 2020.
    """
    url = f"https://www.checkiday.com/api/3/?d={args or util.current_time().strftime('%Y/%m/%d')}"
    async with aiohttp.request("GET", url) as resp:
        if resp.status != 200:
            await chat.send_message(f"HTTP error while trying to get holidays: {resp}", bot.msg_creator)
            return
        data = await resp.json()
    if data["error"] != "none":
        await chat.send_message(f"Error: {data['error']}", bot.msg_creator)
        return
    if not data.get("holidays", None):
        await chat.send_message(f"No holidays on {data['date']}.")
    else:
        msg = f"Here is a list of all the holidays on {data['date']}:\n"
        msg += "\n".join(f"* [{holiday['name']}]({holiday['url']})" for holiday in data["holidays"])
        await chat.send_message(msg, bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_EVERYONE)
async def command_trivia(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Play a game of trivia. See extended description for details. 
    
    Powered by [Open Trivia Database](https://opentdb.com/).
    
    The trivia command has several sub-commands. Here are each one of them:
    - `categories` - Get all the categories and their IDs, which are used later to start a game.
    - `start [category] [difficulty] [type]` - Start a game with an optional category, difficulty and type. The category can be an ID, a name from the `categories` command, 'all' (all regular questions, no custom), or 'custom' (all custom questions, no regular). If the name contains a space, it must be surrounded with quotes. The difficulty can be "easy", "medium" or "hard". The type can be either "true/false" or "multiple-choice". You can also specify "all" for any of the categories.
    - `question`, `next` - Get the next question or repeat the current question. You can also react to a question with :fast_forward: to get the next question after it's been answered.
    - `answer <answer>` - Answer a question. <answer> can always be an option number. It can also be "true" or "false" for true/false questions. You can also use reactions to answer a question.
    - `scores` - View the current scores. Easy questions are worth 10 points, medium questions are worth 20, and hard questions are worth 30 each. You can also react to a question with :trophy: to see the scores.
    - `end` - End the game (can only be used by the "host" (the one who started the game) or Forum Admins or higher).
    - `games` - See all ongoing games.
    - `importCustomQuestions` - Import custom questions as a JSON. Accessible to Org Admins or higher.
    - `exportCustomQuestions` - Export custom questions as a JSON. Accessible to Org Admins or higher.

    Here's how a game usually goes:
    - The "host" uses `@latexbot trivia categories` to see all categories (optional)
    - The "host" uses `@latexbot trivia start [category] [difficulty] [type]` to start the game
    - Someone uses `@latexbot trivia question` or `@latexbot trivia next` to get each question
    - The participants answer each question by using reactions or `@latexbot trivia answer <answer>`
    - The participants use `@latexbot trivia scores` to check the scores during the game
    - The "host" uses `@latexbot trivia end` to end the game

    Since LaTeX Bot v0.6.0, there can be multiple games per organization. 
    However, there can still only be one game per chat. This also includes your private messages with LaTeX Bot.
    After 15 minutes of inactivity, the game will end automatically.

    Note: The `importCustomQuestions`, `exportCustomQuestions`, and `end` sub-commands can have access rules.
    Use the names `trivia importCustomQuestions`, `trivia exportCustomQuestions` and `trivia end` respectively to refer to them in the accessRule command.
    ---
    group: Entertainment Commands
    syntax: <sub-command> [args]
    ---
    > `@latexbot trivia categories` - See all categories.
    > `@latexbot trivia start "Science: Computers" all true/false` - Start a game with the category "Science: Computers", all difficulties, and only true/false questions.
    > `@latexbot trivia question` - Get the question, or repeat the question.
    > `@latexbot trivia next` - Same as `@latexbot trivia question`
    > `@latexbot trivia answer 1` - Answer the question with option 1.
    > `@latexbot trivia scores` - See the current scores.
    > `@latexbot trivia end` - End the game.
    > `@latexbot trivia games` - See all ongoing games.
    > `@latexbot trivia importCustomQuestions {}` - Import some custom questions as a JSON.
    > `@latexbot trivia exportCustomQuestions` - Export some custom questions as a JSON.
    """
    if args == "":
        await chat.send_message("Error: Please specify a sub-command! See `@latexbot help trivia` for details.", bot.msg_creator)
        return

    # Purge old games
    for chat_id, game in bot.trivia_games.items():
        if game.ended:
            bot.trivia_games.pop(chat_id)

    # Find the first whitespace
    space = None
    for i, c in enumerate(args):
        if c.isspace():
            space = i
            break
    if space:
        cmd = args[:space]
        sub_args = args[space + 1:]
    else:
        cmd = args
        sub_args = ""
    
    if cmd == "exportCustomQuestions":
        if await bot.commands.commands["trivia exportCustomQuestions"].is_authorized(bot, chat, user):
            await util.send_json_data(chat, trivia.CUSTOM_TRIVIA_QUESTIONS, "Custom Questions:", 
                                      "trivia.json", bot.user, bot.msg_creator)
        else:
            await chat.send_message("You are not authorized to do that.", bot.msg_creator)
        return
    elif cmd == "importCustomQuestions":
        if await bot.commands.commands["trivia importCustomQuestions"].is_authorized(bot, chat, user):
            msg = await pyryver.retry_until_available(chat.get_message, msg_id, timeout=5.0)
            try:
                trivia.set_custom_trivia_questions(await util.get_attached_json_data(msg, sub_args))
                await chat.send_message("Operation successful.", bot.msg_creator)
            except ValueError as e:
                await chat.send_message(str(e), bot.msg_creator)
        else:
            await chat.send_message("You are not authorized to do that.", bot.msg_creator)
        return

    try:
        args = shlex.split(args)
    except ValueError as e:
        await chat.send_message(f"Invalid syntax: {e}", bot.msg_creator)
        return
    if cmd == "games":
        if not bot.trivia_games:
            await chat.send_message("No games are ongoing.", bot.msg_creator)
            return
        resp = "Current games:\n"
        resp += "\n".join(f"- Game started by {game.get_user_name(game.game.host)} in {bot.ryver.get_chat(id=chat).get_name()}." for chat, game in bot.trivia_games.items()) # pylint: disable=no-member
        await chat.send_message(resp, bot.msg_creator)
    elif cmd == "categories":
        # Note: The reason we're not starting from 0 here is because of markdown forcing you to start a list at 1
        categories = "\n".join(f"{i + 1}. {category['name']}" for i, category in enumerate(await trivia.get_categories()))
        custom_categories = trivia.get_custom_categories()
        if custom_categories:
            categories += "\n\n# Custom categories:\n"
            categories += "\n".join(f"* {category}" for category in custom_categories)
            categories += "\n\nCustom categories can only be specified by name. Use 'all' for all regular categories (no custom), or 'custom' for all custom categories (no regular)."
        await chat.send_message(f"# Categories:\n{categories}", bot.msg_creator)
    elif cmd == "start":
        if len(sub_args) > 3:
            await chat.send_message("Invalid syntax. See `@latexbot help trivia` for details.", bot.msg_creator)
            return
        
        if chat.get_id() in bot.trivia_games:
            game = bot.trivia_games[chat.get_id()]
            await chat.send_message(f"Error: A game started by {game.get_user_name(game.game.host)} already exists in this chat.", bot.msg_creator)
            return
        
        # Try parsing the category
        if len(sub_args) >= 1:
            try:
                # Subtract 1 for correct indexing
                category = int(sub_args[0]) - 1
            except ValueError:
                category = sub_args[0]
            categories = await trivia.get_categories()
            if isinstance(category, int):
                if category < 0 or category >= len(categories):
                    await chat.send_message("Category ID out of bounds! Please see `@latexbot trivia categories` for all valid categories.", bot.msg_creator)
                    return
                # Get the actual category ID
                category = categories[category]["id"]
            # String-based category
            else:
                category = category.lower()
                if category == "all":
                    category = None
                elif category == "custom":
                    category = "custom"
                else:
                    found = False
                    for c in categories:
                        # Case-insensitive search
                        if c["name"].lower() == category:
                            found = True
                            category = c["id"]
                            break
                    if not found:
                        for c in trivia.get_custom_categories():
                            if c.lower() == category:
                                found = True
                                category = c
                                break
                    if not found:
                        await chat.send_message("Invalid category. Please see `@latexbot trivia categories` for all valid categories.", bot.msg_creator)
                        return
        else:
            category = None
            difficulty = None
            question_type = None
        
        # Try parsing the difficulty
        if len(sub_args) >= 2:
            try:
                difficulty = {
                    "easy": trivia.TriviaSession.DIFFICULTY_EASY,
                    "medium": trivia.TriviaSession.DIFFICULTY_MEDIUM,
                    "hard": trivia.TriviaSession.DIFFICULTY_HARD,
                    "all": None,
                }[sub_args[1].lower()]
            except KeyError:
                await chat.send_message("Invalid difficulty! Allowed difficulties are 'easy', 'medium', 'hard' or 'all'.", bot.msg_creator)
                return
        else:
            difficulty = None
            question_type = None
        
        # Try parsing the type
        if len(sub_args) >= 3:
            try:
                question_type = {
                    "true/false": trivia.TriviaSession.TYPE_TRUE_OR_FALSE,
                    "multiple-choice": trivia.TriviaSession.TYPE_MULTIPLE_CHOICE,
                    "all": None,
                }[sub_args[2].lower()]
            except KeyError:
                await chat.send_message("Invalid question type! Allowed types are 'true/false', 'multiple-choice' or 'all'.", bot.msg_creator)
                return
        else:
            question_type = None
        
        # Start the game!
        game = trivia.TriviaGame()
        game.set_category(category)
        game.set_difficulty(difficulty)
        game.set_type(question_type)
        await game.start(user.get_id())
        trivia_game = trivia.LatexBotTriviaGame(chat, game, bot.msg_creator)
        bot.trivia_games[chat.get_id()] = trivia_game
        await trivia_game._try_get_next()

        await chat.send_message("Game started! Use `@latexbot trivia question` to get the question.", bot.msg_creator)
    elif cmd == "question" or cmd == "next":
        if chat.get_id() not in bot.trivia_games:
            await chat.send_message("Error: Game not started! Use `@latexbot trivia start [category] [difficulty] [type]` to start a game.", bot.msg_creator)
            return
        await bot.trivia_games[chat.get_id()].next_question()
    elif cmd == "answer":
        if len(sub_args) != 1:
            await chat.send_message("Invalid syntax. See `@latexbot help trivia` for details.", bot.msg_creator)
            return
        
        if chat.get_id() not in bot.trivia_games:
            await chat.send_message("Error: Game not started! Use `@latexbot trivia start [category] [difficulty] [type]` to start a game.", bot.msg_creator)
            return
        
        game = bot.trivia_games[chat.get_id()]
        if game.game.current_question["answered"]:
            await chat.send_message("Error: The current question has already been answered. Use `@latexbot trivia question` to get the next question.", bot.msg_creator)
            return
        
        try:
            # Subtract 1 for correct indexing
            answer = int(sub_args[0]) - 1
        except ValueError:
            # Is this a true/false question?
            if game.game.current_question["type"] == trivia.TriviaSession.TYPE_TRUE_OR_FALSE:
                answer = sub_args[0].lower()
                # Special handling for true/false text
                if answer == "true":
                    answer = 0
                elif answer == "false":
                    answer = 1
                else:
                    await chat.send_message("Please answer 'true' or 'false' or an option number!", bot.msg_creator)
                    return
            else:
                await chat.send_message("Answer must be an option number, not text!", bot.msg_creator)
                return
        
        if answer < 0 or answer >= len(game.game.current_question["answers"]):
            await chat.send_message("Invalid answer number!", bot.msg_creator)
            return
        
        await game.answer(answer, user.get_id())
    elif cmd == "scores":
        if chat.get_id() not in bot.trivia_games:
            await chat.send_message("Error: Game not started! Use `@latexbot trivia start [category] [difficulty] [type]` to start a game.", bot.msg_creator)
            return
        await bot.trivia_games[chat.get_id()].send_scores()
    elif cmd == "end":
        if chat.get_id() not in bot.trivia_games:
            await chat.send_message("Error: Game not started! Use `@latexbot trivia start [category] [difficulty] [type]` to start a game.", bot.msg_creator)
            return
        game = bot.trivia_games[chat.get_id()]
        # Get the message object so we can check if the user is authorized
        if user.get_id() == game.game.host or await bot.commands.commands["trivia end"].is_authorized(bot, chat, user):
            # Display the scores
            scores = trivia.order_scores(game.game.scores)
            if not scores:
                await chat.send_message("Game ended. No questions were answered, so there are no scores to display.", bot.msg_creator)
            else:
                resp = "The game has ended. "
                # Single winner
                if len(scores[1][0]) == 1:
                    resp += f"**{game.get_user_name(scores[1][0][0])}** is the winner with a score of **{scores[1][1]}**!\n\nFull scoreboard:\n"
                # Multiple winners
                else:
                    resp += f"**{', '.join(game.get_user_name(winner) for winner in scores[1][0])}** are the winners, tying with a score of **{scores[1][1]}**!\n\nFull scoreboard:\n"
                await chat.send_message(resp, bot.msg_creator)
                await game.send_scores()
            await game.end()
            del bot.trivia_games[chat.get_id()]
        else:
            await chat.send_message("Error: Only the one who started the game or a Forum Admin or higher may end the game!", bot.msg_creator)
    else:
        await chat.send_message("Invalid sub-command! Please see `@latexbot help trivia` for all valid sub-commands.", bot.msg_creator)


async def reaction_trivia(bot: "latexbot.LatexBot", ryver: pyryver.Ryver, session: pyryver.RyverWS, data: typing.Dict[str, typing.Any]): # pylint: disable=unused-argument
    """
    This coro does extra processing for interfacing trivia with reactions.
    """
    # Verify that this is an answer to a trivia question
    if data["type"] != "Entity.ChatMessage":
        return
    for game in bot.trivia_games.values():
        if game.question_msg is None:
            return
        if data["id"] == game.question_msg.get_id():
            user = ryver.get_user(id=data["userId"])
            if user == bot.user:
                return
                
            # Scoreboard
            if data["reaction"] == "trophy":
                await game.send_scores()
                return

            # Next question
            if data["reaction"] == "fast_forward":
                if game.game.current_question["answered"]:
                    await game.next_question()
                return

            # Answer
            if game.game.current_question["answered"]:
                return
            # Try to decode the reaction into an answer
            if game.game.current_question["type"] == trivia.TriviaSession.TYPE_MULTIPLE_CHOICE:
                try:
                    answer = trivia.LatexBotTriviaGame.TRIVIA_NUMBER_EMOJIS.index(data["reaction"])
                    # Give up if it's invalid
                    if answer >= len(game.game.current_question["answers"]):
                        return
                except ValueError:
                    return
            else:
                if data["reaction"] == "white_check_mark":
                    answer = 0
                elif data["reaction"] == "x":
                    answer = 1
                else:
                    return
            
            await game.answer(answer, data["userId"])
            break


@command.command(access_level=command.Command.ACCESS_LEVEL_EVERYONE)
async def command_leaderboards(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Print out the activity leaderboards. Only works with analytics enabled.

    Message activity is measured in total number of characters sent. Also available at `/analytics-ui`
    on the web server.
    ---
    group: Entertainment Commands
    syntax:
    """
    if not bot.analytics:
        await chat.send_message("This feature is unavailable because analytics are disabled.", bot.msg_creator)
    leaderboards = [(int(uid), count) for i, (uid, count) in enumerate(sorted(bot.analytics.message_activity.items(), key=lambda x: x[1], reverse=True)) if i < 20]
    resp = "# Message Activity Leaderboards (Top 20)"
    rank = None
    score = None
    for i, (uid, count) in enumerate(leaderboards):
        uobj = bot.ryver.get_user(id=uid)
        resp += f"\n{i + 1}. {uobj.get_name()} (`{uobj.get_username()}`) with a score of **{count}**"
        if uid == user.get_id():
            rank = i + 1
            score = count
    if rank is not None:
        resp += f"\n\nYou are in **{util.ordinal(rank)}** place, with a score of **{score}**."
    else:
        resp += "\n\nYou are not on the leaderboards. Be more active!"
    await chat.send_message(resp, bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_FORUM_ADMIN)
async def command_delete_messages(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Delete messages.

    If no <start> is provided, this command deletes the last <count>/<end> messages.
    If <start> is provided, this command deletes messages from <start> to <end> inclusive, with 1-based indexing.

    The command message itself is always deleted.
    ---
    group: Administrative Commands
    syntax: [<start>-]<end|count>
    ---
    > `@latexbot deleteMessages 10` - Delete the last 10 messages.
    > `@latexbot deleteMessages 10-20` - Delete the 10th last to 20th last messages, inclusive.
    """
    if isinstance(chat, pyryver.User):
        await chat.send_message("This command cannot be used in private messages.", bot.msg_creator)
        return
    try:
        # Try and parse the range
        if "-" in args:
            start = int(args[:args.index("-")].strip())
            args = args[args.index("-") + 1:].strip()
        else:
            start = 1
        end = int(args)
    except (ValueError, IndexError):
        await chat.send_message("Invalid syntax.", bot.msg_creator)
        return
    if start > end:
        await chat.send_message("No messages to delete.", bot.msg_creator)
        return

    # Special case for start = 1
    if start == 1:
        msgs = await util.get_msgs_before(chat, msg_id, end)
    else:
        # Cut off the end (newer messages)
        # Subtract 1 for 1-based indexing
        msgs = (await util.get_msgs_before(chat, msg_id, end))[:-(start - 1)]
    # Use multiple tasks
    WORKERS = 7
    await util.process_concurrent(msgs, pyryver.ChatMessage.delete, WORKERS)
    await (await pyryver.retry_until_available(chat.get_message, msg_id, timeout=5.0)).delete()


@command.command(access_level=command.Command.ACCESS_LEVEL_FORUM_ADMIN)
async def command_move_messages(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Move messages to another forum or team.

    If no <start> is provided, this command moves the last <count>/<end> messages.
    If <start> is provided, this command moves messages from <start> to <end> inclusive, with 1-based indexing.

    The destination chat is specified with the Standard Chat Lookup Syntax.
    Refer to [the usage guide](https://github.com/tylertian123/ryver-latexbot/blob/master/usage_guide.md#the-standard-chat-lookup-syntax) for more info.
    But if you're lazy, you can just use the *case-sensitive* exact name of the destination forum/team.

    Note that reactions cannot be moved perfectly, and are instead shown with text.
    ---
    group: Administrative Commands
    syntax: [<start>-]<end|count> [(name|nickname|username|email|id|jid)=][+|@]<forum|team|user>
    ---
    > `@latexbot moveMessages 10 Off-Topic` - Move the last 10 messages to Off-Topic.
    > `@latexbot moveMessages 10-20 nickname=OffTopic` - Move the 10th last to 20th last messages (inclusive) to a forum/team with the nickname +OffTopic.
    """
    if isinstance(chat, pyryver.User):
        await chat.send_message("This command cannot be used in private messages.", bot.msg_creator)
        return
    try:
        i = args.index(" ")
        msg_range = args[:i]
        to_chat = args[i + 1:]
    except ValueError:
        await chat.send_message("Invalid syntax.", bot.msg_creator)
        return

    try:
        # Try and parse the range
        if "-" in msg_range:
            start = int(msg_range[:msg_range.index("-")].strip())
            msg_range = msg_range[msg_range.index("-") + 1:].strip()
        else:
            start = 1
        end = int(msg_range)
    except (ValueError, IndexError):
        await chat.send_message("Invalid syntax.", bot.msg_creator)
        return

    try:
        to = util.parse_chat_name(chat.get_ryver(), to_chat) # type: pyryver.Chat
        if not to:
            await chat.send_message("Chat not found.", bot.msg_creator)
            return
    except ValueError as e:
        await chat.send_message(str(e), bot.msg_creator)

    # Special case for start = 1
    if start == 1:
        msgs = await util.get_msgs_before(chat, msg_id, end)
    else:
        # Cut off the end (newer messages)
        # Subtract 1 for 1-based indexing
        msgs = (await util.get_msgs_before(chat, msg_id, end))[:-(start - 1)]

    await to.send_message(f"# Begin Moved Message from {chat.get_name()}\n\n---", bot.msg_creator)

    for msg in msgs:
        # Get the creator
        msg_creator = await bot.get_replace_message_creator(msg)

        msg_body = util.sanitize(msg.get_body())
        # Handle reactions
        # Because reactions are from multiple people they can't really be moved the same way
        if msg.get_reactions():
            msg_body += "\n"
            for emoji, people in msg.get_reactions().items():
                # Instead for each reaction, append a line at the bottom with the emoji
                # and every user's display name who reacted with the reaction
                u = [chat.get_ryver().get_user(id=person) for person in people]
                msg_body += f"\n:{emoji}:: {', '.join([user.get_display_name() if user else 'unknown' for user in u])}"

        # Handle file attachments
        if msg.get_attached_file() is not None:
            # Normally if there is a file attachment the message will end with \n\n[filename]
            # It is added automatically by the Ryver client and pyryver; without it the embed doesn't show up
            # But here we should get rid of it to avoid repeating it twice
            index = msg_body.rfind("\n\n")
            if index != -1:
                msg_body = msg_body[:index]
            await to.send_message(msg_body, msg_creator, msg.get_attached_file())
        else:
            await to.send_message(msg_body, msg_creator)
        await msg.delete()

    await to.send_message(f"---\n\n# End Moved Message from {chat.get_name()}", bot.msg_creator)
    await (await pyryver.retry_until_available(chat.get_message, msg_id, timeout=5.0)).delete()
    await chat.send_message(f"{len(msgs)} messages has been moved to {to.get_name()} from this forum/team.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_FORUM_ADMIN)
async def command_count_messages_since(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    r"""
    Count the number of messages since the first message that matches a pattern.

    This command counts messages from the first message that matches <pattern> to the command message (inclusive).
    It can be a very useful tool for deleting or moving long conversations without having to count the messages manually.
    The search pattern is case insensitive.

    If <pattern> is surrounded with slashes `/like so/`, it is treated as a **Python style** regex, with the multiline and ignorecase flags.

    This command will only search through the last 250 messages maximum.
    ---
    group: Administrative Commands
    syntax: <pattern>
    ---
    > `@latexbot countMessagesSince foo bar` - Count the number of messages since someone said "foo bar".
    > `@latexbot countMessagesSince /((?:^|[^a-zA-Z0-9_!@#$%&*])(?:(?:@)(?!\/)))([a-zA-Z0-9_]*)(?:\b(?!@)|$)/` - Count the number of messages since someone last used an @ mention.
    """
    if args.startswith("/") and args.endswith("/"):
        try:
            expr = re.compile(args[1:-1], re.MULTILINE | re.IGNORECASE)
            # Use the regex search function as the match function
            match = expr.search
        except re.error as e:
            await chat.send_message("Invalid regex: " + str(e), bot.msg_creator)
            return
    else:
        args = args.lower()
        # Case insensitive match
        match = lambda x: x.lower().find(args) != -1

    count = 1
    # Max search depth: 250
    while count < 250:
        # Reverse the messages as by default the oldest is the first
        # Search 50 at a time
        msgs = (await util.get_msgs_before(chat, msg_id, 50))[::-1]
        for message in msgs:
            count += 1
            if match(message.get_body()):
                # Found a match
                resp = f"There are a total of {count} messages, including your command but not this message."
                author_name = (await message.get_author()).get_display_name()
                resp += f"\n\nMessage matched (sent by {author_name}):\n{util.sanitize(message.get_body())}"
                await chat.send_message(resp, bot.msg_creator)
                return
        # No match - change anchor
        msg_id = msgs[-1].get_id()
    await chat.send_message(
        "Error: Max search depth of 250 messages exceeded without finding a match.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_FORUM_ADMIN)
async def command_mute(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    "Mute" another user in the current forum.

    Since Ryver doesn't allow muting directly, this is achieved by deleting every single message
    sent by that user immediately. All commands and messages from the user will also be ignored.

    A user cannot mute another user that can also mute, unless they have a higher access level.
    For example, if two people can both use mute, but one of them is a forum admin while the other
    isn't, then the first person can mute the second person. However, if both or neither of them
    are forum admins, then they cannot mute each other.

    You can optionally specify a duration in seconds, after which the user will be automatically
    unmuted.
    ---
    group: Administrative Commands
    syntax: [@]<username> [duration]
    ---
    > `@latexbot mute tylertian` - Mute tylertian in the current forum.
    > `@latexbot mute @foobar 1200` - Mute foobar in the current forum for 1200 seconds (20 minutes).
    """
    try:
        args = shlex.split(args)
    except ValueError as e:
        await chat.send_message(f"Invalid syntax: {e}", bot.msg_creator)
        return
    if len(args) > 2:
        await chat.send_message("Invalid syntax: Too many arguments. See `@latexbot help mute` for more info.", bot.msg_creator)
        return
    username = args[0]
    if username.startswith("@"):
        username = username[1:]
    mute_user = bot.ryver.get_user(username=username)
    if mute_user is None:
        await chat.send_message(f"User {username} not found. Please enter a valid username.", bot.msg_creator)
        return
    if len(args) >= 2:
        try:
            duration = float(args[1])
        except ValueError as e:
            await chat.send_message("Please enter a valid number for the duration.", bot.msg_creator)
            return
    else:
        duration = None
    # Check access levels
    if mute_user == user:
        if duration is None:
            await chat.send_message("Error: You cannot mute yourself without a time limit.", bot.msg_creator)
            return
        else:
            await chat.send_message("Warning: You are muting yourself. If this is a mistake, you can contact an admin to unmute yourself.", bot.msg_creator)
    else:
        if await bot.commands.commands["mute"].is_authorized(bot, chat, mute_user):
            user_level = await command.Command.get_access_level(chat, user)
            mute_level = await command.Command.get_access_level(chat, mute_user)
            if user_level <= mute_level:
                await chat.send_message(f"Error: You cannot mute this user because they can also use mute and have a higher access level than you ({mute_level} >= {user_level}).", bot.msg_creator)
                return
    uid = mute_user.get_id()
    if uid not in bot.user_info or bot.user_info[uid].muted is None:
        bot.user_info[uid] = latexbot.UserInfo(muted={})
    muted = bot.user_info[uid].muted
    # Remove the previous unmute task if it exists
    task = muted.get(chat.get_id())
    if task is not None and not task.done():
        task.cancel()
        await task
    if duration is None:
        muted[chat.get_id()] = None
        await chat.send_message(f"Muted user {mute_user.get_name()} (`{mute_user.get_username()}`) in {chat.get_name()}.", bot.msg_creator)
    else:
        # Define an unmute task that unmutes the user after the specified duration
        async def _unmute_task():
            try:
                await asyncio.sleep(duration)
                muted.pop(chat.get_id())
                await chat.send_message(f"User {mute_user.get_name()} (`{mute_user.get_username()}`) has been unmuted in {chat.get_name()}.", bot.msg_creator)
            except asyncio.CancelledError:
                pass
        muted[chat.get_id()] = asyncio.create_task(_unmute_task())
        await chat.send_message(f"Muted user {mute_user.get_name()} (`{mute_user.get_username()}`) in {chat.get_name()} for {duration} seconds.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_FORUM_ADMIN)
async def command_unmute(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Unmute someone in the current forum.

    See `@latexbot help mute` for more information about muting.
    ---
    group: Administrative Commands
    syntax: [@]<username>
    ---
    > `@latexbot unmute tylertian` - Unmute tylertian in the current forum.
    """
    if args.startswith("@"):
        args = args[1:]
    mute_user = bot.ryver.get_user(username=args)
    if mute_user is None:
        await chat.send_message(f"User {args} not found. Please enter a valid username.", bot.msg_creator)
        return
    if mute_user.get_id() not in bot.user_info or bot.user_info[mute_user.get_id()].muted is None or chat.get_id() not in bot.user_info[mute_user.get_id()].muted:
        await chat.send_message(f"{mute_user.get_name()} is not muted in {chat.get_name()}.", bot.msg_creator)
        return
    # Check access levels
    if await bot.commands.commands["mute"].is_authorized(bot, chat, mute_user):
        user_level = await command.Command.get_access_level(chat, user)
        mute_level = await command.Command.get_access_level(chat, mute_user)
        if user_level <= mute_level:
            await chat.send_message(f"Error: You cannot unmute this user because they can use mute and have a higher access level than you ({mute_level} >= {user_level}).", bot.msg_creator)
            return
    task = bot.user_info[mute_user.get_id()].muted.pop(chat.get_id())
    if task is not None and not task.done():
        task.cancel()
        await task
    await chat.send_message(f"Unmuted user {mute_user.get_name()} (`{mute_user.get_username()}`) in {chat.get_name()}.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_EVERYONE)
async def command_roles(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Get information about roles.

    The roles system allow you to mention a group of people at once through 
    Discord-style role mentions like @RoleName. When a mention like this is
    detected, LaTeX Bot will automatically replace it with mentions for the 
    people with that role. Note that role names work like Ryver usernames, ie
    they can only contain alphanumeric characters and underscores, and are
    case-insensitive.

    If a username is supplied, this command gets all roles of the user.
    If a role name is supplied, this command gets all users with that role.
    If no parameters are supplied, this command gets all roles and users
    with roles.
    ---
    group: Roles Commands
    syntax: [[@]username|role]
    ---
    > `@latexbot roles` - Get all roles and users with the roles.
    > `@latexbot roles Foo` - Get all users with role Foo.
    > `@latexbot roles tylertian` - Get all roles of user tylertian.
    """
    if not bot.roles:
        await chat.send_message("There are currently no roles.", bot.msg_creator)
    if args == "":
        if bot.roles:
            roles_str = "\n".join(
                f"**{role}**: {', '.join(usernames)}" for role, usernames in bot.roles.items())
            await chat.send_message(f"All roles:\n{roles_str}", bot.msg_creator)
    else:
        # A mention
        if args.startswith("@"):
            args = args[1:]
        # A role
        if args in bot.roles:
            users = "\n".join(bot.roles[args])
            await chat.send_message(f"These users have the role '{args}':\n{users}", bot.msg_creator)
        # Check if it's a username
        elif chat.get_ryver().get_user(username=args):
            roles = "\n".join(role for role, usernames in bot.roles.items() if util.contains_ignorecase(args, usernames))
            if roles:
                await chat.send_message(
                    f"User '{args}' has the following roles:\n{roles}", bot.msg_creator)
            else:
                await chat.send_message(f"User '{args}' has no roles.", bot.msg_creator)
        else:
            await chat.send_message(f"'{args}' is not a valid username or role name.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_ORG_ADMIN)
async def command_add_to_role(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Add people to a role.

    Note that role names work like Ryver usernames, ie they can only contain 
    alphanumeric characters and underscores, and are case-insensitive.

    Roles are in a comma-separated list, e.g. Foo,Bar,Baz.
    ---
    group: Roles Commands
    syntax: <role1>[,<role2>...] [@]<username1>[,[@]<username2>...]
    ---
    > `@latexbot addToRole Foo tylertian` - Give Tyler the "Foo" role.
    > `@latexbot addToRole Foo,Bar tylertian latexbot` Give Tyler and LaTeX Bot the "Foo" and "Bar" roles.
    """
    try:
        args = shlex.split(args)
    except ValueError as e:
        await chat.send_message(f"Invalid syntax: {e}", bot.msg_creator)
        return
    if len(args) < 2:
        await chat.send_message("Invalid syntax.", bot.msg_creator)
        return

    roles = [r.strip() for r in args[0].split(",")]
    usernames = [username[1:] if username.startswith(
        "@") else username for username in args[1:]]

    for role in roles:
        if " " in role or "," in role:
            await chat.send_message(
                f"Invalid role: {role}. Role names must not contain spaces or commas. Skipping...", bot.msg_creator)
            continue
        # Role already exists
        if role in bot.roles:
            for username in usernames:
                if username in bot.roles[role]:
                    await chat.send_message(
                        f"Warning: User '{username}' already has role '{role}'.", bot.msg_creator)
                else:
                    bot.roles[role].append(username)
        else:
            bot.roles[role] = usernames
    bot.save_roles()

    await chat.send_message("Operation successful.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_ORG_ADMIN)
async def command_remove_from_role(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Remove people from roles.

    Roles are in a comma-separated list, e.g. Foo,Bar,Baz.
    ---
    group: Roles Commands
    syntax: <role1>[,<role2>...] [@]<username1>[,[@]<username2>...]
    ---
    > `@latexbot removeFromRole Foo tylertian` - Remove Tyler from the "Foo" role.
    > `@latexbot removeFromRole Foo,Bar tylertian latexbot` Remove Tyler and LaTeX Bot from the "Foo" and "Bar" roles.
    """
    try:
        args = shlex.split(args)
    except ValueError as e:
        await chat.send_message(f"Invalid syntax: {e}", bot.msg_creator)
        return
    if len(args) < 2:
        await chat.send_message("Invalid syntax.", bot.msg_creator)
        return

    roles = [r.strip() for r in args[0].split(",")]
    usernames = [username[1:] if username.startswith(
        "@") else username for username in args[1:]]

    for role in roles:
        if not role in bot.roles:
            await chat.send_message(
                f"Error: The role {role} does not exist. Skipping...", bot.msg_creator)
            continue
        
        for username in usernames:
            if not username in bot.roles[role]:
                await chat.send_message(
                    f"Warning: User {username} does not have the role {role}.", bot.msg_creator)
                continue
            bot.roles[role].remove(username)

        # Delete empty roles
        if bot.roles[role]:
            bot.roles.pop(role)
    bot.save_roles()

    await chat.send_message("Operation successful.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_ORG_ADMIN)
async def command_delete_role(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Completely delete a role, removing all users from that role.

    Roles are in a comma-separated list, e.g. Foo,Bar,Baz.
    ---
    group: Roles Commands
    syntax: <role1>[,<role2>...]
    ---
    > `@latexbot deleteRole Foo` - Remove everyone from the role Foo and delete it.
    """
    if args == "":
        await chat.send_message("Error: Please specify at least one role!", bot.msg_creator)
        return
    roles = [r.strip() for r in args.split(",")]
    for role in roles:
        try:
            bot.roles.pop(role)
        except KeyError:
            await chat.send_message(f"Error: The role {role} does not exist. Skipping...", bot.msg_creator)
    bot.save_roles()

    await chat.send_message("Operation successful.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_ORG_ADMIN)
async def command_export_roles(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Export roles data as a JSON. 

    If the data is less than 1000 characters long, it will be sent as a chat message.
    Otherwise it will be sent as a file attachment.
    ---
    group: Roles Commands
    syntax:
    """
    await util.send_json_data(chat, bot.roles.to_dict(), "Roles:", "roles.json", bot.user, bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_ORG_ADMIN)
async def command_import_roles(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Import JSON roles data from the message, or from a file attachment.

    If a file is attached to the message, the roles will always be imported from the file.
    ---
    group: Roles Commands
    syntax: <data|fileattachment>
    ---
    > `@latexbot importRoles {}` - Clear all roles.
    """
    try:
        data = await util.get_attached_json_data(await pyryver.retry_until_available(chat.get_message, msg_id, timeout=5.0), args)
    except ValueError as e:
        await chat.send_message(str(e), bot.msg_creator)
    msg = await pyryver.retry_until_available(chat.get_message, msg_id, timeout=5.0)
    file = msg.get_attached_file()
    if file:
        # Get the actual contents
        try:
            data = (await file.download_data()).decode("utf-8")
        except aiohttp.ClientResponseError as e:
            await chat.send_message(f"Error while trying to GET file attachment: {e}", bot.msg_creator)
            return
        except UnicodeDecodeError as e:
            await chat.send_message(f"File needs to be encoded with utf-8! The following decode error occurred: {e}", bot.msg_creator)
            return
    else:
        data = args
    
    try:
        bot.roles = CaseInsensitiveDict(json.loads(data))
        bot.save_roles()
        await chat.send_message("Operation successful. Use `@latexbot roles` to view the updated roles.", bot.msg_creator)
    except json.JSONDecodeError as e:
        await chat.send_message(f"Error decoding JSON: {e}", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_EVERYONE)
async def command_events(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Display information about ongoing and upcoming events from Google Calendar.

    If the count is not specified, this command will display the next 3 events. 
    This number includes ongoing events.
    ---
    group: Events/Google Calendar Commands
    syntax: [count]
    ---
    > `@latexbot events 5` - Get the next 5 events, including ongoing events.
    """
    try:
        count = int(args) if args else 3
        if count < 1:
            raise ValueError
    except ValueError:
        await chat.send_message("Error: Invalid number.", bot.msg_creator)
        return
    
    events = bot.calendar.get_upcoming_events(count)

    now = util.current_time()
    ongoing = []
    upcoming = []
    
    # Process all the events
    for event in events:
        start = Calendar.parse_time(event["start"])
        end = Calendar.parse_time(event["end"])
        # See if the event has started
        # If the date has no timezone info, make it the organization timezone for comparisons
        if not start.tzinfo:
            start = start.replace(tzinfo=config.timezone)
            # No timezone info means this was created as an all-day event
            has_time = False
        else:
            has_time = True
        if now > start:
            ongoing.append((event, start, end, has_time))
        else:
            upcoming.append((event, start, end, has_time))

    if ongoing:
        resp = "---------- Ongoing Events ----------"
        for evt in ongoing:
            event, start, end, has_time = evt
            # The day number of the event
            day = util.caldays_diff(now, start) + 1
            # If the event does not have a time, then don't include the time
            start_str = datetime.strftime(start, util.DATETIME_DISPLAY_FORMAT if has_time else util.DATE_DISPLAY_FORMAT)
            end_str = datetime.strftime(end, util.DATETIME_DISPLAY_FORMAT if has_time else util.DATE_DISPLAY_FORMAT)
            resp += f"\n# Day *{day}* of {event['summary']} (*{start_str}* to *{end_str}*)"
            if "description" in event and event["description"] != "":
                # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
                resp += f"\u200B:\n{markdownify(event['description'])}"
        resp += "\n\n"
    else:
        resp = ""
    if upcoming:
        resp += "---------- Upcoming Events ----------"
        for evt in upcoming:
            event, start, end, has_time = evt
            # days until the event
            day = util.caldays_diff(start, now)
            # If the event does not have a time, then don't include the time
            start_str = datetime.strftime(start, util.DATETIME_DISPLAY_FORMAT if has_time else util.DATE_DISPLAY_FORMAT)
            end_str = datetime.strftime(end, util.DATETIME_DISPLAY_FORMAT if has_time else util.DATE_DISPLAY_FORMAT)
            if has_time and day == 0:
                hours, seconds = divmod((start - now).seconds, 3600)
                minutes, seconds = divmod(seconds, 60)
                resp += f"\n# {hours}:{minutes:02d} "
            else:
                resp += f"\n# {day} days "
            resp += f"until {event['summary']} (*{start_str}* to *{end_str}*)"
            if "description" in event and event["description"] != "":
                # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
                resp += f"\u200B:\n{markdownify(event['description'])}"
    else:
        resp += "***No upcoming events at the moment.***"

    await chat.send_message(resp, bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_ORG_ADMIN)
async def command_quick_add_event(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Add an event to Google Calendar based on a simple text string.

    Powered by Google Magic. Don't ask me how it works.

    For more details, see [the Google Calendar API Documentation for quickAdd](https://developers.google.com/calendar/v3/reference/events/quickAdd).
    ---
    group: Events/Google Calendar Commands
    syntax: <event>
    ---
    > `@latexbot quickAddEvent Appointment at Somewhere on June 3rd 10am-10:25am`
    """
    event = bot.calendar.quick_add(args)
    start = Calendar.parse_time(event["start"])
    end = Calendar.parse_time(event["end"])
    # Correctly format based on whether the event is an all-day event
    # All day events don't come with timezone info
    start_str = datetime.strftime(start, util.DATETIME_DISPLAY_FORMAT if start.tzinfo else util.DATE_DISPLAY_FORMAT)
    end_str = datetime.strftime(end, util.DATETIME_DISPLAY_FORMAT if end.tzinfo else util.DATE_DISPLAY_FORMAT)
    await chat.send_message(f"Created event {event['summary']} (**{start_str}** to **{end_str}**).\nLink: {event['htmlLink']}", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_ORG_ADMIN)
async def command_add_event(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Add an event to Google Calendar.

    If the event name or start/end time/date contains spaces, surround it with quotes (").

    The description is optional but must be on a new line separate from the rest of the command.
    To type a newline in the chat box, use Shift+Enter.

    The time is optional; if not specified, the event will be created as an all-day event.

    The date must be in one of the formats shown below:
    - YYYY-MM-DD, e.g. 2020-01-01
    - YYYY/MM/DD, e.g. 2020/01/01
    - MMM DD YYYY, e.g. Jan 01 2020
    - MMM DD, YYYY, e.g. Jan 01, 2020

    The time must be in one of the formats shown below:
    - HH:MM, e.g. 00:00
    - HH:MM (AM/PM), e.g. 12:00 AM
    - HH:MM(AM/PM), e.g. 12:00AM
    ---
    group: Events/Google Calendar Commands
    syntax: <name> <startdate> [starttime] <enddate> [endtime] [description on a new line]
    ---
    > `@latexbot addEvent "Foo Bar" 2020-01-01 2020-01-02` - Add an event named "Foo Bar", starting on 2020-01-01 and ending the next day.
    > `@latexbot addEvent "Foo Bar" "Jan 1, 2020" "Jan 2, 2020"` - An alternative syntax for creating the same event.
    > `@latexbot addEvent Foo 2020-01-01 00:00 2020-01-01 12:00` - Add an event named "Foo", starting midnight on 2020-01-01 and ending 12 PM on the same day.
    """
    # If a description is included
    if "\n" in args:
        i = args.index("\n")
        desc = args[i + 1:]
        args = args[:i]
    else:
        desc = None
    try:
        args = shlex.split(args)
    except ValueError as e:
        await chat.send_message(f"Invalid syntax: {e}", bot.msg_creator)
        return
    if len(args) != 3 and len(args) != 5:
        await chat.send_message("Error: Invalid syntax. Check `@latexbot help addEvent` for help. You may have to use quotes if any of the parameters contain spaces.", bot.msg_creator)
        return
    
    # No times specified
    if len(args) == 3:
        start = util.tryparse_datetime(args[1], util.ALL_DATE_FORMATS)
        if not start:
            await chat.send_message(f"Error: The date {args[1]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", bot.msg_creator)
            return
        end = util.tryparse_datetime(args[2], util.ALL_DATE_FORMATS)
        if not end:
            await chat.send_message(f"Error: The date {args[2]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", bot.msg_creator)
            return
        event_body = {
            "start": {
                "date": datetime.strftime(start, util.CALENDAR_DATE_FORMAT),
            },
            "end": {
                "date": datetime.strftime(end, util.CALENDAR_DATE_FORMAT),
            }
        }
    else:
        start_date = util.tryparse_datetime(args[1], util.ALL_DATE_FORMATS)
        if not start_date:
            await chat.send_message(f"Error: The date {args[1]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", bot.msg_creator)
            return
        start_time = util.tryparse_datetime(args[2], util.ALL_TIME_FORMATS)
        if not start_time:
            await chat.send_message(f"Error: The time {args[2]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", bot.msg_creator)
            return

        end_date = util.tryparse_datetime(args[3], util.ALL_DATE_FORMATS)
        if not end_date:
            await chat.send_message(f"Error: The date {args[3]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", bot.msg_creator)
            return
        end_time = util.tryparse_datetime(args[4], util.ALL_TIME_FORMATS)
        if not end_time:
            await chat.send_message(f"Error: The time {args[4]} uses an invalid format. Check `@latexbot help addEvent` for valid formats.", bot.msg_creator)
            return
        
        # Merge to get datetimes
        start = datetime.combine(start_date, start_time.time())
        end = datetime.combine(end_date, end_time.time())
        event_body = {
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": bot.timezone,
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": bot.timezone,
            }
        }
    event_body["summary"] = args[0]
    if desc:
        event_body["description"] = desc
    event = bot.calendar.add_event(event_body)
    start_str = datetime.strftime(start, util.DATETIME_DISPLAY_FORMAT if len(args) == 5 else util.DATE_DISPLAY_FORMAT)
    end_str = datetime.strftime(end, util.DATETIME_DISPLAY_FORMAT if len(args) == 5 else util.DATE_DISPLAY_FORMAT)
    if not desc:
        await chat.send_message(f"Created event {event['summary']} (**{start_str}** to **{end_str}**).\nLink: {event['htmlLink']}", bot.msg_creator)
    else:
        # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
        await chat.send_message(f"Created event {event['summary']} (**{start_str}** to **{end_str}**)\u200B:\n{markdownify(event['description'])}\n\nLink: {event['htmlLink']}", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_ORG_ADMIN)
async def command_delete_event(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Delete an event by name from Google Calendar.

    Note that the event name only has to be a partial match, and is case-insensitive.
    Therefore, try to be as specific as possible to avoid accidentally deleting the wrong event.

    This command can only remove events that have not ended.

    Unlike addEvent, this command only takes a single argument, so quotes should not be used.
    ---
    group: Events/Google Calendar Commands
    syntax: <name>
    ---
    > `@latexbot deleteEvent Foo Bar` - Remove the event "Foo Bar".
    """
    args = args.lower()
    events = bot.calendar.get_upcoming_events()
    matched_event = None
    
    for event in events:
        # Found a match
        if args in event["summary"].lower():
            matched_event = event
            break
    
    if matched_event:
        bot.calendar.remove_event(matched_event["id"])
        # Format the start and end of the event into strings
        start = Calendar.parse_time(matched_event["start"])
        end = Calendar.parse_time(matched_event["end"])
        start_str = datetime.strftime(start, util.DATETIME_DISPLAY_FORMAT if start.tzinfo else util.DATE_DISPLAY_FORMAT)
        end_str = datetime.strftime(end, util.DATETIME_DISPLAY_FORMAT if end.tzinfo else util.DATE_DISPLAY_FORMAT)
        await chat.send_message(f"Deleted event {matched_event['summary']} (**{start_str}** to **{end_str}**).", bot.msg_creator)
    else:
        await chat.send_message("Error: No event matches that name.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_BOT_ADMIN)
async def command_set_enabled(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Enable or disable me.
    ---
    group: Developer Commands
    syntax: true|false
    """
    # The only way this actually gets called is if the user passed neither "true" nor "false"
    await chat.send_message(f"Invalid option: {args}", bot.msg_creator)


KILL_MSGS = [
    "Goodbye, world.",
    "Bleh I'm dead",
    "x_x",
    "Goodbye cruel world",
]


@command.command(access_level=command.Command.ACCESS_LEVEL_BOT_ADMIN)
async def command_kill(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Kill me (:fearful:).

    With the current settings, I will restart a few minutes after being killed.
    Consider using the disable or sleep commands if you intend to disable me.
    ---
    group: Developer Commands
    syntax:
    """
    await chat.send_message(random.choice(KILL_MSGS), bot.msg_creator)
    await bot.shutdown()


@command.command(access_level=command.Command.ACCESS_LEVEL_BOT_ADMIN)
async def command_sleep(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Put me to sleep.

    To wake me back up, use `@latexbot wakeUp` or `@latexbot setEnabled true`.
    ---
    group: Developer Commands
    syntax: <seconds>
    """
    secs = 0
    try:
        secs = float(args)
    except ValueError:
        await chat.send_message("Invalid number.", bot.msg_creator)
        return
    await chat.send_message("Good night! :sleeping:", bot.msg_creator)
    bot.enabled = False
    await bot.session.send_presence_change(pyryver.RyverWS.PRESENCE_AWAY)
    async def _wakeup_task():
        try:
            await asyncio.sleep(secs)
        except asyncio.CancelledError:
            pass
        finally:
            if not bot.enabled:
                bot.enabled = True
                await bot.session.send_presence_change(pyryver.RyverWS.PRESENCE_AVAILABLE)
                await chat.send_message("Good morning!", bot.msg_creator)
    asyncio.create_task(_wakeup_task())


@command.command(access_level=command.Command.ACCESS_LEVEL_MAINTAINER)
async def command_execute(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Execute arbitrary Python code.

    Before you start messing around, keep in mind I run in a Docker container,
    so everything you do here is sandboxed.

    All output to stdout and stderr will be sent as a message after the code finishes executing.

    Best to stay away from this command unless you're a dev.
    ---
    group: Developer Commands
    syntax: <code>
    ---
    > `@latexbot execute print("Hello World")`
    """
    # Temporarily replace stdout and stderr
    stdout = sys.stdout
    stderr = sys.stderr
    # Merge stdout and stderr
    try:
        sys.stdout = io.StringIO()
        sys.stderr = sys.stdout
        exec("async def __aexec_func(bot, chat, user, msg_id, args):\n" + textwrap.indent(args, "    "), globals(), locals()) # pylint: disable=exec-used
        await locals()["__aexec_func"](bot, chat, user, msg_id, args)
        output = sys.stdout.getvalue()
        await chat.send_message(output, bot.msg_creator)
    except Exception: # pylint: disable=broad-except
        await chat.send_message(
            f"An exception has occurred:\n```\n{format_exc()}\n```", bot.msg_creator)
    finally:
        sys.stdout = stdout
        sys.stderr = stderr


@command.command(access_level=command.Command.ACCESS_LEVEL_BOT_ADMIN)
async def command_update_cache(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Update the cached list of forums/teams and users.

    As getting organization data takes time, LaTeX Bot caches this information,
    so when org data is updated, such as when a new user joins, or when a new forum is created,
    LaTeX Bot might fail to recognize it. Run this command to fix it.
    ---
    group: Developer Commands
    syntax:
    """
    await bot.update_cache()
    await chat.send_message("Forums/Teams/Users updated.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_ORG_ADMIN)
async def command_alias(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Manage aliases.

    Aliases allow you to save typing time on a commonly used command.
    They're expanded as if they were a command; therefore, they cannot contain whitespace.

    E.g. If there is an alias `answer` \u2192 `trivia answer`, the command
    `@latexbot answer 1` will expand to `@latexbot trivia answer 1`.
    However, the `answer` in `@latexbot trivia answer` will not be expanded.
    Note that alias expansion happens before command evaluation.

    Aliases can refer to other aliases. However, recursive aliases cannot be evaluated.
    E.g. If `A` \u2192 `B` and `B` \u2192 `C`, both `A` and `B` will expand to `C`.
    However, if `B` \u2192 `A`, both `A` and `B` will fail to evaluate.

    The alias command has 3 actions (sub-commands). They are as follows:
    - No argument: View all aliases.
    - `create [from] [to]` - Create an alias. If the expansion has spaces, it should be surrounded by quotes.
    - `delete [alias]` - Delete an alias.
    ---
    group: Miscellaneous Commands
    syntax: [create|delete] [args]
    ---
    > `@latexbot alias` - View all aliases.
    > `@latexbot alias create "answer" "trivia answer"` - Create an alias `answer` that expands to `trivia answer`.
    > `@latexbot alias delete "answer"` - Delete the alias `answer`.
    """
    if args == "":
        if not config.aliases:
            resp = "No aliases have been created."
        else:
            resp = "All aliases:"
            for alias in config.aliases:
                resp += f"\n* `{alias['from']}` \u2192 `{alias['to']}`"
        await chat.send_message(resp, bot.msg_creator)
        return

    try:
        args = shlex.split(args)
    except ValueError as e:
        await chat.send_message(f"Invalid syntax: {e}", bot.msg_creator)
        return
    if args[0] == "create":
        if len(args) != 3:
            await chat.send_message("Invalid syntax. Did you forget the quotes?", bot.msg_creator)
            return
        config.aliases.append({
            "from": args[1],
            "to": args[2],
        })
        bot.save_config()
        await chat.send_message(f"Successfully created alias `{args[1]}` \u2192 `{args[2]}`.", bot.msg_creator)
    elif args[0] == "delete":
        if len(args) != 2:
            await chat.send_message("Invalid syntax.", bot.msg_creator)
            return
        
        for i, alias in enumerate(config.aliases):
            if alias["from"] == args[1]:
                del config.aliases[i]
                bot.save_config()
                await chat.send_message(f"Successfully deleted alias `{args[1]}`.", bot.msg_creator)
                return
        await chat.send_message("Alias not found!", bot.msg_creator)
    else:
        await chat.send_message("Invalid action. Allowed actions are create, delete and no argument (view).", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_EVERYONE)
async def command_macro(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Manage macros.

    Macros allow LaTeX Bot to automatically replace specific strings in your messages with
    something else. They can be used by putting a dot in front of the macro name, e.g. `.shrug`.
    When a message containing one or more macros is sent, the macros will be automatically expanded
    (replaced with its expansion). They can be used anywhere and any number of times in a message
    and anyone can use them.

    For example, you could create a macro `tableflip` that expands to
    (\u256f\xb0\u25a1\xb0)\u256f\ufe35 \u253b\u2501\u253b. Then, the message "foo .tableflip bar"
    will be expanded to "foo (\u256f\xb0\u25a1\xb0)\u256f\ufe35 \u253b\u2501\u253b bar".

    The macro command has 3 actions (sub-commands). They are as follows:
    - No argument: View all macros.
    - `create [macro] [expansion]` - Create a macro. If the expansion has spaces, it should be
    surrounded by quotes. If the macro already exists, it will be replaced.
    - `delete [macro]` - Delete a macro.

    Macro names can only contain **lowercase letters, numbers and underscores**.

    Note that macros only work in chat messages and not topics or tasks. Once a message is replaced
    with its macro expansion, you can no longer edit it.
    ---
    group: Miscellaneous Commands
    syntax: [create|delete] [args]
    ---
    > `@latexbot macro` - View all macros.
    > `@latexbot macro create tableflip "(\u256f\xb0\u25a1\xb0)\u256f\ufe35 \u253b\u2501\u253b"` - Create a macro named "tableflip".
    > `@latexbot macro delete` - Delete the "tableflip" macro.
    """
    if args == "":
        if not config.macros:
            resp = "No macros have been created."
        else:
            resp = "All macros:"
            for macro, expansion in config.macros.items():
                resp += f"\n* `{macro}` expands to `{expansion}`"
        await chat.send_message(resp, bot.msg_creator)
        return

    try:
        args = shlex.split(args)
    except ValueError as e:
        await chat.send_message(f"Invalid syntax: {e}", bot.msg_creator)
        return
    if args[0] == "create":
        if not await bot.commands.commands["macro create"].is_authorized(bot, chat, user):
            await chat.send_message("You are not allowed to do that.", bot.msg_creator)
            return
        if len(args) != 3:
            await chat.send_message("Invalid syntax. Did you forget the quotes?", bot.msg_creator)
            return
        s = set(args[1])
        if not s.issubset(util.MACRO_CHARS):
            await chat.send_message(f"Invalid character(s) for a macro name: {s - util.MACRO_CHARS}", bot.msg_creator)
            return
        config.macros[args[1]] = args[2]
        bot.save_config()
        await chat.send_message(f"Successfully created macro `{args[1]}` expands to `{args[2]}`.", bot.msg_creator)
    elif args[0] == "delete":
        if not await bot.commands.commands["macro delete"].is_authorized(bot, chat, user):
            await chat.send_message("You are not allowed to do that.", bot.msg_creator)
            return
        if len(args) != 2:
            await chat.send_message("Invalid syntax.", bot.msg_creator)
            return
        if args[1] not in config.macros:
            await chat.send_message("Macro not found!", bot.msg_creator)
            return
        config.macros.pop(args[1])
        bot.save_config()
        await chat.send_message(f"Successfully deleted macro `{args[1]}`.", bot.msg_creator)
    else:
        await chat.send_message("Invalid action. Allowed actions are create, delete and no argument (view).", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_ORG_ADMIN)
async def command_export_config(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Export config as a JSON.

    If the data is less than 1000 characters long, it will be sent as a chat message.
    Otherwise it will be sent as a file attachment.
    ---
    group: Miscellaneous Commands
    syntax:
    """
    data, err = config.dump()
    if err:
        await chat.send_message(err, bot.msg_creator)
    await util.send_json_data(chat, data, "Config:", "config.json", bot.user, bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_ORG_ADMIN)
async def command_import_config(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Import config from JSON.

    Note that although it is encouraged, the config JSON does not have to contain all fields.
    If a field is not specified, it will just be left unchanged.

    If a file is attached to this message, the config will always be imported from the file.
    ---
    group: Miscellaneous Commands
    syntax: <data>
    """
    try:
        errs = config.load(await util.get_attached_json_data(await pyryver.retry_until_available(
            chat.get_message, msg_id, timeout=5.0), args))
        if errs:
            util.log("Error loading config:", errs)
        await bot.reload_config()
        bot.update_help()
        bot.save_config()
        if errs:
            await chat.send_message(errs, bot.msg_creator)
        else:
            await chat.send_message("Operation successful.", bot.msg_creator)
    except ValueError as e:
        await chat.send_message(str(e), bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_ORG_ADMIN)
async def command_access_rule(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    View or modify access rules.

    Access rules are a powerful and flexible way of controlling access to commands.
    They work together with access levels to grant and restrict access.

    Each command may have a number of access rules associated with it. 
    Here are all the types of access rules:
    - `level`: Override the access level of the command. Each access level is represented by a number. See [the usage guide](https://github.com/tylertian123/ryver-latexbot/blob/master/usage_guide.md#access-levels) for more details.
    - `allowUser`: Allow a user to access the command regardless of their access level.
    - `disallowUser`: Disallow a user to access the command regardless of their access level.
    - `allowRole`: Allow users with a role to access the command regardless of their access level.
    - `disallowRole`: Disallow users with a role to access the command regardless of their access level.

    If there is a conflict between two rules, the more specific rule will come on top;
    i.e. rules about specific users are the most powerful, followed by rules about specific roles, and then followed by general access level rules.
    Rules that disallow access are also more powerful than rules that allow access.
    E.g. "disallowRole" overrides "allowRole", but "allowUser" still overrides them both as it's more specific.

    To use this command, you need to specify a command, an action, a rule type and argument(s).
    If none of these arguments are given, this command will print out all access rules for every command.
    If only a command name is given, this command will print out the access rules for that command.

    The command is simply the command for which you want to modify or view the access rules.
    The action can be one of these:
    - `set` - Set the value; **only supported by the `level` rule type and only takes 1 argument**.
    - `add` - Add a value to the list; **not supported by the `level` rule type**.
    - `remove` - Remove a value from the list; **not supported by the `level` rule type**.
    - `delete` - Remove a rule entirely; **does not take any arguments**.

    The rule type is one of the 5 access rule types mentioned above (`level`, `allowUser`, etc).
    The argument(s) are one or more values for the operation, e.g. users to add to the allow list.
    Note that the `set` action can only take one argument.
    
    See the examples below.
    ---
    group: Miscellaneous Commands
    syntax: [command] [action] [ruletype] [args]
    ---
    > `@latexbot accessRule` - View all access rules for every command.
    > `@latexbot accessRule ping` - View access rules for the "ping" command.
    > `@latexbot accessRule ping set level 1` - Set the access level for "ping" to 1 (Forum Admins).
    > `@latexbot accessRule ping delete level` - Undo the command above.
    > `@latexbot accessRule ping add allowUser tylertian foo` - Allow users tylertian and foo to access the ping command regardless of his access level.
    > `@latexbot accessRule ping remove allowUser tylertian foo` - Undo the command above.
    > `@latexbot accessRule ping add allowRole Pingers` - Allow the "pingers" role to access the ping command regardless of their access level.
    > `@latexbot accessRule ping add disallowUser tylertian` - Disallow tylertian from accessing the ping command regardless of his access level.
    """
    if args == "":
        if not config.access_rules:
            await chat.send_message("No access rules were created.", bot.msg_creator)
            return
        resp = "\n\n".join(util.format_access_rules(command, rule) for command, rule in config.access_rules.items())
        await chat.send_message(resp, bot.msg_creator)
        return
    try:
        args = shlex.split(args)
    except ValueError as e:
        await chat.send_message(f"Invalid syntax: {e}", bot.msg_creator)
        return
    # Only command name is given - show access rules
    if len(args) == 1:
        if args[0] not in bot.commands.commands:
            await chat.send_message("Error: Invalid command.", bot.msg_creator)
            return
        if args[0] in config.access_rules:
            await chat.send_message(util.format_access_rules(args[0], config.access_rules[args[0]]), bot.msg_creator)
        else:
            await chat.send_message(f"No access rules for command {args[0]}.", bot.msg_creator)
    # If both command name and action are given, then rule type and args must be given
    elif len(args) < 3:
        await chat.send_message("Invalid syntax! See `@latexbot help accessRule` for details.", bot.msg_creator)
    else:
        # Verify arguments are correct
        if args[0] not in bot.commands.commands:
            await chat.send_message("Error: Invalid command.", bot.msg_creator)
            return
        if args[1] == "set":
            if args[2] != "level":
                await chat.send_message(f"Error: Invalid rule type for action `set`: {args[2]}. See `@latexbot help accessRule` for details.", bot.msg_creator)
                return
            if len(args) != 4:
                await chat.send_message("Error: The `set` action takes exactly 1 argument.", bot.msg_creator)
                return
            try:
                level = int(args[3])
            except ValueError:
                await chat.send_message(f"Error: Invalid access level: {level}. Access levels must be integers. See `@latexbot help accessRule` for details.", bot.msg_creator)
            # Set the rules
            rules = config.access_rules.get(args[0], {})
            rules["level"] = level
            config.access_rules[args[0]] = rules
        # Combine the two because they're similar
        elif args[1] == "add" or args[1] == "remove":
            # Verify rule type
            if args[2] not in ("allowUser", "disallowUser", "allowRole", "disallowRole"):
                await chat.send_message(f"Error: Invalid rule type for action `{args[1]}`: {args[2]}. See `@latexbot help accessRule` for details.", bot.msg_creator)
                return
            if len(args) < 4:
                await chat.send_message(f"Error: At least one argument must be supplied for action `{args[1]}`. See `@latexbot help accessRule` for details.", bot.msg_creator)
                return
            # Set the rules
            rules = config.access_rules.get(args[0], {})
            if args[1] == "add":
                # Handle @mention syntax usernames
                items = [item[1:] if item.startswith("@") else item for item in args[3:]]
                # If there are already items, merge the lists
                if args[2] in rules:
                    for item in items:
                        # Don't allow duplicates
                        if item in rules[args[2]]:
                            await chat.send_message(f"Warning: {item} is already in the list for rule {args[2]}.", bot.msg_creator)
                        else:
                            rules[args[2]].append(item)
                # Otherwise directly assign
                else:
                    rules[args[2]] = items
            else:
                if args[2] not in rules:
                    await chat.send_message(f"Error: Rule {args[2]} is not set for command {args[0]}.", bot.msg_creator)
                    return
                # Remove each one
                for item in args[3:]:
                    if item.startswith("@"):
                        item = item[1:]
                    if item not in rules[args[2]]:
                        await chat.send_message(f"Warning: {item} is not in the list for rule {args[2]}.", bot.msg_creator)
                    else:
                        rules[args[2]].remove(item)
                # Don't leave empty arrays
                if not rules[args[2]]:
                    rules.pop(args[2])
            # Set the field
            # This is needed in case get() returned the empty dict
            config.access_rules[args[0]] = rules
            # Don't leave empty dicts
            if not config.access_rules[args[0]]:
                config.access_rules.pop(args[0])
        elif args[1] == "delete":
            if len(args) != 3:
                await chat.send_message("Error: The `delete` action does not take any arguments.", bot.msg_creator)
                return
            try:
                config.access_rules[args[0]].pop(args[2])
                # Don't leave empty dicts
                if not config.access_rules[args[0]]:
                    config.access_rules.pop(args[0])
            except KeyError:
                await chat.send_message(f"Error: Command {args[0]} does not have rule {args[2]} set.", bot.msg_creator)
                return
        else:
            await chat.send_message(f"Error: Invalid action: {args[1]}. See `@latexbot help accessRule` for details.", bot.msg_creator)
            return
        
        bot.update_help()
        bot.save_config()
        await chat.send_message("Operation successful.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_ORG_ADMIN)
async def command_set_daily_message_time(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Set the time daily messages are sent each day or turn them on/off.

    The time must be in the "HH:MM" format (24-hour clock).
    Leave the argument blank to turn daily messages off.
    ---
    group: Miscellaneous Commands
    syntax: [time]
    ---
    > `@latexbot setDailyMessageTime 00:00` - Set daily messages to be sent at 12am each day.
    > `@latexbot setDailyMessageTime` - Turn off daily messages.
    """
    if args == "" or args.lower() == "off":
        config.daily_msg_time = None
    else:
        # Try parse to ensure validity
        try:
            config.daily_msg_time = datetime.strptime(args, "%H:%M")
        except ValueError:
            await chat.send_message("Invalid time format.", bot.msg_creator)
            return
    
    # Schedule or unschedule the daily message task
    bot.schedule_daily_message()
    
    bot.save_config()
    if config.daily_msg_time:
        await chat.send_message(f"Messages will now be sent at {args} daily.", bot.msg_creator)
    else:
        await chat.send_message("Messages have been disabled.", bot.msg_creator)


@command.command(access_level=command.Command.ACCESS_LEVEL_ORG_ADMIN)
async def command_daily_message(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Send the daily message.

    The daily message is sent automatically each day at a set time if it is turned on
    (through `setDailyMessageTime`). This command can be used to trigger it manually.

    Note that the daily message will be sent to the chats in the config, not the chat
    that this command was invoked from.

    Sending the daily message also updates the cached chats data.
    ---
    group: Miscellaneous Commands
    syntax:
    ---
    > `@latexbot dailyMessage` - Send the daily message.
    """
    if bot.analytics:
        bot.analytics.save()
    await bot.update_cache()
    now = util.current_time()
    events = bot.calendar.get_today_events(now)
    if events:
        resp = "Reminder: These events are happening today:"
        for event in events:
            start = Calendar.parse_time(event["start"])
            end = Calendar.parse_time(event["end"])

            # The event has a time, and it starts today (not already started)
            if start.tzinfo and start > now:
                resp += f"\n# {event['summary']} today at *{start.strftime(util.TIME_DISPLAY_FORMAT)}*"
            else:
                # Otherwise format like normal
                start_str = start.strftime(util.DATETIME_DISPLAY_FORMAT if start.tzinfo else util.DATE_DISPLAY_FORMAT)
                end_str = end.strftime(util.DATETIME_DISPLAY_FORMAT if end.tzinfo else util.DATE_DISPLAY_FORMAT)
                resp += f"\n# {event['summary']} (*{start_str}* to *{end_str}*)"

            # Add description if there is one
            if "description" in event and event["description"] != "":
                # Note: The U+200B (Zero-Width Space) is so that Ryver won't turn ): into a sad face emoji
                resp += f"\u200B:\n{markdownify(event['description'])}"
        await bot.announcements_chat.send_message(resp, bot.msg_creator)
    
    url = f"https://www.checkiday.com/api/3/?d={now.strftime('%Y/%m/%d')}"
    async with aiohttp.request("GET", url) as resp:
        if resp.status != 200:
            util.log(f"HTTP error while trying to get holidays: {resp}")
            data = {
                "error": f"HTTP error while trying to get holidays: {resp}",
            }
        else:
            data = await resp.json()
    if data["error"] != "none":
        await bot.messages_chat.send_message(f"Error while trying to check today's holidays: {data['error']}", bot.msg_creator)
    else:
        if data.get("holidays", None):
            msg = "Here is a list of all the holidays today:\n"
            msg += "\n".join(f"* [{holiday['name']}]({holiday['url']})" for holiday in data["holidays"])
            await bot.messages_chat.send_message(msg, bot.msg_creator)
    comic = await xkcd.get_comic()
    if comic['num'] <= config.last_xkcd:
        util.log(f"No new xkcd found (latest is {comic['num']}).")
    else:
        util.log(f"New comic found! (#{comic['num']})")
        xkcd_creator = pyryver.Creator(bot.msg_creator.name, util.XKCD_PROFILE)
        await bot.messages_chat.send_message(f"New xkcd!\n\n{xkcd.comic_to_str(comic)}", xkcd_creator)
        # Update xkcd number
        config.last_xkcd = comic['num']
        bot.save_config()


@command.command(access_level=command.Command.ACCESS_LEVEL_ORG_ADMIN)
async def command_message(bot: "latexbot.LatexBot", chat: pyryver.Chat, user: pyryver.User, msg_id: str, args: str): # pylint: disable=unused-argument
    """
    Send a message to a chat.
    ---
    group: Hidden Commands
    syntax: [(name|nickname|id|jid)=][+]<forum|team> <message>
    hidden: true
    """
    try:
        i = args.index(" ")
    except ValueError:
        await chat.send_message("Invalid syntax.", bot.msg_creator)
        return
    chat_name = args[:i]
    msg = args[i + 1:]
    try:
        to = util.parse_chat_name(bot.ryver, chat_name)
    except ValueError as e:
        await chat.send_message(str(e), bot.msg_creator)
        return
    if to is None:
        await chat.send_message("Chat not found.", bot.msg_creator)
        return
    await to.send_message(msg, bot.msg_creator)


import latexbot # nopep8 # pylint: disable=unused-import
