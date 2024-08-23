from flask import Flask
from flask_restful import Api
from flask_cors import CORS
from resources import PendingOrders  # ייבוא המשאב לניהול הזמנות במצב pending
from models import db, Config  # ייבוא של ההגדרות והמסד נתונים

app = Flask(__name__)

# הגדרת CORS כולל תמיכה בעוגיות (Credentials)
CORS(app, supports_credentials=True)

# הגדרת התצורה של האפליקציה מתוך מחלקת Config
app.config.from_object(Config)

# יצירת API והוספת ה-DB לאפליקציה
api = Api(app)
db.init_app(app)

# הוספת המשאב PendingOrders לנתיב '/orders/pending'
api.add_resource(PendingOrders, '/orders/pending', '/orders/pending/<int:id>')

# יצירת טבלאות במסד הנתונים (אם עדיין לא קיימות)
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
