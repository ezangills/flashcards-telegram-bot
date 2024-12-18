import configparser
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ForceReply
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
)
from services import DatabaseManager
import random


user_learning_sessions = {}  # user_id -> {"cards": [], "current_step": 0, "current_card_index": 0}
user_general_session = {}
config = configparser.ConfigParser()
config.read("token.properties")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Flashcards Bot!\nUse /help to see commands.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(all_commands())


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if (update.message.from_user.id not in user_general_session):
        user_general_session[update.message.from_user.id] = {}
    keyboard = [
        [InlineKeyboardButton("List Decks", callback_data=f"command_switch_deck"), InlineKeyboardButton("Add a Deck", callback_data=f"command_add_deck")]
    ]
    await update.message.reply_text(text="Menu", reply_markup=InlineKeyboardMarkup(keyboard))


async def list_decks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = DatabaseManager(update.message.from_user.id)
    deck_ids = [deck.id for deck in sorted(db.decks, key=lambda deck: deck.name)]
    deck_names = [deck.name for deck in sorted(db.decks, key=lambda deck: deck.name)]
    if (update.message.from_user.id not in user_general_session):
        user_general_session[update.message.from_user.id] = {}

    user_general_session[update.message.from_user.id]["page"] = 0
    page = user_general_session[update.message.from_user.id]["page"]
    if deck_ids:
        keyboard = __list_decks(deck_ids, deck_names, page)
        await update.message.reply_text(text="Pick a Deck", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("No decks available.")
        await show_menu(update, context)


async def present_next_card(update: Update, user_id, context: ContextTypes.DEFAULT_TYPE):
    session = user_learning_sessions.get(user_id)

    if not session:
        await update.message.reply_text("No active learning session. Use /learn <deck_name> to start.")
        return

    cards = session["cards"]
    current_index = session["current_card_index"]

    if current_index >= len(cards):
        # Move to the next step if all cards are reviewed in the current step
        session["current_card_index"] = 0
        session["current_step"] += 1

        if session["current_step"] > 5:
            # End the session and show results after all steps are complete
            await show_results(update, context)
            return

    # Get the current card
    card = cards[session["current_card_index"]]
    current_step = session["current_step"]

    if current_step == 1:
        # Step 1: Multiple-choice for backs
        options = generate_options(card, cards, "back")
        message = f"Step 1: What is the back for: '{card.front}'?"
        await send_options(update, context, message, options, card.back, card.id)

    elif current_step == 2:
        # Step 2: Matching cards (front and back)
        message = f"Step 2: Match the front '{card.front}' with the correct back."
        back_options = [c.back for c in cards]
        await send_options(update, context, message, back_options, card.back, card.id)

    elif current_step == 3:
        # Step 3: Multiple-choice for fronts
        options = generate_options(card, cards, "front")
        message = f"Step 3: What is the front for: '{card.back}'?"
        await send_options(update, context, message, options, card.front, card.id)

    elif current_step == 4:
        # Step 4: Typing the back
        message = f"Step 4: Type the back for: '{card.front}'"
        session["correctCard"] = card
        await update.message.reply_text(
            text=message,
            reply_markup=ForceReply()
        )

    elif current_step == 5:
        # Step 5: Typing the front
        message = f"Step 5: Type the front for: '{card.back}'"
        session["correctCard"] = card
        await update.message.reply_text(
            text=message,
            reply_markup=ForceReply()
        )

    # Move to the next card in the session
    session["current_card_index"] += 1


async def send_options(update, context, question, options, correct_option, correct_card_id):
    keyboard = [
        [InlineKeyboardButton(option, callback_data=("correct_" + correct_card_id if option == correct_option else "incorrect_" + correct_card_id))]
        for option in options
    ]

    if update.message:  # If called from a standard message
        await update.message.reply_text(
            text=question,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.callback_query:  # If called from a callback query
        await update.callback_query.message.reply_text(
            text=question,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    session = user_learning_sessions.get(user_id)
    cards = session["cards"]
    db = DatabaseManager(user_id)

    results = []
    for card in cards:
        progress = session["progress"][card.id]
        correct = progress["correct"]
        incorrect = progress["incorrect"]

        # Update card level based on answers
        if correct >= 3 and card.level < 6:
            card.level += 1
        if incorrect >= 4 and card.level > 0:
            card.level -= 1

        results.append(f"Card '{card.front}' - Correct: {correct}, Incorrect: {incorrect}, Level: {card.level}")
        db.edit_card(user_general_session[update.message.from_user.id]["deck_name"], card.front, card.back, card.level, user_id)
    # Display results
    keyboard = [
        [InlineKeyboardButton("Switch Deck", callback_data=f"command_switch_deck"), InlineKeyboardButton("Learn", callback_data=f"command_learn_deck")],
        [InlineKeyboardButton("Add Cards", callback_data=f"command_add_cards_to_deck"), InlineKeyboardButton("Delete Cards", callback_data=f"command_delete_cards_in_deck")],
        [InlineKeyboardButton("Add a Deck", callback_data=f"command_add_deck"), InlineKeyboardButton("Delete a Deck", callback_data=f"command_delete_deck")]
    ]
    result_message = "Learning Session Complete! Results:\n" + "\n".join(results) + "Current Deck: " + user_general_session[user_id]["deck_name"]
    await update.message.reply_text(
        text=result_message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    user_learning_sessions.pop(user_id, None)  # Clear the session


async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    session = user_learning_sessions.get(user_id)

    if not session:
        await update.message.reply_text("No active learning session.")
        return

    cards = session["cards"]
    current_index = session["current_card_index"] - 1  # Step moves the index forward
    card = cards[current_index]

    current_step = session["current_step"]
    user_response = update.message.text.strip()

    if current_step == 4 and user_response == card.back:
        await update.message.reply_text("Correct! (test)")
        #update_card_progress(session, card, True)
    elif current_step == 5 and user_response == card.front:
        await update.message.reply_text("Correct! (test)")
        #update_card_progress(session, card, True)
    else:
        correct_answer = card.back if current_step == 4 else card.front
        await update.message.reply_text(f"Incorrect. The correct answer is: {correct_answer} (test)")
        #update_card_progress(session, card, False)

    # Continue to the next card or step
    await present_next_card(update, user_id, context)


async def handle_name_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if this is a reply to the ForceReply prompt
    user_id = update.message.from_user.id
    db = DatabaseManager(user_id)
    session = user_learning_sessions.get(user_id)
    correctCard = None

    if session is not None:
        if "correctCard" in session:
            correctCard = session["correctCard"]
    if update.message.reply_to_message and "Enter Deck Name" == update.message.reply_to_message.text:
        deck_name = update.message.text  # The user's input
        if db.add_deck(deck_name, user_id):
            await update.message.reply_text(f"Deck '{deck_name}' created.")
        else:
            await update.message.reply_text(f"Deck '{deck_name}' already exists.")
    if update.message.reply_to_message and "Enter Deck Name that you want to DELETE" == update.message.reply_to_message.text:
        deck_name = update.message.text
        if db.get_deck(deck_name):
            db.delete_deck(deck_name, user_id)
            await update.message.reply_text(f"Deck '{deck_name}' deleted.")
        else:
            await update.message.reply_text(f"Deck '{deck_name}' not found.")
    if "deck_name" in user_general_session[user_id]:
        if update.message.reply_to_message and "Type in FRONT (Deck: " + user_general_session[user_id]["deck_name"] + ")" == update.message.reply_to_message.text:
            user_general_session[user_id]["front"] = update.message.text
            await update.message.reply_text(
                text="Type in BACK (Deck: " + user_general_session[user_id]["deck_name"] + ")",
                reply_markup=ForceReply()
            )
            return
        if update.message.reply_to_message and "Type in BACK (Deck: " + user_general_session[user_id]["deck_name"] + ")" == update.message.reply_to_message.text:
            front = user_general_session[user_id]["front"]
            back = update.message.text
            db.add_card(user_general_session[user_id]["deck_name"], front, back, user_id)
            await update.message.reply_text("Card has been added to Deck " + user_general_session[user_id]["deck_name"] + " and saved.")
            await update.message.reply_text(
                text="Type in FRONT (Deck: " + user_general_session[user_id]["deck_name"] + ")",
                reply_markup=ForceReply()
            )
            return
    if correctCard:
        if update.message.reply_to_message and f"Step 4: Type the back for: '{correctCard.front}'" == update.message.reply_to_message.text:
            back = update.message.text
            if correctCard.back == back:
                user_learning_sessions[user_id]["progress"][correctCard.id]["correct"] += 1
                await update.message.reply_text("Correct! ✅")
            else:
                user_learning_sessions[user_id]["progress"][correctCard.id]["incorrect"] += 1
                await update.message.reply_text("Incorrect. ❌")
            await present_next_card(update, user_id, context)
            return
        if update.message.reply_to_message and f"Step 5: Type the front for: '{correctCard.back}'" == update.message.reply_to_message.text:
            front = update.message.text
            if correctCard.front == front:
                user_learning_sessions[user_id]["progress"][correctCard.id]["correct"] += 1
                await update.message.reply_text("Correct! ✅")
            else:
                user_learning_sessions[user_id]["progress"][correctCard.id]["incorrect"] += 1
                await update.message.reply_text("Incorrect. ❌")
            await present_next_card(update, user_id, context)
            return

    await show_menu(update, context)


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    db = DatabaseManager(user_id)

    if query.data == "command_add_deck":
        await query.message.reply_text(
            text="Enter Deck Name",
            reply_markup=ForceReply()
        )
        return
    if query.data == "command_delete_deck":
        await query.message.reply_text(
            text="Enter Deck Name that you want to DELETE",
            reply_markup=ForceReply()
        )
        return
    if query.data == "command_add_cards_to_deck":
        await query.message.reply_text(
            text="Type in FRONT (Deck: " + user_general_session[user_id]["deck_name"] + ")",
            reply_markup=ForceReply()
        )
        return
    if query.data == "command_delete_cards_in_deck" or query.data.startswith("page_ce_"):
        page_ce = 0
        if query.data.startswith("page_ce_"):
            page_ce = query.data.split("page_ce_")[1]
        cards = db.select_cards(user_general_session[user_id]["deck_name"])
        keyboard_ce = __list_cards(cards, page_ce)
        await query.edit_message_text(text="Delete card from Deck " + user_general_session[user_id]["deck_name"], reply_markup=InlineKeyboardMarkup(keyboard_ce))
        return
    if query.data == "command_switch_deck":
        db = DatabaseManager(user_id)
        deck_ids = [deck.id for deck in sorted(db.decks, key=lambda deck: deck.name)]
        deck_names = [deck.name for deck in sorted(db.decks, key=lambda deck: deck.name)]
        if (user_id not in user_general_session):
            user_general_session[user_id] = {}

        user_general_session[user_id]["page"] = 0
        page = user_general_session[user_id]["page"]
        if deck_ids:
            keyboard = __list_decks(deck_ids, deck_names, page)
            await query.edit_message_text(text="Pick a Deck", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text("No decks available.")
            await show_menu(query, context)
        return
    if query.data == "command_learn_deck":
        deck_name = user_general_session[user_id]["deck_name"]
        cards = db.select_cards_for_learning(deck_name)
        if not cards:
            await query.message.reply_text(f"No cards available for learning in deck '{deck_name}'.")
            return

        user_learning_sessions[user_id] = {
            "cards": cards,
            "current_step": 1,
            "current_card_index": 0,
            "progress": {}
        }

        for card in cards:
            user_learning_sessions[user_id]["progress"][card.id] = {}
            user_learning_sessions[user_id]["progress"][card.id]["correct"] = 0
            user_learning_sessions[user_id]["progress"][card.id]["incorrect"] = 0

        await query.message.reply_text(f"Starting learning session for deck '{deck_name}'.")

        # Proceed to the first card
        await present_next_card(query, user_id, context)
        return
    if query.data.startswith("deck_"):
        if (user_id not in user_general_session):
            user_general_session[user_id] = {}

        deck_id = query.data.split("deck_")[1]
        for deck in db.decks:
            if deck.id == deck_id:
                user_general_session[user_id]["deck_name"] = deck.name
        keyboard = [
            [InlineKeyboardButton("Switch Deck", callback_data=f"command_switch_deck"), InlineKeyboardButton("Learn", callback_data=f"command_learn_deck")],
            [InlineKeyboardButton("Add Cards", callback_data=f"command_add_cards_to_deck"), InlineKeyboardButton("Delete Cards", callback_data=f"command_delete_cards_in_deck")],
            [InlineKeyboardButton("Add a Deck", callback_data=f"command_add_deck"), InlineKeyboardButton("Delete a Deck", callback_data=f"command_delete_deck")]
        ]
        await query.edit_message_text(
            text="Current Deck: " + user_general_session[user_id]["deck_name"],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    if query.data.startswith("page_"):
        page = int(query.data.split("page_")[1])
        deck_ids = [deck.id for deck in sorted(db.decks, key=lambda deck: deck.name)]
        deck_names = [deck.name for deck in sorted(db.decks, key=lambda deck: deck.name)]
        keyboard = __list_decks(deck_ids, deck_names, page)
        await query.edit_message_text(text="Pick a Deck", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    if query.data.startswith("delete_card_"):
        id = (query.data.split("delete_card_")[1])
        db.delete_card(user_general_session[user_id]["deck_name"], id, user_id)
        cards = db.select_cards(user_general_session[user_id]["deck_name"])
        keyboard_ce = __list_cards(cards, 0)
        await query.message.reply_text("Card has been deleted from Deck " + user_general_session[user_id]["deck_name"] + ".")
        await query.edit_message_text(text="Delete card from Deck " + user_general_session[user_id]["deck_name"], reply_markup=InlineKeyboardMarkup(keyboard_ce))
        return
    if query.data.startswith("correct_"):
        user_learning_sessions[user_id]["progress"][query.data.split("correct_")[1]]["correct"] += 1
        await query.edit_message_text("Correct! ✅")
    if query.data.startswith("incorrect"):
        user_learning_sessions[user_id]["progress"][query.data.split("incorrect_")[1]]["incorrect"] += 1
        await query.edit_message_text("Incorrect. ❌")

    # Proceed to the next card
    session = user_learning_sessions.get(user_id)
    await present_next_card(query, user_id, context)


def __list_cards(cards, page_ce):
    items_per_page_ce = 5
    total_pages_ce = int(len(cards) / items_per_page_ce)
    start_index_ce = int(page_ce) * items_per_page_ce
    end_index_ce = start_index_ce + items_per_page_ce
    keyboard_ce = [[InlineKeyboardButton(card.front + ' : ' + card.back, callback_data=f"delete_card_{card.id}")] for card in cards[start_index_ce:end_index_ce]]
    navigation_buttons_ce = []
    if int(page_ce) > 0:
        navigation_buttons_ce.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_ce_{int(page_ce) - 1}"))
    if int(page_ce) < total_pages_ce:
        navigation_buttons_ce.append(InlineKeyboardButton("➡️ Next", callback_data=f"page_ce_{int(page_ce) + 1}"))
    if navigation_buttons_ce:
        keyboard_ce.append(navigation_buttons_ce)
    return keyboard_ce

def __list_decks(deck_ids, deck_names, page):
    items_per_page = 5
    total_pages = int(len(deck_ids) / items_per_page)
    start_index = page * items_per_page
    end_index = start_index + items_per_page
    keyboard = []
    for i in range(len(deck_ids)):
        if i >= start_index and i <= end_index:
            keyboard.append([InlineKeyboardButton(deck_names[i], callback_data=f"deck_{deck_ids[i]}")])
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{page - 1}"))
    if page < total_pages:
        navigation_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"page_{page + 1}"))
    if navigation_buttons:
        keyboard.append(navigation_buttons)
    return keyboard

def generate_options(correct_card, all_cards, attribute):
    options = set(getattr(card, attribute) for card in all_cards if card != correct_card)
    options = list(options)[:3]  # Choose 3 random incorrect options
    options.append(getattr(correct_card, attribute))  # Add the correct option
    random.shuffle(options)  # Shuffle the options
    return options


def main():
    app = ApplicationBuilder().token(config.get("DEFAULT", "BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("menu", show_menu))
    app.add_handler(CommandHandler("list", list_decks))
    app.add_handler(CallbackQueryHandler(handle_answer))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_reply))
    print("Bot is running...")
    app.run_polling()


def all_commands():
    return """
/start - Start the bot
/help - Show available commands
/menu - Show menu
/list - List all decks
    """


if __name__ == "__main__":
    main()
