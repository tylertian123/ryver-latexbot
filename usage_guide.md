# LaTeX Bot Usage Guide
This guide will help you explore the various features of LaTeX Bot.
It covers many important topics that you might find helpful.

For more information about a particular command, do `@latexbot help <command>`. 
This guide does not cover all commands, nor does it offer in-depth syntax info for most commands.

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
      - [`countMessagesSince`](#countmessagessince)
    - [Roles](#roles)
      - [Viewing Roles](#viewing-roles)
      - [Managing Roles](#managing-roles)
  - [Miscellaneous](#miscellaneous)
    - [Daily Message](#daily-message)
    - [Command Aliases](#command-aliases)
      - [Managing Aliases](#managing-aliases)
    - [Command Prefixes](#command-prefixes)
    - [Updating Cached Chat Data](#updating-cached-chat-data)
  - [Configuring LaTeX Bot](#configuring-latex-bot)

# Access Levels
Each command in LaTeX Bot has a specific Access Level.
This restricts access to sensitive commands such as admin tools. 

The Access Levels are strictly hierarchical.
A user with a certain access level can also access all commands users with lower level can access.

The access levels go like this:
  1. Everyone
  2. Forum Admins (specific to each forum; a forum admin of one forum has a different Access Level in another forum)
  3. Org Admins
  4. Bot Admins (configurable in the config JSON; see [Configuring LaTeX Bot](#configuring-latex-bot))
  5. Tyler

Where the level increases as you go down the list.

# General Usage
This section outlines commands and topics accessible to everyone.

## Rendering Math/Chemical Equations
Of course, the primary function of LaTeX Bot is to render LaTeX.
You can render an equation with the `render` command, e.g. `@latexbot render \frac{1}{2}` will render the fraction 1/2.

LaTeX Bot also supports rendering chemical equations with `mhchem`.
Render chemical equations with the `chem` command, e.g. `@latex bot render HCl_{(aq)} + NaOH_{(aq)} -> H2O_{(l)} + NaCl_{(aq)}`.
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

All trivia games are global, and there can only ever be one trivia game at a time.

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
For the question type, accepted otpoins are `true/false` or `multiple-choice`.

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
By default, you can provide the forum/team using its display name, e.g. `@latexbot moveMessages Off-Topic`. 
However, you can also provide it using nicknames by using the standard syntax for nickname linking (+), e.g. `@latexbot moveMessages 10 +OffTopic`, 
or specify the lookup method explicitly by putting `name=` or `nickname=` before the name, e.g. `@latexbot moveMessages 10 nickname=OffTopic`.

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

## Updating Cached Chat Data
In order to make LaTeX Bot boot up faster, the internal data for users/teams/forums are all cached.
This means that they're not automatically updated when a new user/team/forum is created, and as a result, LaTeX Bot may not recognize them.
If this ever happens, run the `updateChats` command to update the cache.

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
  ],
  "organizationTimeZone": "EST5EDT", // The timezone of the organization
  "homeChat": "Test", // The nickname of the forum/team where startup messages and other misc messages are sent
  "announcementsChat": "Gen", // The nickname of the forum/team where daily event reminders are sent
  "messagesChat": "OffTopic", // The nickname of the forum/team where daily xkcds and holidays are sent
  "googleCalendarId": "foo@group.calendar.google.com", // The ID of the calendar for Google Calendar Integration
  "dailyMessageTime": "00:00", // The time of day daily messages are sent, HH:MM
  "lastXKCD": 0, // The newest XKCD; used to determine if a comic is new; set automatically
  "commandPrefixes": [ // A list of command prefixes; see the Command Prefixes section for details
    "@latexbot ", // Note the space is required, otherwise @latexbotping would be parsed as a valid command
    "!l "
  ],
  "aliases": [ // A list of command aliases; see the Command Aliases section for details
    {
      "from": "something", // The alias
      "to": "something else", // The thing the alias expands to
    }
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

Congratulations! You've read until the end!

As a reward... If you're an Org Admin, there's a hidden command in LaTeX Bot, `message`, that allows you to send a message to anywhere you want.
The syntax is `@latexbot message <id> <message>`.
You can find the ID of a user by going to their profile, or the ID of a forum/team in the URL of the webpage.
You can use this command in DMs, so it allows you to send completely anonymous messages.
Have fun!