# LaTeX Bot Usage Guide
This guide will help you explore the various features of LaTeX Bot.
It covers many important topics that you might find helpful.

For more information about a particular command, do `@latexbot help <command>`. 
This guide does not cover all commands, nor does it offer in-depth syntax info for most commands.

This guide is for LaTeX Bot v0.6.0.

# Table of Contents
  - [Access Levels](#access-levels)
  - [General Usage](#general-usage)
    - [Rendering Math/Chemical Equations](#rendering-mathchemical-equations)
    - [Viewing XKCDs](#viewing-xkcds)
    - [Checkiday](#checkiday)
    - [Playing Trivia](#playing-trivia)
      - [Starting a Game](#starting-a-game)
      - [Playing the Game](#playing-the-game)
      - [Ending the Game](#ending-the-game)
      - [Adding Custom Trivia Questions](#adding-custom-trivia-questions)
  - [Google Calendar Integration](#google-calendar-integration)
    - [Checking Events](#checking-events)
    - [Managing Events](#managing-events)
      - [Adding Events](#adding-events)
      - [Deleting Events](#deleting-events)
  - [Admin Usage](#admin-usage)
    - [Chat Admin Commands](#chat-admin-commands)
      - [`deleteMessages`](#deletemessages)
      - [`moveMessages`](#movemessages)
        - [The Standard Chat Lookup Syntax](#the-standard-chat-lookup-syntax)
      - [`countMessagesSince`](#countmessagessince)
    - [Roles](#roles)
      - [Viewing Roles](#viewing-roles)
      - [Managing Roles](#managing-roles)
  - [Miscellaneous](#miscellaneous)
    - [Daily Message](#daily-message)
    - [Command Aliases](#command-aliases)
      - [Managing Aliases](#managing-aliases)
    - [Command Prefixes](#command-prefixes)
    - [Access Rules](#access-rules)
    - [Updating Cached Chat Data](#updating-cached-chat-data)
  - [Configuring LaTeX Bot](#configuring-latex-bot)

# Access Levels
Each command in LaTeX Bot has a specific Access Level.
This restricts access to sensitive commands such as admin tools. 

The Access Levels are strictly hierarchical;
i.e. normally, users with higher access levels can also access commands available to lower access levels.
However, using [Access Rules](#access-rules), Org Admins can set exceptions for specific users and roles,
allowing things such as giving a user/role access to a command they normally can't use, or disallowing them from using a command they normally would have access to.
Access Rules can also be used to override the access level of a command.

Additionally, each access level is represented by a number internally; this is only used when configuring Access Rules.
The access levels go like this:
  1. Everyone - **0**
  2. Forum Admins (specific to each forum; a forum admin of one forum has a different Access Level in another forum) - **1**
  3. Org Admins - **2**
  4. Bot Admins (configurable in the config JSON; see [Configuring LaTeX Bot](#configuring-latex-bot)) - **3**
  5. Tyler - **9001**

Where the level increases as you go down the list.

# General Usage
This section outlines commands and topics accessible to everyone.

## Rendering Math/Chemical Equations
Of course, the primary function of LaTeX Bot is to render LaTeX.
You can render an equation with the `render` command, 
e.g. `F(s) = \int_{0}^{\infty} f(t) e^{-st} dt` will render the definition of the Laplace Transform.

LaTeX Bot also supports rendering chemical equations with `mhchem`.
Render chemical equations with the `chem` command, 
e.g. `@latex bot render HCl_{(aq)} + NaOH_{(aq)} -> H2O_{(l)} + NaCl_{(aq)}` will render the neutralization of hydrochloric acid and sodium hydroxide.
Note that the spaces before and after the plus signs and the arrow are required; 
if there are no spaces around the arrow, the equation cannot be rendered;
if there are no spaces around the plus signs, they will get rendered as charges instead.

Fun fact: The output colour is grey because it is the only decent-looking colour visible in both light and dark mode.

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

# Google Calendar Integration
This section outlines commands and topics related to Google Calendar events integration in LaTeX Bot.

Note: To use Google Calendar Integration, the `"googleCalendarId"` in the config must be set.

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

# Admin Usage
This section outlines commands and topics that are designed to help forum/org admins perform administrative tasks.

## Chat Admin Commands
LaTeX Bot offers 3 admin commands that are useful for chat administration.
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
```
[(name|nickname|id|jid)=][+]<forum|team>
```
Essentially, this means that you have several ways of specifying a chat (includes users too!):
  - Specify by name directly (e.g. "Programming"), without any additional specifiers.
  - Specify by name, nickname, ID or JID (e.g. "nickname=Prog", "id=1303314").
    You can do this by putting the type of the query parameter before the value, with a = in between, as demonstrated in the examples. 
    Note that if you're specifying by nickname (and *only* nickname), it is ok to have the nickname starting with a + (e.g. "nickname=+Prog").
  - Specify using the Ryver nickname linking syntax, putting a + before the nickname (e.g. "+Prog").

Note that due to implementation details, these queries are *case sensitive* and must match exactly!

### `countMessagesSince`
`countMessagesSince` is a helper command you can use with the other two commands to help you count messages.
You can use it to count the number of messages since the beginning of a conversation, so you can then pass that number to one of the other admin commands.

Use it by providing a search string, e.g. `@latexbot countMessagesSince some words`.
The search string is case-insensitive.
If it is surrounded with slashes, it is treated as a multiline regex.

## Roles
Roles are a powerful feature of LaTeX Bot that allows you to conveniently mention a group of people at the same time.
They work like Discord roles; you can mention all the people with a role just by doing `@RoleName` somewhere in the message,
and LaTeX Bot will automatically replace it with mentions to the correct people.
Using Roles and [Access Rules](#access-rules), you can also grant and restrict access to certain commands for particular roles.

Role names work exactly like regular Ryver usernames.
They are case-insensitive, and can only contain alphanumeric characters and underscores. 

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

# Miscellaneous
This section covers features not covered in other sections.

## Daily Message
The daily message is sent each day to two chats: the "announcements" chat and the "messages" chat.

Currently, the daily message consists of the following:
  - A list of events happening today ([Google Calendar Integration](#google-calendar-integration)), to the "announcements" chat
  - A new xkcd, if there is one, to the "messages" chat
  - Today's holidays, to the "messages" chat

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
Aliases can be nested, but cannot be recursive.
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

# Configuring LaTeX Bot
This section outlines the usage of the config file.

The config file is a JSON-based configuration tool for LaTeX Bot.
With it, Org Admins can edit settings that can't be edited through conventional means.

Working with the configuration file is done through the `importConfig` and `exportConfig` commands.
You can use `importConfig` by directly pasting the JSON data into the command as part of the message, or use a file attachment if it's over the character limit.
Similarly, `exportConfig` will send the config in the message if it's < 1k characters, and otherwise attach it as a file.

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
  "googleCalendarId": "foo@group.calendar.google.com", // The ID of the calendar for Google Calendar Integration
  "dailyMessageTime": "00:00", // The time of day daily messages are sent, HH:MM
  "lastXKCD": 0, // The newest XKCD; used to determine if a comic is new; set automatically
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
      "allowUser": ["foo", "bar"], // A list of users to give access to regardless of level
      "disallowUser": ["baz"], // A list of users to disallow regardless of level
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
  ]
}
```

Out of these configuration options, these can *only* be changed through updating the config directly:
  - Bot Admins
  - Organization Time Zone
  - Home Chat
  - Announcements Chat
  - Messages Chat
  - Google Calendar ID
  - Last XKCD (although this one is set automatically)
  - Command Prefixes
  - Opinions

Congratulations! You've read until the end!

Hint: There's a hidden command in LaTeX Bot, `message`, that allows admins to send a message to anywhere they want (including user DMs).
The syntax is `@latexbot message [(name|nickname|id|jid)=][+]<forum|team> <message>`.
(The chat is specified using the [Standard Chat Lookup Syntax](#the-standard-chat-lookup-syntax).)
