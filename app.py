from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import threading
import time
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///channel_manager.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
CORS(app)

# Models
class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(50), unique=True)
    total_units = db.Column(db.Integer)
    available_units = db.Column(db.Integer)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(50))
    channel = db.Column(db.String(50))
    checkin_date = db.Column(db.String(20))
    status = db.Column(db.String(20), default='confirmed')

# Create tables & seed data
with app.app_context():
    db.create_all()
    if Inventory.query.filter_by(room_id='room101').first() is None:
        db.session.add(Inventory(room_id='room101', total_units=10, available_units=10))
        db.session.add(Inventory(room_id='room102', total_units=8, available_units=8))
        db.session.commit()

def push_to_otas(room_id, units):
    time.sleep(1)
    print(f"✅ Pushed {room_id}: {units} to Booking.com, Expedia")

@app.route('/inventory/update', methods=['POST'])
def update_inventory():
    data = request.json
    room = Inventory.query.filter_by(room_id=data['room_id']).first()
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    room.available_units = data['available_units']
    db.session.commit()
    threading.Thread(target=push_to_otas, args=(data['room_id'], data['available_units'])).start()
    return jsonify({'success': True, 'updated': data['available_units']})

@app.route('/bookings/pull', methods=['GET', 'POST'])
def pull_bookings():
    if request.method == 'POST':
        new_bookings = [
            {'room_id': 'room101', 'channel': 'booking.com', 'checkin_date': '2026-01-15'},
            {'room_id': 'room102', 'channel': 'expedia', 'checkin_date': '2026-01-20'}
        ]
        for booking in new_bookings:
            room = Inventory.query.filter_by(room_id=booking['room_id']).first()
            if room and room.available_units > 0:
                room.available_units -= 1
                db.session.add(Booking(**booking))
        db.session.commit()
        return jsonify({'success': True, 'new_bookings': len(new_bookings)})
    
    bookings = Booking.query.limit(10).all()
    return jsonify([{
        'id': b.id, 'room_id': b.room_id, 'channel': b.channel, 
        'checkin_date': b.checkin_date
    } for b in bookings])

@app.route('/rates/push', methods=['POST'])
def push_rates():
    data = request.json
    room_id = data['room_id']
    price = data['price']
    print(f"💰 Pushed rate ${price} for {room_id} to {data.get('channel', 'all')}")
    
    room = Inventory.query.filter_by(room_id=room_id).first()
    if room:
        room.total_units = price
        db.session.commit()
    
    return jsonify({'success': True, 'price': price, 'room_id': room_id})

@app.route('/rooms', methods=['GET'])
def list_rooms():
    rooms = Inventory.query.all()
    return jsonify([{
        'room_id': r.room_id,
        'total': r.total_units,
        'available': r.available_units
    } for r in rooms])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
if __name__ == '__main__':
    app.run()

