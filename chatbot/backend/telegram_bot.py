from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
import logging

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/restaurant'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram bot token
TOKEN = 'xxxxxx'

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
    items = db.Column(db.String(80), nullable=False)
    address = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    pending = db.Column(db.String(80), nullable=False)

# Create all tables
with app.app_context():
    db.create_all()

# Define menu
menu = {
    "1. פיצה מרגריטה": 40,
    "2. סלט יווני": 30,
    "3. פסטה בולונז": 50,
    "4. קינוח שוקולד": 25
}

# Function to ask for user's name
async def ask_for_name(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    await update.message.reply_text("מה שמך?")
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

        user_data[chat_id] = {"order": [], "sum": 0, "state": "ordering"}
        await show_menu(update)

    elif user_data.get(chat_id, {}).get("state") == "ordering":
        await handle_choice(update, context)
    elif user_data.get(chat_id, {}).get("state") == "waiting_for_address":
        await handle_address(update, context)

# Show menu to the user
async def show_menu(update: Update):
    chat_id = update.message.chat_id
    menu_text = "בבקשה בחר מהתפריט:\n"
    menu_text += "\n".join([f"{dish}: ₪{price}" for dish, price in menu.items()])
    menu_text += "\n\nהקלד את מספר המאכל שתרצה להוסיף להזמנה. להשלמת ההזמנה הקלד 'אישור'.\n"
    menu_text += "להתחלת הזמנה חדשה, הקלד 9."
    
    await update.message.reply_text(menu_text)

# Handle user's choice
async def handle_choice(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_choice = update.message.text.strip()
    
    if user_choice in ["1", "2", "3", "4"]:
        dish = list(menu.keys())[int(user_choice) - 1]
        price = menu[dish]
        
        # Add to order and update the total sum
        user_data[chat_id]["order"].append(dish)
        user_data[chat_id]["sum"] += price
        
        await update.message.reply_text(f"{dish} נוסף להזמנה שלך.")
        await update.message.reply_text(
            "הקלד את מספר מאכל נוסף להוספת פריטים נוספים, או הקלד 'אישור' לסיום ההזמנה.\n"
            "להתחלת הזמנה חדשה, הקלד 9."
        )
    elif user_choice.lower() == "אישור":
        if user_data[chat_id]["order"]:
            user_data[chat_id]["state"] = "waiting_for_address"
            await update.message.reply_text("בבקשה הקלד את הכתובת שלך (עיר + רחוב).")
        else:
            await update.message.reply_text("ההזמנה שלך ריקה. בבקשה הוסף פריטים לפני האישור.")
    elif user_choice == "9":
        user_data[chat_id] = {"order": [], "sum": 0, "state": "ordering"}
        await update.message.reply_text("ההזמנה שלך אופסה. בבקשה בחר פריטים חדשים מהתפריט.")
        await show_menu(update)
    else:
        await update.message.reply_text("בחירה לא תקפה. בבקשה בחר מספר מאכל תקף או הקלד 'אישור' לסיום ההזמנה.")

# Handle user's address input
async def handle_address(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    address = update.message.text.strip()
    order_summary = "\n".join(user_data[chat_id]["order"])
    total_sum = user_data[chat_id]["sum"]

    try:
        with app.app_context():
            user = User.query.filter_by(chat_id=chat_id).first()
            order = Order(items=", ".join(user_data[chat_id]["order"]), address=address, user=user, pending='בהמתנה')
            
            db.session.add(order)
            
            db.session.commit()
            db.session.flush()  # Flushing ensures the ID is generated before commit
            
            order_id = order.id
            print(str(order_id)+"dasdsadadasdaa")
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
    user_data[chat_id] = {"order": [], "sum": 0, "state": "ordering"}

# Main function
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", ask_for_name))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))

    # Run the bot
    app.run_polling()

if __name__ == '__main__':
    main()
