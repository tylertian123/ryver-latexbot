import random
import datetime

def generate_random_tip(bot: "latexbot.LatexBot"):
    """
    Pick a latexbot tip from the list of tips (which is nonconfigurable since laziness)
    """

    curdate: datetime.datetime = bot.current_time()

    if curdate.month == 12 and curdate.day == 31:
        return "Did you know today is Matthew's birthday? What do you mean this isn't a tip?"

    TIPS = [
        "Did you know latexbot can run a trivia game? Try the `trivia` command!",
        "latexbot can notify you when someone says a keyword of your choosing; see the `watch` command.",
        "Missing out on important messages? Try the keyword watch mechanism with the `watch` command!",
        "Confused about something in latexbot? Have you checked [the manual?](https://github.com/tylertian123/ryver-latexbot/blob/master/usage_guide.md)",
        "Despite it literally being in the name of the bot, LaTeX rendering still remains the least used feature. Make your sysadmin happy by `render`-ing something today!",
        "Don't like writing obtuse LaTeX expressions? Try the advanced™ simple expression support with `renderSimple sin(x^2)/4`",
        "Discussing chemical equations? latexbot can render them! Try `chem HCl + NaOH -> H2O + NaCl`",
        "Don't want to expand a chat macro? Prefix the dot with a backslash to supress it.",
        "Want to 'improve' your messages? Try adding a chat macro; the list is available in the `macro` command.",
        "Don't want keyword watches to bug you, but you don't want to delete them all? Try the `watch off` command (or `watch supress <time in seconds>`).",
        "Did you know latexbot can talk to TBA? Try out the `tba` command!",
        "Need to schedule an event but you don't want to leave Ryver? latexbot can add calendar events with the `addEvent` and `quickAddEvent` commands!",
        "Curious about what's coming up? Check out upcoming events with the `events` command!",
        "Need to do some censorship? latexbot's got you covered with the `deleteMessages` command.",
        "Need to do some _immediate_ censorship? Exercise your administrative power with the `mute` command.",
        "Unable to stop yourself from chatting? You can always `mute` yourself!",
        "Need to do some chat cleanup? latexbot can help with the `moveMessages` command!",
        "Want to move a bunch of messages but don't want to tediously count them all? Try the `countMessagesSince` (or `cms`) command!",
        "Interested in holidays for a day _other_ than today? Try out the `checkiday` command!",
        "Need a second opinion? Why not ask latexbot with the `whatDoYouThink` (or `wdyt`) command?",
        "Want to see who chats the most? Become unnecessarily competitive with the `leaderboards` command!",
        "Try and `mute` me, I dare you.",
        "Need to _seriously_ censor someone? You can disable their account for up to a day with the `timeout` command.",
        "Don't like typing long command names? You can add aliases with the `alias` command.",
        "Want to be benevolent and let the plebians use privileged commands? Setup access rules as horrendously complex as you desire with the `accessRule` command.",
        "Moving messages but want to keep a few recent ones? `moveMessages` and `deleteMessages` both take ranges: `deleteMessages 4-10` keeps the latest few messages intact!"
    ]

    return random.choice(TIPS)

