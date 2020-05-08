import asyncio
import org
import os
import pyryver
import typing
from latexbot_util import *

# Make print() flush immediately
# Otherwise the logs won't show up in real time in Docker
old_print = print


def print(*args, **kwargs):
    kwargs["flush"] = True
    # Add timestamp
    old_print(current_time().strftime("%Y-%m-%d %H:%M:%S"), *args, **kwargs)


################################ GLOBAL VARIABLES AND CONSTANTS ################################

VERSION = "v0.4.0-dev"

creator = pyryver.Creator(f"LaTeX Bot {VERSION}", "")

enabled = True

# Auto generated later
help_text = ""
extended_help_text = {}


################################ UTILITY FUNCTIONS ################################


def generate_help_text(ryver: pyryver.Ryver):
    global help_text
    help_text = ""
    commands = {}
    for name, command in command_processors.items():
        if command[0].__doc__ == "":
            print(f"Warning: Command {name} has no documentation, skipped")
            continue

        try:
            properties = parse_doc(command[0].__doc__)
            if properties.get("hidden", False) == "true":
                # skip hidden commands
                continue

            # Generate syntax string
            syntax = f"`@latexbot {name} {properties['syntax']}`" if properties["syntax"] else f"`@latexbot {name}`"
            # Generate short description
            description = f"{syntax} - {properties['short_desc']} {ACCESS_LEVEL_STRS[command[1]]}"

            # Group commands
            group = properties['group']
            if group in commands:
                commands[group].append(description)
            else:
                commands[group] = [description]

            extended_description = properties["long_desc"] or "***No extended description provided.***"
            examples = "\n".join(
                "* " + ex for ex in properties["examples"]) if properties["examples"] else "***No examples provided.***"

            description += f"\n\n{extended_description}\n\n**Examples:**\n{examples}"
            extended_help_text[name] = description
        except (ValueError, KeyError) as e:
            print(f"Error while parsing doc for {name}: {e}")

    for group, cmds in commands.items():
        help_text += group + ":\n"
        for description in cmds:
            help_text += f"  - {description}\n"
        help_text += "\n"
    admins = ", ".join([ryver.get_user(id=id).get_name() for id in org.admins])
    if admins:
        help_text += f"\nCurrent Bot Admins are: {admins}."
    else:
        help_text += "\nNo Bot Admins are in the configuration."
    help_text += "\n\nFor more details about a command, try `@latexbot help <command>`."


################################ COMMAND PROCESSORS ################################


async def _ping(chat: pyryver.Chat, s: str):
    """
    I will respond with 'Pong' if I'm here.
    ---
    group: General Commands
    syntax:
    """
    await chat.send_message("Pong", creator)

command_processors = {
    "ping": [_ping, ACCESS_LEVEL_EVERYONE],
}


################################ OTHER FUNCTIONS ################################


async def main():
    print(f"LaTeX Bot {VERSION} has been started. Initializing...")
    # Init Ryver session
    cache = pyryver.FileCacheStorage("data", "latexbot-")
    async with pyryver.Ryver(os.environ["LATEXBOT_ORG"], os.environ["LATEXBOT_USER"], os.environ["LATEXBOT_PASS"], cache) as ryver:
        # Init other stuff
        await ryver.load_missing_chats()
        await org.init(ryver)        
        generate_help_text(ryver)
        # Start live session
        async with ryver.get_live_session() as session:
            @session.on_connection_loss
            async def _on_conn_loss():
                print("Error: Connection lost!")
                session.close()
            
            @session.on_chat
            async def _on_chat(msg: typing.Dict[str, str]):
                text = msg["text"]
                if text.startswith(org.command_prefix) and len(text) > len(org.command_prefix):
                    # Check the sender
                    from_user = ryver.get_user(jid=msg["from"])
                    # Ignore messages sent by us
                    if from_user.get_username() == os.environ["LATEXBOT_USER"]:
                        return
                    to = ryver.get_chat(jid=msg["to"])
                    print(f"Command received from {from_user.get_name()} to {to.get_name()}: {text}")
                    # Check if this is a DM
                    if isinstance(to, pyryver.User):
                        # For DMs special processing is required
                        # Since we don't want to reply to ourselves, reply to the sender directly instead
                        to = from_user
                    
                    # Chop off the beginning
                    text = text[len(org.command_prefix):]
                    # Separate command from args
                    if " " in text or "\n" in text:
                        i = min(text.index(" ") if " " in text else float("inf"), text.index("\n") if "\n" in text else float("inf"))
                        command = text[:i]
                        args = text[i + 1:]
                    else:
                        command = text
                        args = ""
                    
                    if command in command_processors:
                        # Check the access level
                        if not is_authorized(to, from_user, command_processors[command][1]):
                            await to.send_message(get_access_denied_message(), creator)
                            print("Access was denied.")
                        else:
                            await command_processors[command][0](to, args)
                            print("Command processed.")
                    else:
                        print("Invalid command.")
                        await to.send_message(f"Sorry, I didn't understand what you were asking me to do.", creator)

            print("LaTeX Bot is running!")
            await org.home_chat.send_message( 
                f"LaTeX Bot {VERSION} is online! Note that to reduce load, I only check messages once per 3 seconds or more!", creator)
            await org.home_chat.send_message(help_text, creator)

            await session.run_forever()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
