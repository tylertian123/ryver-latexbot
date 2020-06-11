"""
This module contains the main logic for LaTeX Bot.
"""

import commands
import org
import os
import pyryver
from command import Command
from latexbot_util import * # pylint: disable=redefined-builtin
from org import creator
from traceback import format_exc


################################ GLOBAL VARIABLES AND CONSTANTS ################################

enabled = True

################################ UTILITY FUNCTIONS ################################


def preprocess_command(command: str, is_dm: bool):
    """
    Preprocess a command.

    Separate the command into the command name and args and resolve aliases 
    if it is a command. Otherwise return None.

    If it encouters a recursive alias, it raises ValueError.
    """
    is_command = False
    for prefix in org.command_prefixes:
        # Check for a valid command prefix
        if command.startswith(prefix) and len(command) > len(prefix):
            is_command = True
            # Remove the prefix
            command = command[len(prefix):]
    
    # DMs don't require command prefixes
    if not is_command and not is_dm:
        return None
    
    # Repeat until all aliases are expanded
    used_aliases = set()
    while True:
        # Separate command from args
        # Find the first whitespace
        command = command.strip()
        space = None
        # Keep track of this for alias expansion
        space_char = ""
        for i, c in enumerate(command):
            if c.isspace():
                space = i
                space_char = c
                break
        
        if space:
            cmd = command[:space]
            args = command[space + 1:]
        else:
            cmd = command
            args = ""

        # Expand aliases
        command = None
        for alias in org.aliases:
            if alias["from"] == cmd:
                # Check for recursion
                if alias["from"] in used_aliases:
                    raise ValueError(f"Recursive alias: '{alias['from']}'!")
                used_aliases.add(alias["from"])
                # Expand the alias
                command = alias["to"] + space_char + args
                break
        # No aliases were expanded - return
        if not command:
            return (cmd.strip(), args.strip())
        # Otherwise go again until no more expansion happens


################################ OTHER FUNCTIONS ################################


async def main():
    print(f"LaTeX Bot {org.VERSION} has been started. Initializing...")
    # Init Ryver session
    cache = pyryver.FileCacheStorage("data", "latexbot-")
    async with pyryver.Ryver(os.environ["LATEXBOT_ORG"], os.environ["LATEXBOT_USER"], os.environ["LATEXBOT_PASS"], cache=cache) as ryver: # type: pyryver.Ryver
        # Init other stuff
        await ryver.load_missing_chats()
        await org.init(ryver)
        commands.generate_help_text(ryver)
        # Start live session
        async with ryver.get_live_session() as session: # type: pyryver.RyverWS
            @session.on_connection_loss
            async def _on_conn_loss():
                print("Error: Connection lost!")
                await session.close()
            
            @session.on_chat
            async def _on_chat(msg: pyryver.WSChatMessageData):
                # Ignore non-chat messages
                if msg.subtype != pyryver.ChatMessage.SUBTYPE_CHAT_MESSAGE:
                    return

                # Check the sender
                from_user = ryver.get_user(jid=msg.from_jid)
                # Ignore messages sent by us
                if from_user.get_username() == os.environ["LATEXBOT_USER"]:
                    return
                
                # Check if this is a DM
                to = ryver.get_chat(jid=msg.to_jid)
                if isinstance(to, pyryver.User):
                    # For DMs special processing is required
                    # Since we don't want to reply to ourselves, reply to the sender directly instead
                    to = from_user
                    is_dm = True
                else:
                    is_dm = False

                global enabled
                try:
                    preprocessed = preprocess_command(msg.text, is_dm)
                except ValueError as e:
                    # Skip if not enabled
                    if enabled:
                        await to.send_message(f"Cannot process command: {e}", creator)
                    return
                
                if preprocessed:
                    command, args = preprocessed
                    # Processing for re-enabling after disable
                    if command == "setEnabled" and args == "true":
                        # Send the presence change anyways in case it gets messed up
                        await session.send_presence_change(pyryver.RyverWS.PRESENCE_AVAILABLE)
                        if not enabled:
                            enabled = True
                            print(f"Re-enabled by user {from_user.get_name()}!")
                            await to.send_message("I have been re-enabled!", creator)
                        else:
                            await to.send_message("I'm already enabled.", creator)
                        return
                    elif command == "setEnabled" and args == "false" and enabled:
                        enabled = False
                        print(f"Disabled by user {from_user.get_name()}.")
                        await to.send_message("I have been disabled.", creator)
                        await session.send_presence_change(pyryver.RyverWS.PRESENCE_AWAY)
                        return

                    if not enabled:
                        return
                    if is_dm:
                        print(f"DM received from {from_user.get_name()}: {msg.text}")
                    else:
                        print(f"Command received from {from_user.get_name()} to {to.get_name()}: {msg.text}")

                    async with session.typing(to):
                        if command in Command.all_commands:
                            try:
                                if not await Command.process(command, args, to, from_user, msg.message_id):
                                    await to.send_message(Command.get_access_denied_message(), creator)
                                    print("Access Denied")
                                else:
                                    print("Command processed.")
                            except Exception as e: # pylint: disable=broad-except
                                print(f"Exception raised:\n{format_exc()}")
                                await to.send_message(f"An exception occurred while processing the command:\n```{format_exc()}\n```\n\nPlease try again.", creator)
                        else:
                            print("Invalid command.")
                            await to.send_message(f"Sorry, I didn't understand what you were asking me to do.", creator)
                # Not a command
                else:
                    # Check for roles
                    if MENTION_REGEX.search(msg.text):
                        # Replace roles and re-send
                        def replace_func(match):
                            group1 = match.group(1)
                            name = match.group(2)
                            if name in org.roles:
                                name = " @".join(org.roles[name])
                            return group1 + name
                        new_text = MENTION_REGEX.sub(replace_func, msg.text)
                        if new_text != msg.text:
                            # Get the message object
                            to = ryver.get_chat(jid=msg.to_jid)
                            print(f"Role mention received from {from_user.get_name()} to {to.get_name()}: {msg.text}")
                            async with session.typing(to):
                                # Pretend to be the creator
                                msg_creator = pyryver.Creator(
                                    from_user.get_name(), org.user_avatars.get(from_user.get_id(), ""))
                                await to.send_message(new_text, msg_creator)
                            # Can't delete the other person's messages in DMs, so skip
                            if not is_dm:
                                await (await pyryver.retry_until_available(to.get_message, msg.message_id)).delete()
            
            @session.on_chat_updated
            async def _on_chat_updated(msg: pyryver.WSChatUpdatedData):
                # Sometimes updates are sent for things other than message edits
                if msg.text is None:
                    return
                await _on_chat(msg)
            
            @session.on_event(pyryver.RyverWS.EVENT_REACTION_ADDED)
            async def _on_reaction_added(msg: pyryver.WSEventData):
                # Extra processing for interfacing trivia with reactions
                await commands._trivia_on_reaction(ryver, session, msg.event_data)

            print("LaTeX Bot is running!")
            if os.environ.get("LATEXBOT_DEBUG", "0") != "1":
                await org.home_chat.send_message(f"LaTeX Bot {org.VERSION} is online! **I now respond to messages in real time!**\n\n{commands.help_text}", creator)

            await session.run_forever()
