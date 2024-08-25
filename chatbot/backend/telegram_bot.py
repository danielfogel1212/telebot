from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
import logging
import time
app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/restaurant'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram bot token
TOKEN = ''

# User data storage
user_data = {}

# Define models
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, unique=True)
    username = db.Column(db.String(80), nullable=False)
    orders = db.relationship('Order', backref='user')

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    items = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    pending = db.Column(db.String(80), nullable=False)

# Create all tables
with app.app_context():
    db.create_all()

# Define categorized menu
menu = {
    "פיצות": {
        "1. פיצה מרגריטה": 40,
        "2. פפרוני": 45,
        "3. ארבע גבינות": 50,
        "4. פיצה יוונית": 48,
        "5. פיצה ים תיכונית": 55,
        "6. פיצה פונגי": 52,
        "7. פיצה מקסיקנית": 57,
        "8. פיצה טבעונית": 45,
    },
    "סלטים": {
        "1. סלט יווני": 30,
        "2. סלט קפרזה": 35,
        "3. סלט קיסר עם עוף": 40,
    },
    "קינוחים": {
        "1. טירמיסו": 25,
        "2. פיצה שוקולד": 30,
        "3. קרם ברולה": 28,
        "4. סורבה פירות": 20,
    },
    "משקאות": {
        "1. קולה/דיאט קולה": 10,
        "2. מים מינרלים": 8,
        "3. בירה מקומית": 20,
        "4. יין הבית (כוס)": 25,
    }
}

# Function to ask for user's name
async def ask_for_name(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    await update.message.reply_text("ברוכים הבאים לפיצה פוגל" )
    time.sleep(1)
    await update.message.reply_text("שנתחיל בעוד")
    time.sleep(1)
    await update.message.reply_text("3")
    time.sleep(1)
    await update.message.reply_text("2")
    time.sleep(1)
    await update.message.reply_text("1")
    await update.message.reply_text("אז איך קוראים לך?" )



    
    user_data[chat_id] = {"state": "waiting_for_name", "order": [], "sum": 0}

# Handle user input
async def handle_input(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_input = update.message.text.strip()

    # If waiting for the user's name
    if user_data.get(chat_id, {}).get("state") == "waiting_for_name":
        try:
            with app.app_context():
                user = User.query.filter_by(chat_id=chat_id).first()
                if not user:
                    user = User(chat_id=chat_id, username=user_input)
                    db.session.add(user)
                    db.session.commit()
                    logger.info(f"משתמש {chat_id} עם השם {user_input} נוצר ונוסף למסד הנתונים.")
                else:
                    user.username = user_input  # Update username if necessary
                    db.session.commit()
                    logger.info(f"שם המשתמש {chat_id} עודכן ל-{user_input} במסד הנתונים.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"שגיאה בשמירת משתמש {chat_id} למסד הנתונים: {e}")
            await update.message.reply_text("התרחשה שגיאה. נסה שוב מאוחר יותר.")
            return

        user_data[chat_id] = {"order": [], "sum": 0, "state": "choosing_category"}
        await show_categories(update)

    elif user_data.get(chat_id, {}).get("state") == "choosing_category":
        await handle_category_selection(update, context)
    elif user_data.get(chat_id, {}).get("state") == "ordering":
        await handle_choice(update, context)
    elif user_data.get(chat_id, {}).get("state") == "waiting_for_address":
        await handle_address(update, context)

# Show category options to the user with clickable buttons
async def show_categories(update: Update):
    chat_id = update.message.chat_id
    categories = list(menu.keys())
    
    # Create inline keyboard with categories
    keyboard = [[InlineKeyboardButton(category, callback_data=category)] for category in categories]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("בבקשה בחר קטגוריה:", reply_markup=reply_markup)

# Handle user's category selection (from inline keyboard)
async def handle_category_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    category = query.data
    chat_id = query.message.chat_id

    # Initialize user_data if not already present
    if chat_id not in user_data:
        user_data[chat_id] = {"order": [], "sum": 0, "state": "ordering"}

    user_data[chat_id]["state"] = "ordering"
    user_data[chat_id]["current_category"] = category

    # Debug: Log selected category
    logger.info(f"קטגוריה שנבחרה: {category}")
    
    await query.answer()
    await show_menu(query, category)

# Show items in the selected category
async def show_menu(query, category):
    chat_id = query.message.chat_id
    items = menu.get(category, {})
    
    # Debug: Log items in the category
    logger.info(f"פריטים בקטגוריה {category}: {items}")
    
    if items:
        menu_text = f"--- {category} ---\n"
        menu_text += "\n".join([f"{dish}: ₪{price}" for dish, price in items.items()])
        menu_text += "\n\nהקלד את מספר המאכל שתרצה להוסיף להזמנה. להשלמת ההזמנה הקלד 'אישור'.\n"
        menu_text += "להתחלת הזמנה חדשה, הקלד 9."
    
        await query.message.reply_text(menu_text)
    else:
        # If there are no items in the category, show an error
        await query.message.reply_text("שגיאה: קטגוריה לא תקפה או ריקה. נסה שוב.")

# Handle user's choice from the menu
async def handle_choice(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_choice = update.message.text.strip()
    category = user_data[chat_id].get("current_category")

    # Ensure that the user's data is properly initialized
    if chat_id not in user_data:
        user_data[chat_id] = {"order": [], "sum": 0, "state": "ordering"}

    # Flatten the items in the current category
    items_in_category = list(menu.get(category, {}).keys())

    # Debug: Log user's choice and available items
    logger.info(f"בחירת המשתמש: {user_choice}, פריטים זמינים: {items_in_category}")

    if user_choice.isdigit() and int(user_choice) in range(1, len(items_in_category) + 1):
        item_key = items_in_category[int(user_choice) - 1]
        price = menu[category][item_key]
        
        # Add to order and update the total sum
        user_data[chat_id]["order"].append(item_key)
        user_data[chat_id]["sum"] += price
        
        await update.message.reply_text(f"{item_key} נוסף להזמנה שלך.")
        
        # Ensure category is still saved for subsequent choices
        user_data[chat_id]["current_category"] = category
        
        # Show categories again after a valid selection
        await show_categories(update)
    elif user_choice.lower() == "אישור":
        if user_data[chat_id]["order"]:
            user_data[chat_id]["state"] = "waiting_for_address"
            await update.message.reply_text("בבקשה הקלד את הכתובת שלך (עיר + רחוב).")
        else:
            await update.message.reply_text("ההזמנה שלך ריקה. בבקשה הוסף פריטים לפני האישור.")
    elif user_choice == "9":
        user_data[chat_id] = {"order": [], "sum": 0, "state": "choosing_category"}
        await update.message.reply_text("ההזמנה שלך אופסה. בבקשה בחר קטגוריה חדשה.")
        await show_categories(update)
    else:
        await update.message.reply_text("בחירה לא תקפה. בבקשה בחר מספר מאכל תקף או הקלד 'אישור' לסיום ההזמנה.")

async def handle_address(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    address = update.message.text.strip()
    
    # Build the order summary without the numbers
    order_summary = "\n".join([item.split(". ", 1)[1] for item in user_data[chat_id]["order"]])
    total_sum = user_data[chat_id]["sum"]

    try:
        with app.app_context():
            user = User.query.filter_by(chat_id=chat_id).first()
            order = Order(items=", ".join(user_data[chat_id]["order"]), address=address, user=user, pending='בהמתנה')
            
            db.session.add(order)
            db.session.commit()
            db.session.flush()  # Flushing ensures the ID is generated before commit
            
            order_id = order.id
            logger.info(f"הזמנה נשמרה עבור משתמש {chat_id}: {order_summary} בכתובת {address}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"שגיאה בשמירת ההזמנה עבור משתמש {chat_id}: {e}")
        await update.message.reply_text("התרחשה שגיאה בשמירת ההזמנה שלך. בבקשה נסה שוב.")
        return

    await update.message.reply_text(
        f"ההזמנה שלך אושרה:\n"
        f"מזהה הזמנה: {order_id}\n"
        f"{order_summary}\n"
        f"כתובת: {address}\n"
        f"סכום לתשלום: {total_sum} ש״ח"
    )
    user_data[chat_id] = {"order": [], "sum": 0, "state": "choosing_category"}
    await update.message.reply_text("תודה שרכשת בפיצה פוגל!")


# Main function
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", ask_for_name))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.add_handler(CallbackQueryHandler(handle_category_selection))

    # Run the bot
    app.run_polling()

if __name__ == '__main__':
    main()
