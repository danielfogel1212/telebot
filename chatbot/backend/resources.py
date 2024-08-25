from flask import Flask, jsonify
from flask_restful import Api, Resource, reqparse
from flask_cors import CORS
from models import Order, db, User  # Ensure correct imports
from telegram import Bot
import logging
import  asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue
# Telegram bot token (replace with your own)
TELEGRAM_BOT_TOKEN = '7394035467:AAHBZ-rEMbTDjMY5KaZtZnZtdJKdg6JV6_0'
message_queue = Queue()
# Initialize the bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Setup logging
logging.basicConfig(level=logging.INFO)

class PendingOrders(Resource):
    def get(self):
        # Retrieve all orders from the database
        all_orders = Order.query.all()

        # Filter orders with a pending status in Python
        pending_orders = [order.serialize() for order in all_orders]

        return jsonify(pending_orders)

  

    def put(self, id):
    # Update the status of the order by id
     order = Order.query.get(id)
     if order:
        parser = reqparse.RequestParser()
        parser.add_argument('status', type=str, required=True, help="סטטוס חדש של ההזמנה.")
        args = parser.parse_args()

        # Update the order status
        old_status = order.pending
        order.pending = args['status']

        try:
            # Commit the update to the database
            db.session.commit()

            # Check if the status was updated to "יצא לדרך"
            if order.pending == 'יצא לדרך':
                # Fetch the user's chat_id
                user = User.query.get(order.user_id)
                if user and user.chat_id:
                    userid= User.query.filter_by(id=user.id).first()
                    message_queue.put((user.chat_id, id,user.username))
                    logging.info(f"Added Telegram notification for order {id} to queue")

            return {'message': 'הסטטוס עודכן בהצלחה'}, 200
        except Exception as e:
            # Rollback in case of an error
            db.session.rollback()
            logging.error(f"Error updating order: {e}")
            return {'message': f'שגיאה בעת עדכון ההזמנה: {str(e)}'}, 500
     else:
        return {'message': 'הזמנה לא נמצאה'}, 404

async def process_queue():
    while True:
        # קבל הודעה מהתור
        chat_id, order_id, userid = message_queue.get()
        try:
          

            await bot.send_message(chat_id=chat_id, text=f"הזמנה מספר {order_id} של {userid} יצאה לדרך!")
            logging.info(f"Sent Telegram notification for order {order_id}")
        except Exception as e:
            logging.error(f"Failed to send Telegram message: {e}")
        message_queue.task_done()

# הפעל את לולאת האירועים האסינכרונית בת'רד נפרד
def start_event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(process_queue())

threading.Thread(target=start_event_loop, daemon=True).start()
