from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import sessionmaker
from flask import current_app

import os
from datetime import timedelta
# יצירת אובייקט SQLAlchemy
db = SQLAlchemy()

# פונקציה ליצירת חיבור לבסיס הנתונים
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
    def serialize(self):
        return {
            'id': self.id,
            'items': self.items,
            'address': self.address,
            'pending': self.pending,
            'user_id': self.user_id,
            "username": self.user.username 
        }


class Config:
    # חיבור למסד הנתונים, כאן אנו משתמשים ב-MySQL דרך MySQL Connector
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+mysqlconnector://root:@localhost/restaurant')
    
    # ביטול מעקב אחרי שינויים במבני הטבלאות כדי לשפר ביצועים
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # מפתח סודי לשימוש ב-JWT (בברירת מחדל, מוגדר כערך קבוע, ניתן לשנות דרך משתני סביבה)
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', "d3f67a8b4c2e19f092c3a5b8d7e6f1a7b0c9d8e7f1a2c3b4d5e6f7a8b9c0d1e2")
    
    # תוקף של טוקן ה-JWT (במקרה הזה, 30 ימים)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)