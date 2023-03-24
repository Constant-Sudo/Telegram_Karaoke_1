import cherrypy
import flask_babel
import karaoke
import psutil

import pygame
import qrcode
from unidecode import unidecode

import logging
import constants
import startkaraoke as sk
import threading

from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 5):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, InlineKeyboardButton, InlineKeyboardMarkup, MenuButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

LANGUAGE, NAME = range(2)

SEARCH, SHOW = range(2)
ONE, TWO, THREE, FOUR = range(4)

CHOOSE, EDIT = range(2)
FIVE, SIX, SEVEN, EIGHT, NINE, TEN = range(6)

constants.paused = False
constants.disabled = False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks the user about their Language."""
    reply_keyboard = [["German", "English", "Netherlands"]]

    await update.message.reply_text(
        "Hi! This is the Karaoke Bot for this night. You can look up songs, put them into the queue and be notified, when it's your turn. "
        "Send /cancel to stop."
        "Send /help if you need anything.\n\n"
        "What's your language?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Language?"
        ),
    )

    return LANGUAGE


async def language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("Language of %s: %s", user.first_name, update.message.text)

    context.user_data["language"] = update.message.text

    await update.message.reply_text(
        "Your language is set to: " + str(update.message.text) + "\nWhat's your name?",
        reply_markup=ReplyKeyboardRemove(),
    )

    return NAME


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user

    context.user_data["name"] = update.message.text
    
    await update.message.reply_text(
        str(context.user_data["name"]) + ", Thanks for your name and language.\nFeel free to search for songs and add them to the queue"
    )

    return ConversationHandler.END


async def language_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user

    logger.info("Language Set person: %s is: %s", user.first_name, update.message.text)
    del context.user_data["language"]
    context.user_data["language"] = update.message.text

    await update.message.reply_text(
        "Hello " + str(context.user_data["name"]) + "\n\nYou selected following language:  " + str(update.message.text), reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def newSong(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    if constants.disabled is True: 
        await update.message.reply_text("Search function was deactivated")
        return ConversationHandler.END

    await update.message.reply_text(
        "You can search for any Karaoke Video now. "
        "\nPlease type in your Search: "
    ) 

    return SEARCH


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    user = update.message.from_user
    logger.info("User: %s searched for: %s", context.user_data["name"], update.message.text)


    context.user_data["result_search"] = sk.k.get_karaoke_search_results(update.message.text)
 
    keyboard = [
        [
            InlineKeyboardButton("Queue Video 1", callback_data=str(ONE)),
            InlineKeyboardButton("Queue Video 2", callback_data=str(TWO)),
        ],
        [
            InlineKeyboardButton("Queue Video 3", callback_data=str(THREE)),
            InlineKeyboardButton("Search again", callback_data=str(FOUR)),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Search Results:\n\nVideo 1:" + str(context.user_data["result_search"][0][0]) + "\n" + str(context.user_data["result_search"][0][1]))
    await update.message.reply_text("Search Results:\n\nVideo 2:" + str(context.user_data["result_search"][1][0]) + "\n" + str(context.user_data["result_search"][1][1]))
    await update.message.reply_text("Search Results:\n\nVideo 3:" + str(context.user_data["result_search"][2][0]) + "\n" + str(context.user_data["result_search"][2][1]))

    await update.message.reply_text("Select a Video", reply_markup=reply_markup)
    # await update.message.reply_text("Here are your Search Results:\n\nVideo 1:" + str(search_results[0][0]) + "\n" + str(search_results[0][1]) + "\n\nVideo 2:\n" + str(search_results[1][0]) + "\n" + str(search_results[1][1]) + "\n\nVideo 3:\n" + str(search_results[2][0]) + "\n" + str(search_results[2][1]), reply_markup=reply_markup)

    return SHOW 


async def one(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    
    x = threading.Thread(target=sk.k.download_video, args=[context.user_data["result_search"][0][1], True, context.user_data["name"]])
    x.deamon = True
    x.start()

    await query.answer()
    await query.edit_message_text(text="Song 1 added to the queue. \nHave fun performing later :)")

    return ConversationHandler.END


async def two(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    x = threading.Thread(target=sk.k.download_video, args=[context.user_data["result_search"][1][1], True, context.user_data["name"]])
    x.deamon = True
    x.start()

    await query.answer()
    await query.edit_message_text(text="Song 2 added to the queue. \nHave fun performing later :)")

    return ConversationHandler.END
    

async def three(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    x = threading.Thread(target=sk.k.download_video, args=[context.user_data["result_search"][2][1], True, context.user_data["name"]])
    x.deamon = True
    x.start()

    await query.answer()
    await query.edit_message_text(text="Song 3 added to the queue. \nHave fun performing later :)")

    return ConversationHandler.END


async def four(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    await query.answer()
    await query.edit_message_text(text="Please type in your search: ")

    return SEARCH


async def queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    logger.info("User: %s wants to see the queue", update.message.from_user.first_name)


    if len(sk.k.queue) >= 1:

        songs = ""
        x = sk.k.queue

        for a in x:
            songs = songs + "\n\n" + "Title: " + str(a["title"]) + "\nSinger: " + str(a["user"])

        await update.message.reply_text(
            "Queue:" + songs
        )
    else:
        await update.message.reply_text(
            "Unfortunately there are no songs in the queue. \nFeel free to add some with /newsong"
        )
    return None


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Canceled!", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    user = update.message.from_user
    logger.info("Admin %s skipped a song", user.first_name)

    try:
        sk.k.skip()
    except Exception as e:
        logger.info("Exception - %s", str(e))

    await update.message.reply_text(
        "Skipped this song"
    )


async def volup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    user = update.message.from_user
    logger.info("Admin %s - Volume Up", user.first_name)

    sk.k.url = "https://t.me/this_karaoke_bot"

    try:
        sk.k.vol_up()
    except Exception as e:
        logger.info("Exception - %s", str(e))

    await update.message.reply_text(
        "Increased Volume"
    )


async def voldown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    user = update.message.from_user
    logger.info("Admin %s - Volume Down", user.first_name)

    try:
        sk.k.vol_down()
    except Exception as e:
        logger.info("Exception - %s", str(e))

    await update.message.reply_text(
        "Decreased volume"
    )


async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    logger.info("Admin %s - Pause", user.first_name)

    try:
        sk.k.pause()
    except Exception as e:
        logger.info("Exception - %s", str(e))  

    if constants.paused is False:
        await update.message.reply_text(
            "Paused"
        )
        constants.paused = True
    elif constants.paused is True:    
        await update.message.reply_text(
            "Playing now"
        )
        constants.paused = False


async def addrandom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    
    logger.info("Admin: %s - Adding 3 random songs", user.first_name)

    try: 
        rc = sk.k.queue_add_random(3)
        if rc:
            logger.info("Added 3 random tracks")
            await update.message.reply_text(
                "Successfully Added 3 Tracks"
            )
        else:
            logger.info("Problem with adding tracks")
            await update.message.reply_text(
                "Problem with adding tracks"
            )
    except Exception as e:
        logger.info("Exception - Adding 3 random songs - %s", str(e))

    return None


async def clearqueue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    user = update.message.from_user
    logger.info("Admin %s - Clear Queue", user.first_name)

    try:
        sk.k.queue_clear()
    except Exception as e:
        logger.info("Exception - %s", str(e))

    await update.message.reply_text(
        "Cleared Queue"
    )


async def queueEdit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Admin - Queue Edit by %s", context.user_data["name"])

    if len(sk.k.queue) >= 1:

        songs = ""
        x = sk.k.queue
        number = 0

        for a in x:
            number += 1
            songs = songs + "\n\n" + str(number) + ". Title: " + str(a["title"]) + "\nSinger: " + str(a["user"])

        await update.message.reply_text(
            "Queue:" + songs + "\n\nType in the number of the Song you want to edit (example: 2)"
        )
    else:
        await update.message.reply_text(
            "Unfortunately there are no songs to edit"
        )
        return ConversationHandler.END
    
    return CHOOSE


async def choose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("Admin - Queue Edit by %s - Following Track was choosen: %s", context.user_data["name"], update.message.text)

    print(str(len(sk.k.queue)))

    if update.message.text == "/cancel":
        await update.message.reply_text("Canceled")
        return ConversationHandler.END


    try:
        song_number = int(update.message.text)
        if song_number <= len(sk.k.queue):
            song_number = song_number - 1
            context.user_data["choosen_song"] = sk.k.queue[song_number]["title"] 
        else:
            raise Exception("Krise")
    except:
        await update.message.reply_text("This song doesn't exist or there's an error with your input. Please choose a song which you want to edit (example: 2)")
        return CHOOSE

    keyboard = [
        [
            InlineKeyboardButton("Move Down", callback_data=str(FIVE)),  # <- editing hear One, Two, Three, Four
            InlineKeyboardButton("Move Up", callback_data=str(SIX)),
        ],
        [
            InlineKeyboardButton("Go Back", callback_data=str(SEVEN)),
            InlineKeyboardButton("Delete Song", callback_data=str(EIGHT)),
        ],
        [
            InlineKeyboardButton("Finish Queue Edit", callback_data=str(NINE)),
        ],
        [  
            InlineKeyboardButton("Move to Top", callback_data=str(TEN))
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Editing: \n\nSong: " + str(sk.k.queue[song_number]["title"]) + "\nSinger:" + str(sk.k.queue[song_number]["user"]), reply_markup=reply_markup)

    return EDIT


async def five(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    sk.k.queue_edit(str(context.user_data["choosen_song"]), "down")
    if len(sk.k.queue) >= 1:

        songs = ""
        x = sk.k.queue
        number = 0

        for a in x:
            number += 1
            songs = songs + "\n\n" + str(number) + ". Title: " + str(a["title"]) + "\nSinger: " + str(a["user"])

        await query.edit_message_text(
            "Queue:" + songs + "\n\nType in the number of the Song you want to edit (example: 2)"
        )
    else:
        await query.edit_message_text(
            "Unfortunately there are no songs to edit"
        )
        return ConversationHandler.END

    return CHOOSE


async def six(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    await query.answer()
    sk.k.queue_edit(context.user_data["choosen_song"], "up")
    if len(sk.k.queue) >= 1:

        songs = ""
        x = sk.k.queue
        number = 0

        for a in x:
            number += 1
            songs = songs + "\n\n" + str(number) + ". Title: " + str(a["title"]) + "\nSinger: " + str(a["user"])

        await query.edit_message_text(
            "Queue:" + songs + "\n\nType in the number of the Song you want to edit (example: 2)"
        )
    else:
        await query.edit_message_text(
            "Unfortunately there are no songs to edit"
        )
        return ConversationHandler.END
    return CHOOSE


async def seven(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    await query.answer()
 
    if len(sk.k.queue) >= 1:

        songs = ""
        x = sk.k.queue
        number = 0

        for a in x:
            number += 1
            songs = songs + "\n\n" + str(number) + ". Title: " + str(a["title"]) + "\nSinger: " + str(a["user"])

        await query.edit_message_text(
            "Queue:" + songs + "\n\nType in the number of the Song you want to edit (example: 2)"
        )
    else:
        await query.edit_message_text(
            "Unfortunately there are no songs to edit"
        )
        return ConversationHandler.END

    return CHOOSE


async def eight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    await query.answer()
    sk.k.queue_edit(context.user_data["choosen_song"], "delete")
    if len(sk.k.queue) >= 1:

        songs = ""
        x = sk.k.queue
        number = 0

        for a in x:
            number += 1
            songs = songs + "\n\n" + str(number) + ". Title: " + str(a["title"]) + "\nSinger: " + str(a["user"])

        await query.edit_message_text(
            "Queue:" + songs + "\n\nType in the number of the Song you want to edit (example: 2)"
        )
    else:
        await query.edit_message_text(
            "Unfortunately there are no songs to edit"
        )
        return ConversationHandler.END

    return CHOOSE


async def nine(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    await query.answer()
    await query.edit_message_text("Finished Queue Editing")
    return ConversationHandler.END


async def ten(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: 
    query = update.callback_query
    await query.answer()

    for a in range(len(sk.k.queue)):
        sk.k.queue_edit(str(context.user_data["choosen_song"]), "up")
        print(a)


    if len(sk.k.queue) >= 1:

        songs = ""
        x = sk.k.queue
        number = 0

        for a in x:
            number += 1
            songs = songs + "\n\n" + str(number) + ". Title: " + str(a["title"]) + "\nSinger: " + str(a["user"])

        await query.edit_message_text(
            "Queue:" + songs + "\n\nType in the number of the Song you want to edit (example: 2)"
        )
    else:
        await query.edit_message_text(
            "Unfortunately there are no songs to edit"
        )
        return ConversationHandler.END
    return CHOOSE


async def disable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Disable - Admin: %s", context.user_data["name"])
    
    if constants.disabled is True:
        constants.disabled = False
        await update.message.reply_text("Search is activated")
    elif constants.disabled is False:
        constants.disabled = True
        await update.message.reply_text("Search is deactivated")


async def reboot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Rebooting - Admin: %s", context.user_data["name"])
    th = threading.Thread(target=sk.delayed_halt, args=[2])
    th.start()
    await update.message.reply_text(
        "Rebooting now"
    )


async def change_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Changing Connection - Admin: %s ", context.user_data["name"])
    if constants.changed is False: 
        sk.k.url = constants.BOT_LINK
        constants.changed = True
    elif constants.changed is True:
        sk.k.url = "http://%s:%s" % (sk.k.ip, sk.k.port)
        constants.changed = False

    sk.k.generate_qr_code()

    await update.message.reply_text("Changed Connection Link")
    

def main() -> None:

    persistence = PicklePersistence(filepath="karaokebot")
    application = Application.builder().token(constants.API_KEY).persistence(persistence).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE: [MessageHandler(filters.Regex("^(German|English|Netherlands)$"), language)],
            NAME: [MessageHandler(filters.Text(), name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        persistent=True,
        name="start",
    )

    application.add_handler(conv_handler)

    language_handler = ConversationHandler(
        entry_points=[CommandHandler("language", start)],
        states={
            LANGUAGE: [MessageHandler(filters.Regex("^(German|English|Netherlands)$"), language_select)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        persistent=True,
        name="language",
    )

    application.add_handler(language_handler)

    sear_handler = ConversationHandler(
        entry_points=[CommandHandler("newSong", newSong)],
        states={
            SEARCH: [MessageHandler(filters.TEXT, search)],
            SHOW: [
                CallbackQueryHandler(one, pattern="^" + str(ONE) + "$"),
                CallbackQueryHandler(two, pattern="^" + str(TWO) + "$"),
                CallbackQueryHandler(three, pattern="^" + str(THREE) + "$"),
                CallbackQueryHandler(four, pattern="^" + str(FOUR) + "$"),
            ]


        }, 
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(sear_handler)

    queue_handler = CommandHandler("queue", queue)
    application.add_handler(queue_handler)

    # Admin Befehle
    application.add_handler(CommandHandler("adminskip", skip))
    application.add_handler(CommandHandler("adminvolup", volup))
    application.add_handler(CommandHandler("adminvoldown", voldown))
    application.add_handler(CommandHandler("adminpause", pause))
    application.add_handler(CommandHandler("adminaddrandom", addrandom))
    application.add_handler(CommandHandler("adminclearqueue", clearqueue))
    application.add_handler(CommandHandler("admindisablesearch", disable))
    application.add_handler(CommandHandler("adminreboot", reboot))
    application.add_handler(CommandHandler("adminchangeconnection", change_connection))

    queueEdit_handler = ConversationHandler(
        entry_points=[CommandHandler("adminqueueedit", queueEdit)],
        states={
            CHOOSE: [MessageHandler(filters.TEXT, choose), ],
            EDIT: [
                CallbackQueryHandler(five, pattern="^" + str(FIVE) + "$"),
                CallbackQueryHandler(six, pattern="^" + str(SIX) + "$"),
                CallbackQueryHandler(seven, pattern="^" + str(SEVEN) + "$"),
                CallbackQueryHandler(eight, pattern="^" + str(EIGHT) + "$"),
                CallbackQueryHandler(nine, pattern="^" + str(NINE) + "$"),
                CallbackQueryHandler(ten, pattern="^" + str(TEN) + "$"),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(queueEdit_handler)

    x = threading.Thread(target=sk.main)
    x.start()
    
    application.run_polling()


if __name__ == "__main__":
    main()
