# LaTeX Bot Usage Guide

This guide will help you explore the various features of LaTeX Bot.
It covers many important topics that you might find helpful.

For more information about a particular command, do `@latexbot help <command>`.
This guide does not cover all commands, nor does it offer in-depth syntax info for most commands.

This guide is for LaTeX Bot v0.11.0.

# Table of Contents

- [Access Levels](#access-levels)
- [General Usage](#general-usage)
  - [Rendering Math/Chemical Equations](#rendering-mathchemical-equations)
    - [Rendering Simple Equations](#rendering-simple-equations)
  - [Viewing XKCDs](#viewing-xkcds)
  - [Checkiday](#checkiday)
  - [Chat Macros](#chat-macros)
    - [Managing Macros](#managing-macros)
  - [Playing Trivia](#playing-trivia)
    - [Starting a Game](#starting-a-game)
    - [Playing the Game](#playing-the-game)
    - [Ending the Game](#ending-the-game)
    - [Adding Custom Trivia Questions](#adding-custom-trivia-questions)
- [Keyword Watches](#keyword-watches)
  - [Managing Your Keyword Watches](#managing-your-keyword-watches)
    - [Viewing Your Keywords and Configurations](#viewing-your-keywords-and-configurations)
    - [Adding Keywords](#adding-keywords)
    - [Removing Keywords](#removing-keywords)
    - [Turning Keyword Watches Off](#turning-keyword-watches-off)
    - [Suppressing Keyword Watches](#suppressing-keyword-watches)
    - [Setting Your Activity Timeout](#setting-your-activity-timeout)
  - [Keyword Watch JSON Format](#keyword-watch-json-format)
- [The Blue Alliance (TBA) Integration](#the-blue-alliance-tba-integration)
- [Google Calendar Integration](#google-calendar-integration)
  - [Checking Events](#checking-events)
  - [Managing Events](#managing-events)
    - [Adding Events](#adding-events)
    - [Deleting Events](#deleting-events)
- [GitHub Integration](#github-integration)
  - [Update Messages](#update-messages)
  - [Issues/Pull Requests to Ryver Tasks](#issuespull-requests-to-ryver-tasks)
- [Admin Usage](#admin-usage)
  - [Managing Messages](#managing-messages)
    - [`deleteMessages`](#deletemessages)
    - [`moveMessages`](#movemessages)
      - [The Standard Chat Lookup Syntax](#the-standard-chat-lookup-syntax)
    - [`countMessagesSince`](#countmessagessince)
  - [Muting](#muting)
  - [Giving Timeouts](#giving-timeouts)
  - [Roles](#roles)
    - [Viewing Roles](#viewing-roles)
    - [Managing Roles](#managing-roles)
  - [Read-Only Chats](#read-only-chats)
- [Miscellaneous](#miscellaneous)
  - [Daily Message](#daily-message)
  - [Command Aliases](#command-aliases)
    - [Managing Aliases](#managing-aliases)
  - [Command Prefixes](#command-prefixes)
  - [Access Rules](#access-rules)
  - [Updating Cached Chat Data](#updating-cached-chat-data)
  - [Analytics](#analytics)
    - [Analytics JSON Format](#analytics-json-format)
  - [Server](#server)
- [Configuring LaTeX Bot](#configuring-latex-bot)
  - [Advanced Config Items](#advanced-config-items)
  - [Config File Format](#config-file-format)

# Access Levels

First and foremost, each command in LaTeX Bot has a specific "Access Level". This restricts access to sensitive commands such as admin tools. If you're not an admin, then all you need to know is that (obviously) there are some commands that you don't have access to. If you are an admin, read on.

When you do `@latexbot help`, by default it will only list the commands you have access to (use `help all` to list all commands).

(The Access Levels are hierarchical; i.e. normally, users with higher access levels can also access commands available to lower access levels. However, using [Access Rules](#access-rules), Org Admins can set exceptions for specific users and roles, allowing things such as giving a user/role access to a command they normally can't use, or disallowing them from using a command they normally would have access to. Access Rules can also be used to override the access level of a command.)

Additionally, each access level is represented by a number:

1. Everyone - **0**
2. Forum Admins (specific to each forum; a forum admin of one forum has a different Access Level in another forum) - **1**
3. Org Admins - **2**
4. Bot Admins (configurable in the config JSON; see [Configuring LaTeX Bot](#configuring-latex-bot)) - **3**
5. The Maintainer (set via the `LATEXBOT_MAINTAINER_ID` environment variable) - **4**

Where the level increases as you go down the list.

# General Usage

This section outlines commands and topics that are commonly used and (mostly) accessible to everyone.

## Rendering Math/Chemical Equations

Of course, the primary function of LaTeX Bot is to render LaTeX.
You can render an equation with the `render` command,
e.g. `F(s) = \int_{0}^{\infty} f(t) e^{-st} dt` will render the definition of the Laplace Transform.

LaTeX Bot also supports rendering chemical equations with `mhchem`.
Render chemical equations with the `chem` command,
e.g. `@latexbot render HCl_{(aq)} + NaOH_{(aq)} -> H2O_{(l)} + NaCl_{(aq)}` will render the neutralization of hydrochloric acid and sodium hydroxide.

Note that the spaces before and after the plus signs and the arrow are required (blame the `mhchem` package, not me);
if there are no spaces around the arrow, the equation cannot be rendered;
if there are no spaces around the plus signs, they will get rendered as charges instead.

Fun fact: The output colour is grey because it is the only decent-looking colour visible in both light and dark mode.

### Rendering Simple Equations

LaTeX can be quite verbose and a lot to type when you just want to render a simple equation during a discussion.
To solve this problem, LaTeX Bot supports *simple equations*.

Simple equations have a syntax much less verbose and much more intuitive and readable than LaTeX.
For example, the simple equation `sin(sqrt(e^x + a) / 2)` will be converted into LaTeX `\sin\left(\frac{\sqrt{e^{x}+a}}{2}\right)`.

To render a simple equation, use the `renderSimple` command.
For more details on simple equations, see `@latexbot help renderSimple`, or read the simple equation grammar in `latexbot/simplelatex.py`.

## Viewing XKCDs

View the current xkcd or any past xkcd using the `xkcd` command!
If not given arguments, it'll get the latest xkcd.
If given a comic number, it'll try to get that specific comic.

New xkcds (if there is one) are sent each day as part of the Daily Message.
See [Daily Message](#daily-message) for details.

## Checkiday

Check today's holidays (from https://checkiday.com) using the `checkiday` command!
If not given any arguments, it'll print out today's holidays.
If given a specific date (format: YYYY/MM/DD), it'll print out the holidays for that day.

Holidays are sent each day as part of the Daily Message.
See [Daily Message](#daily-message) for details.

## Chat Macros

Macros allow LaTeX Bot to automatically replace specific strings in your messages with something else.
They can be used by putting a dot in front of the macro name, e.g. `.shrug`.
When a message containing one or more macros is sent, the macros will be automatically expanded (replaced with its expansion).
They can be used anywhere and any number of times in a message and anyone can use them.

If you do not want a string to be replaced as a macro, put a backslash before it, e.g. `\.shrug` will not be parsed as a macro.
Because of Ryver's Markdown rendering, the backslash will not be visible in the final message.

### Managing Macros

Admins can add or remove macros with the `macro` command.
Use `@latexbot macro` with no arguments to list all macros.

Use `@latexbot macro create <macro> <expansion>` to create a macro.
The expansion must be surrounded in quotes if it contains a space.
Additionally, macro names can only contain lowercase letters, numbers and underscores.

Use `@latexbot macro delete <macro>` to delete a macro.

By default no macros are defined. Here's a suggested list that you could add:

- `.shrug` - &#x00af;\\\_(&#x30c4;)\_/&#x00af; (Make sure to escape the backslashes and underscores)
- `.tableflip`, `.flip` - (&#x256f;&#xb0;&#x25a1;&#xb0;)&#x256f;&#xfe35; &#x253b;&#x2501;&#x253b;
- `.unflip` - &#x252c;&#x2500;&#x252c;&#x30ce;( &#xba; _ &#xba;&#x30ce;) (escape the underscore)
- `.lenny` - ( &#x0361;&#xb0; &#x035c;&#x0296; &#x0361;&#xb0;)
- `.disapproval` - &#x0ca0;_&#x0ca0; (escape the underscore)
- `.sendlove`, `.love` - (&#x0254;&#x25d4;&#x203f;&#x25d4;)&#x0254; :heart:
- `.megaphone`, `.announcement`, `.scream` - &#x0001f4e3; ('&#x1d17;' )&#x0648;
- `.celebration` - &#xff3c;(&#xff3e;O&#xff3e;)&#xff0f;

## Playing Trivia

Yes, LaTeX Bot has games!
Trivia is a multiplayer game ~~(if you don't have friends, singleplayer is fine too)~~.
However, the game itself doesn't implement any rules, such as turns, etc.
It only provides a scoreboard, so moderation is required if you want an organized game.

Since LaTeX Bot v0.6.0, trivia games are no longer global and are now chat-local.
This means you can have two different games at the same time, as long as they're in different chats.
(This includes forums, teams and private messages.) However, there can only be one trivia game per chat.

The `trivia` command can be used to play trivia, and it has a few sub-commands used to manipulate the game.

### Starting a Game

The `start` sub-command can be used to start a trivia game.
It accepts up to 3 optional arguments, the category, difficulty, and type (true/false or multiple-choice).
For argument, you can do also choose `all` (which is the default).
E.g. `@latexbot trivia start all hard true/false`

You can see all available categories with the `categories` sub-command (does not accept arguments).
Categories may be specified by their number, or by full name (put it in quotes if it contains a space).
Note that custom categories can only be specified by full name. You can also do `custom` for all custom categories.

Note: Choosing `all` for the category does not include any custom questions.
To add or remove custom questions, see [Adding Custom Trivia Questions](#adding-custom-trivia-questions).

For the difficulty, accepted options are `easy`, `medium`, `hard` or `all`.
For the question type, accepted options are `true/false` or `multiple-choice`.

### Playing the Game

Once a game is started, you can do `@latexbot trivia question` or `@latexbot trivia next` to get the next question.

You can answer the questions using reactions.
Click on :one:-:nine: to answer the question (or :white_check_mark: or :x: for true or false questions).
You can also click on :trophy: to view the scoreboard, or :fast_forward: to get the next question after the current question has been answered.

Alternatively, answer using the `answer` sub-command with the answer number, or "true"/"false".
You can get the scoreboard using the `scoreboard` sub-command, and move on to the next question with `question` or `next`.

### Ending the Game

Use `@latexbot trivia end` to end the game.
Only the game "host" (the person who started the game) or a Forum Admin or higher may end the game.
Scores will be announced when the game ends.

Note that the game will automatically end if there is more than 15 minutes of inactivity.
When the game times out, **scores are not announced**.

### Adding Custom Trivia Questions

You can import/export custom trivia questions using the `importCustomQuestions` and `exportCustomQuestions` sub-commands.
Unlike other sub-commands, those commands are only accessible to Org Admins or higher.

Note that `importCustomQuestions` does not merge the input with the current database; it overwrites the current questions.

When importing, you can paste the JSON directly in the command, or attach it as a file attachment if it's over the character limit.

The JSON should have the following format:

```json5
{
  "<category name>": {
    "questions": [
      {
        "category": "<category name>",
        "type": "<question type>", // 'boolean' or 'multiple'
        "difficulty": "<question difficulty>", // 'easy', 'medium' or 'hard'
        "question": "<question text>",
        "correct_answer": "<the correct answer>",
        "incorrect_answers": [
          "<incorrect answer #1>",
          "<incorrect answer #2>"
          // ...
        ]
      }
    ]
    // ...
  }
  // ...
}
```

# Keyword Watches

Keyword watches allow you to set up one or more keywords (which can be multiple words, parts of a word or even symbols)
that you're interested in, so that you're notified each time someone sends a message with your keyword in it.
This allows you to never miss out on conversations of interest.
Keyword watches can be configured through the `@latexbot watch [sub-command] [args]` command.

You can configure keywords to be case-sensitive and/or match whole words only (by default they're neither).
**However, you will not be notified if any of the following are true:**

- Your status is Available (indicated by a green dot; you can change this by clicking on your
  profile in the top left corner)
- The message was sent to a forum or team you are not in
- You turned keyword notifications off using `@latexbot watch off`
- You are considered "active" by LaTeX Bot, i.e. you sent a message recently (by default in the
  last 3 minutes, configurable via `@latexbot watch activityTimeout <seconds>`).
- Keyword watches have been suppressed explicitly through `watch suppress <seconds>` (see below).

Keyword matching is done using a DFA constructed using the Aho-Corasick algorithm to match a large number of keywords at once.

## Managing Your Keyword Watches

### Viewing Your Keywords and Configurations

To view your list of keywords and configuration options, use the command with no arguments (`@latexbot watch`).
This will list all the keywords you have defined as well as any relevant configuration options.

### Adding Keywords

To add a keyword, use the `add <keyword> [match-case] [match-whole-word]` sub-command.
Surround your keyword in quotes if it contains a space.
To make the search case-sensitive or match whole words only, provide `true` or `yes` for `[match-case]` or `[match-whole-word]`.
Likewise, use `false` or `no` to turn these options off. The options are separate for each keyword.
By default, both options are false.

For example, the command `@latexbot watch add "3d printer" false true` will add a watch for the keyword "3d printer", which is case-insensitive and matches whole words only.

### Removing Keywords

To remove a keyword, first list all your keywords with `@latexbot watch`, and then find the number of the keyword you wish to delete.
Then, use `@latexbot watch delete <number>` to delete that keyword.
Alternatively, use `@latexbot watch delete all` to delete *all* keywords.

### Turning Keyword Watches Off

You can turn keyword watches off entirely so you don't receive any notifications by using `@latexbot watch off`.
To turn it back on, use `@latexbot watch on`.

### Suppressing Keyword Watches

To temporarily suppress keyword watch notifications, use `@latexbot watch suppress <seconds>`.
This is completely separate from turning it off/on.
To un-suppress without having to wait the full duration, simply suppress with a duration of 0, i.e. `@latexbot watch suppress 0`.

### Setting Your Activity Timeout

Your activity timeout is how long you're considered "active" for after you send a message.
When you're considered "active", you will not receive keyword watch notifications, even if your status is not Available.
By default, your activity timeout is 3 minutes long, i.e. after sending a message, you will not receive keyword notifications in the next 3 minutes.
You can change this by using `@latexbot watch activityTimeout <seconds>`. Set it to 0 to turn this feature off.

## Keyword Watch JSON Format

By default, keyword watches are stored in `data/keyword_watches.json`. The format of this file is as follows:

```json5
{
  "1234567": { // User ID
    "on": true, // Whether keyword notifications are on
    "activityTimeout": 180.0, // Activity timeout in seconds
    "keywords": [ // A list of keyword objects
      {
        "keyword": "foo", // The keyword
        "wholeWord": true, // Whether to only match whole words
        "matchCase": false // Whether the keyword is case-sensitive
      },
      // ...
    ]
  },
  // ...
}
```

# The Blue Alliance (TBA) Integration

The Blue Alliance (TBA) integration was added in version 0.6.0.
It allows users to query info about FRC teams, districts and events using the `tba <sub-command> [args]` command.

For more details, see the output of `@latexbot help tba`.

Here is a list of supported actions:

- `team <team>` - Get basic team info.
- `teamEvents <team> [year]` - Get info about a team's events.
- `districts [year]` - Get a list of all the districts.
- `districtRankings <district> [year] [range]` - Get the team rankings for a district.
- `districtEvents <district> [year] [week(s)]` - Get the events in a district.
- `event <event> [year]` - Get info about an event.
- `eventRankings <event> [year] [range]` - Get the rankings for an event.

Note that districts and events are specified by code and not name, e.g. "ONT", "ONOSH" (case-insensitive).

For all commands, the word "team" can be abbreviated as "t", "district(s)" can be abbreviated as "d",
"event(s)" can be abbreviated as "e", and "ranking(s)" can be abbreviated as "r". They are also
case-insensitive.
E.g. `districtEvents` can be abbreviated as `dEvents`, `districtE` or `dE`.

Some of these commands make use of *ranges*. A range can be one of the following:

- A single number, e.g. "10" for the top 10 results.
- Two numbers separated by a dash, e.g. "10-20" for the 10th result to the 20th result (inclusive).
- A number followed by a plus, e.g. "10+", for everything after and including the 10th result.

Additionally, if configured, LaTeX Bot will highlight the rows containing information about the team when displaying ranking tables.
This requires the `"frcTeam"` field to be set in the JSON config.

Please see the deployment guide for how to set it up.

# Google Calendar Integration

This section outlines commands and topics related to Google Calendar events integration in LaTeX Bot.

Note: To use Google Calendar Integration, the `"googleCalendarId"` in the config must be set.
See the deployment guide for more details.

## Checking Events

Anyone can check the upcoming events using the `events` command.
By default it only shows 3 events; you can give it a number, the number of events to show.

## Managing Events

You can also add/delete Google Calendar events from LaTeX Bot.
These commands are accessible to Org Admins or higher only.

### Adding Events

There are two ways to add events: with the `addEvent` command, or with the `quickAddEvent` command.

The `addEvent` command has a specific syntax. See its extended help for details.
With the `addEvent` command, you can specify an exact start and end date and time, and an optional description.
The description must be on a new line.

The `quickAddEvent` command on the other hand allows you to add an event with a natural description,
e.g. "Some event happening tomorrow at 1pm".
It uses Google magic (not a part of LaTeX Bot!) to figure it out.
Even though it might be faster, `addEvent` is still the preferred method if you want to specify event details exactly.

### Deleting Events

To delete an event, use the `deleteEvent` command and give it the name of the event you want to delete.

Note: You do not have to give the full name of the event.
E.g. `@latexbot deleteEvent Foo` will delete an event named "Foo Bar".
The name is case-insensitive.

# GitHub Integration

GitHub integration was added in version 0.6.0.
Please see the deployment guide for how to set it up and a list of supported events.

The `"ghUpdatesChat"` field in the config must be set for GitHub updates, and the `"ghIssuesChat"` field must be set for integration with Ryver Tasks.

## Update Messages

Every time an event occurs on GitHub, LaTeX Bot will send a message update to the configured chat.
For example, here's what the message for a push looks like:

> **tylertian123** (*tylertian123@gmail.com*) pushed 2 commit(s) to branch [*master*](https://github.com/tylertian123/cuddly-palm-tree/tree/master) in [**tylertian123/cuddly-palm-tree**](https://github.com/tylertian123/cuddly-palm-tree).
> [Compare Changes](https://github.com/tylertian123/cuddly-palm-tree/compare/b7f3d986fa6f...595fa151b26d)
>
> Commits pushed:
> | Commit | Author | Message |
> | --- | --- | --- |
> [4e1a210](https://github.com/tylertian123/cuddly-palm-tree/commit/4e1a210ce5e4d3150588bb067e8feee776924eba) | **Tyler Tian** (*tylertian123@gmail.com*) | Update README.md
> [595fa15](https://github.com/tylertian123/cuddly-palm-tree/commit/595fa151b26db58a2dcfd141371df79131ab9c94) | **Tyler Tian** (*tylertian123@gmail.com*) | Merge pull request #4 from tylertian123/latexbot-link

## Issues/Pull Requests to Ryver Tasks

When Issues or Pull Requests are opened, closed, assigned, reviewed etc, LaTeX Bot will automatically create or update a Ryver Task in the configured chat.
(Note: If a task board already exists, it **must** be a task board with categories, not a task list.)

The tasks will be created in a new or existing category with the same name as the repository.
For example, if a new issue was created in the "cuddly-palm-tree" repository, a Task with the issue's name and contents will be created under the "cuddly-palm-tree" category.
All Tasks created by LaTeX Bot will be tagged with `#latexbot-github`, and additionally `#issue` or `#pull-request`.
**Do not add or remove the `#latexbot-github` tag manually.**

Any kind of update to the GitHub issue or pull request (e.g. a new comment, being labelled or assigned) will cause the Task to be updated.
Most of these will only result in an automatic comment to the Task, with the exception of a few things:

- Deletion - The task will be deleted
- Closing (or merging) - The task will be completed and archived
- Assignment/unassignment - The corresponding Ryver user will be assigned/unassigned to the Ryver Task
- Labelling/Unlabelling - A tag with the same name as the label will be added/removed from the Task.

Note that in order for assignment/unassignment to work, the assigned GitHub user's username must be present in `"ghUsersMap"` in the config. If the user does not exist in the config, there is no way to find the corresponding Ryver user, so it is not possible to assign/unassign the Ryver Task. By default, LaTeX Bot will also attempt to use the GitHub username to look up the corresponding Ryver user. To modify the GitHub-Ryver username associations (i.e. the `"ghUsersMap"`), use the command `@latexbot linkGitHub <gh-user> <ryver-user>`.

# Admin Usage

This section outlines commands and topics that are designed to help forum/org admins perform administrative tasks.
LaTeX Bot offers powerful functions such as deleting or moving messages and muting users.

## Managing Messages

LaTeX Bot offers 3 admin commands that are useful for managing messages in chat.
They are:

- `deleteMessages`
- `moveMessages`
- `countMessagesSince`

### `deleteMessages`

`deleteMessages` deletes a number or a range of messages.
This is useful for tasks such as cleaning up an unwanted conversation so chats aren't cluttered.

You can pass it a single number, the number of messages to delete, e.g. `@latexbot deleteMessages 10` will delete the last 10 messages.
You can also pass it a range, e.g. `@latexbot deleteMessages 5-10` will delete from the 5th-last message up to and including the 10th-last message.

### `moveMessages`

`moveMessages` "moves" a number or a range of messages to another forum/team.
This is useful for dealing with things such as a conversation in the wrong forum/team or an off-topic conversation that you don't want to delete entirely.

As you can't actually "move" messages, this is accomplished by LaTeX Bot sending a message with the same contents and author to another forum/team, and deleting the original message.
This unfortunately means reactions cannot be moved properly; however, they will still be shown in the moved message with text.

Like `deleteMessages`, `moveMessages` can also accept either a number or a range.
Additionally, you must specify where to move the messages to.
This is done using the Standard Chat Lookup Syntax (see below section).

#### The Standard Chat Lookup Syntax

The Standard Chat Lookup Syntax is specified by the following:

```text
[(name|nickname|username|email|id|jid)=][+|@]<forum|team|user>
```

Essentially, this means that you have several ways of specifying a chat (includes users too!):

- Specify by name directly (e.g. "Programming"), without any additional specifiers.
- Specify by name, nickname, username, email, ID or JID (e.g. "nickname=Prog", "id=1303314").
  You can do this by putting the type of the query parameter before the value, with a = in between, as demonstrated in the examples.
  Note that if you're specifying by chat nickname, it is ok to have the chat nickname start with a + (e.g. "nickname=+Prog").
  This also applies to specifying by username and using an @.
- Specify using the Ryver nickname linking syntax, putting a + before the nickname (e.g. "+Prog").
- Specify using a user mention, putting a @ before the username (e.g. "@tylertian").

Note: When specifying by name directly, queries are *case-sensitive* and must match *exactly* (including any leading/trailing whitespace).
However, when specifying a username, email, or chat nickname, queries are case-insensitive (since these things are case-insensitive in the official app).

Due to implementation details, these queries are *case sensitive* and must match exactly!

### `countMessagesSince`

`countMessagesSince` is a helper command you can use with the other two commands to help you count messages.
You can use it to count the number of messages since the beginning of a conversation, so you can then pass that number to one of the other admin commands.

Use it by providing a search string, e.g. `@latexbot countMessagesSince some words`. The search string is case-insensitive. If it is surrounded with slashes, it is treated as a multiline regex, e.g. `/abc[de]+/`.

## Muting

The `mute` command can be used to temporarily "mute" a user. Since Ryver doesn't allow muting directly, this is achieved by deleting every single message sent by that user immediately. All commands and messages from the user will also be ignored.

Use `@latexbot mute <username> [duration]` to mute a user in the current chat for a specified duration. If the duration is unspecified, they will be muted forever!

Note that muted user information is not persistent. When LaTeX Bot reboots, all users will be unmuted.

See `@latexbot help mute` for more information. Warning: Do **not** try to mute LaTeX Bot!

## Giving Timeouts

Have someone *really* disruptive? Use `@latexbot timeout <username> <duration>` to temporarily **disable** their account! *Please note that with the current implementation, if LaTeX Bot is restarted while a user is in time-out, that user's account will **not** be re-enabled after the period ends.*

This command is very similar to `mute`, but the duration in seconds *must* be specified and cannot be greater than 1 day (86400 seconds).

## Roles

Roles are a powerful feature of LaTeX Bot that allows you to conveniently mention a group of people at the same time.
They work like Discord roles; you can mention all the people with a role just by doing `@RoleName` somewhere in the message,
and LaTeX Bot will automatically replace it with mentions to the correct people.
Using Roles and [Access Rules](#access-rules), you can also grant and restrict access to certain commands for particular roles.

Role names work exactly like regular Ryver usernames.
They are case-insensitive, and can only contain alphanumeric characters and underscores.

If you want to send a literal `@RoleName` and not have LaTeX Bot expand it, you can prefix it with a backslash, e.g. `\@RoleName`.
Because of Ryver's Markdown rendering, the backslash will not be visible in the final message.

### Viewing Roles

You can view roles using the `roles` command.
Without any arguments, `@latexbot roles` will show all roles and users with the roles.
If you provide a username, it will show all the roles a user has, e.g. `@latexbot roles tylertian`.
Or, you can provide a role name to see all users with that role, e.g. `@latexbot roles Programmers`.

### Managing Roles

You can add or remove people from a role using the `addToRole` or `removeFromRole` commands.

The two commands have the exact same syntax.
You can specify multiple roles at once, separated by commas (but not spaces!), and multiple users separated by spaces.
E.g. `@latexbot addToRole Foo,Bar @tylertian @spam @eggs` will give all 3 users both the Foo role and the Bar role.
Note that the `@` before the username is entirely optional.

Note that you don't have to first "create" a role to add people to it, as a role cannot exist without any users.
`addToRole` automatically creates the role if it's not created yet.
`removeFromRole` will automatically delete the role if there are no users left after removing.

Finally, you can delete a role entirely, removing all users from it using the `deleteRole` command.
Just like the other two, you can specify multiple roles at a time by separating them with commas.
And of course, the only difference in syntax between them is that `deleteRoles` doesn't take any usernames.

## Read-Only Chats

Have a forum for announcements that you don't want spam in? Make it a read-only chat so only users with the specified roles can send messages there.

The `@latexbot readOnly` command and its sub-commands can convert a chat into read-only mode. In read-only mode, only users with one of the specified roles may send messages on the chat; messages from all other users will be immediately deleted similarly to `mute`, and they will get a private message explaining why. Unlike `mute`, this setting is persistent; once a chat is in read-only mode, it stays as read-only until configured otherwise.

To make a chat read-only or to add additional allowed roles, use `@latexbot readOnly allow <roles>`. To turn the chat back to normal, use `@latexbot readOnly clear`, or use `@latexbot readOnly clear <roles>` to remove roles from the allowed list. Once all allowed roles are removed, the chat will be automatically converted back to normal.

# Miscellaneous

This section covers miscellaneous features not mentioned in other sections.

## Daily Message

The daily message is sent each day to two chats: the "announcements" chat and the "messages" chat.
In order to specify them you must use `importConfig` and set the fields `"announcementsChat"` and `"messagesChat"`.

Currently, the daily message consists of the following:

- A list of events happening today ([Google Calendar Integration](#google-calendar-integration)), to the "announcements" chat
- A new xkcd, if there is one, to the "messages" chat
- Today's holidays, to the "messages" chat
- A tip of the day

Additionally, the cached data is also updated as part of this routine.
See [Updating Cached Chat Data](#updating-cached-chat-data) for more info.

Org Admins can change the time of day the message is sent using the `setDailyMessageTime` command.
By default, daily messages are sent at 12am each day.
If this command is given the argument "off", daily messages will be turned off.

At the moment, there is no way to customize the contents of the daily message.

Org Admins can change the location of the "announcements" chat and the "messages" chat in the config.
There currently exist no interface to change them directly; they must be changed through editing the config.
See [Configuring LaTeX Bot](#configuring-latex-bot) for details.

## Command Aliases

Command Aliases are a way to save typing time on commands you commonly use, or to create alternate names for commands.
If you've used Git aliases, LaTeX Bot aliases work the exact same way.

Aliases are expanded as if they were a command.
E.g. If there is an alias `answer` &#8594; `trivia answer`, the command `@latexbot answer 1` is equivalent to `@latexbot trivia answer 1`.
Aliases can refer to each other, but cannot be recursive, since that'd cause an infinite loop.
E.g. If there is an alias `A` &#8594; `B`, but `B` is an alias itself to `C`, both `@latexbot A` and `@latexbot B` will be expanded to `@latexbot C`.
However, if there is an alias `recursion` &#8594; `recursion`, it'll fail to evaluate as it results in an infinite loop.
For more details on alias expansion rules, see `@latexbot help alias`.

### Managing Aliases

Org Admins have permission to manage aliases through the `alias` command.

When not given any arguments, the `alias` command will print out all aliases.
This is similar to how the aliases are shown at the end of the general help message.

The alias command supports two actions, `create` and `delete`.
Create an alias using `@latexbot alias create something "something else"`; note the usage of quotes.
Delete an alias using `@latexbot alias delete`.

For more details on the syntax of the command, see `@latexbot help alias`.

## Command Prefixes

Command prefixes let you customize what LaTeX Bot responds to.
Instead of only responding to the default `@latexbot `, you can make it also respond to other names.

For example, adding a command prefix of `!l ` will make it also respond to `!l <command>`.
A command prefix of `/` will make it respond to `/command`, etc.

Command prefixes can only be set through the config file at the moment.
See [Configuring LaTeX Bot](#configuring-latex-bot) for details.

## Access Rules

Access Rules are a powerful and flexible way of controlling access to commands.
They work together with access levels to grant and restrict access.

With Access Rules, Org Admins can control access to commands based on users or roles.
E.g. Allowing users with a certain role to access a command even though their access level might not be high enough.

Each command may have a number of access rules associated with it.
Here are all the types of access rules:

- `level`: Override the access level of the command.
- `allowUser`: Allow a user to access the command regardless of their access level.
- `disallowUser`: Disallow a user to access the command regardless of their access level.
- `allowRole`: Allow users with a role to access the command regardless of their access level.
- `disallowRole`: Disallow users with a role to access the command regardless of their access level.

If there is a conflict between two rules, the more specific rule will come on top;
i.e. rules about specific users are the most powerful, followed by rules about specific roles, and then followed by general access level rules.
Rules that disallow access are also more powerful than rules that allow access.
E.g. "disallowRole" overrides "allowRole", but "allowUser" still overrides them both as it's more specific.

To view and manage Access Rules, use the `accessRule` command or the [Configuration JSON](#configuring-latex-bot).
The syntax of the `accessRule` command is thoroughly explained in `@latexbot help accessRule`.

## Updating Cached Chat Data

In order to make LaTeX Bot boot up faster, the internal data for users/teams/forums are all cached.
This means that they're not automatically updated when a new user/team/forum is created, and as a result, LaTeX Bot may not recognize them.
If this ever happens, run the `updateChats` command to update the cache.

This usually should not be necessary, as the chat cache is updated automatically as part of the daily message routine.
However, disabling daily messages will also disable the automatic refreshes, so this command may be necessary.

## Analytics

You can enable analytics to collect data about usage of LaTeX Bot commands, member message activity, etc.
Enable it by setting the `LATEXBOT_ANALYTICS` env var to a value of `1`.
When enabled, the data is accessible through the web server (see below).
You can access the raw JSON of the data at `/analytics` and the Analytics Dashboard at `/analytics-ui`.

### Analytics JSON Format

By default, the analytics data is stored in a JSON at `data/analytics.json`. The format of this file is as follows:

```json5
{
  "commandUsage": { // Each command's usage by each user
    "ping": { // The name of a command
      "1234567": 1, // How many times the user with that ID has used this command
      // ...
    },
    // ...
  },
  "shutdowns": [ // A list of shutdown and startup times in the last 10 days
    3199892446, // (unix timestamp << 1) + 1 if startup, + 0 if shutdown
    3199893117, // E.g. this one represents a startup event at 1599946558 unix time
    // ...
  ],
  "messageActivity": { // Total message character count for each user
    "1234567": 100, // Total character count of all the messages sent by the user with that ID
  }
}
```

## Server

In order to receive inbound webhooks for GitHub integration, LaTeX Bot hosts a web server.
By default, this is on port 80, and can be changed by specifying the `LATEXBOT_SERVER_PORT` environment variable.
In addition to receiving inbound webhooks, there are also these pages:

- `/config` - Config JSON (read).
- `/roles` - Roles JSON (read).
- `/trivia` - Custom Trivia Questions JSON (read).
- `/analytics` - Analytics Data JSON (if enabled) (read).
- `/analytics-ui` - Analytics Dashboard (if enabled) (read).
- `/message` - UI or POST endpoint for sending messages (write).

To prevent information leakage, LaTeX Bot will ask for credentials when accessing some pages such as `/config` or `/message`.
There are 3 usernames you can login with, `read`, `write` and `admin`, each with a different level of access.
For example, `/config` requires `read` or higher, but `/message` requires `/write` or higher.
The passwords for each of these logins can be set with the environment variables `LATEXBOT_SERVER_AUTH_READ`, `LATEXBOT_SERVER_AUTH_WRITE`, and `LATEXBOT_SERVER_AUTH_ADMIN` respectively.
If the password for a login is not set, it will be disabled.

# Advanced Configuration & Customization

This section outlines the usage of the config file. The config file is a JSON-based configuration tool for LaTeX Bot. The config file allows Org Admins or higher to configure advanced settings that don't have associated commands to edit them.

Working with the configuration file is done through the `importConfig` and `exportConfig` commands.
You can use `importConfig` by directly pasting the JSON data into the command as part of the message, or use a file attachment if it's over the character limit.
Similarly, `exportConfig` will send the config in the message if it's < 1k characters, and otherwise attach it as a file.

## Advanced Config Items

The following items can *only* be changed through updating the config directly:

- Bot Admins
  - Bot Admins have the second highest access level (only below the maintainer). They have access to all administrative *and* developer commands.
- Organization Time Zone
  - Used for sending daily messages and other things.
- Home Chat
  - This is where LaTeX Bot sends its start-up message, among other things.
- Announcements Chat
  - This is where LaTeX Bot sends the daily event reminders.
- Messages Chat
  - This is where LaTeX Bot sends the daily XKCDs, holidays, and Reddit posts.
- Google Calendar ID
  - The calendar LaTeX Bot uses for events integration.
- GitHub integration: Where GitHub updates are sent and where Issues are made into Ryver Tasks.
- Customization:
  - Command Prefixes
    - These allow you to refer to LaTeX Bot using a prefix other than `@latexbot`. For example, a command prefix of `"lb "` would allow you to use LaTeX Bot as `lb <command>`.
  - Custom responses for `whatDoYouThink` for specific items
  - Custom positive/negative responses for `whatDoYouThink`
  - Custom responses for when a user is denied access to a command
- Last XKCD (although this one is set automatically)

## Config File Format

Below is an illustration of the JSON config file format:

```json5
{
  "admins": [ // A list of org admins
    1234567 // Admins are listed by their user ID
    // ...
  ],
  "organizationTimeZone": "EST5EDT", // The timezone of the organization
  "homeChat": "nickname=Test", // The forum/team where startup messages and other misc messages are sent, (Standard Chat Lookup Syntax)
  "announcementsChat": "nickname=Gen", // The forum/team where daily event reminders are sent (Standard Chat Lookup Syntax)
  "messagesChat": "nickname=OffTopic", // The forum/team where daily xkcds and holidays are sent (Standard Chat Lookup Syntax)
  "ghUpdatesChat": "nickname=ProgUpdates", // The forum/team where GitHub updates are sent (Standard Chat Lookup Syntax)
  "ghIssuesChat": "nickname=ProgUpdates", // The forum/team where Tasks are created for GitHub issues and pull requests (Standard Chat Lookup Syntax)
  "googleCalendarId": "foo@group.calendar.google.com", // The ID of the calendar for Google Calendar Integration
  "dailyMessageTime": "00:00", // The time of day daily messages are sent, HH:MM
  "lastXKCD": 0, // The newest XKCD; used to determine if a comic is new; set automatically
  "frcTeam": 6135, // The FRC team of the organization. Used to highlight info in tba.
  "commandPrefixes": [ // A list of command prefixes; see the Command Prefixes section for details
    "@latexbot ", // Note the space is required, otherwise @latexbotping would be parsed as a valid command
    "!l "
    // ...
  ],
  "aliases": [ // A list of command aliases; see the Command Aliases section for details
    {
      "from": "something", // The alias
      "to": "something else", // The thing the alias expands to
    }
    // ...
  ],
  "accessRules": { // All command Access Rules. See the Access Rules section for details
    "ping": { // The Access Rules for a particular command, in this case ping
      "level": 1, // Override the Access Level of this command - see Access Levels and Access Rules
      "allowUser": [1234567], // A list of user IDs to give access to regardless of level - Changed in 0.9.0, used to be a list of usernames
      "disallowUser": [7654321], // A list of user IDs to disallow regardless of level - Changed in 0.9.0, used to be a list of usernames
      "allowRole": ["Pingers"], // A list of roles to give access to regardless of level
      "disallowRole": ["NoPing"] // A list of roles to disallow regardless of level
    }
    // ...
  },
  "opinions": [ // A list of defined responses for whatDoYouThink
    {
      "thing": ["foo", "about foo"], // A list of things this opinion is for. Has to be lowercase!
      "user": ["foo", "bar"], // A list of possible users that also has to be matched; optional
      "opinion": ["An opinion", "Another opinion"] // A list of possible responses from which the response is randomly chosen
    }
    // ...
  ],
  "ghUsersMap": { // A mapping of GitHub usernames to Ryver usernames for Task assignments
    "foobar": "foo_bar"
    // ...
  },
  "macros": { // A mapping of macro names to expansions
    "shrug": "\u00af\\\\_(\u30c4)\\_/\u00af",
    // ...
  },
  "accessDeniedMessages": [ // A list of possible responses when a user tries to access an inaccessible command
    "I'm sorry Dave, I'm afraid I can't do that.",
    // ...
  ],
  "wdytYesMessages": [ // A list of possible positive responses for the whatDoYouThink command
    ":thumbsup:",
    // ...
  ],
  "wdytNoMessages": [ // A list of possible negative responses for the whatDoYouThink command
    ":thumbsup:",
    // ...
  ],
  "readOnlyChats": { // A mapping of chats that are read-only and their allowed roles
    "name=Foo": ["Bar"],
  },
}
```
