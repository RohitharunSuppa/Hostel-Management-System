from pymongo import MongoClient
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, session, url_for
from flask_pymongo import PyMongo
import hashlib
import os
from bson import ObjectId
import bson
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'  
client = MongoClient('******')   #  Replace ****** with mongodb url for your database
db = client['hostel_management'] 
app.config['MONGO_URI'] = "*******"   #  Replace ****** with mongodb url for your database
mongo = PyMongo(app)
bcrypt = Bcrypt(app)

@app.route('/',  methods=['GET', 'POST'])
def index():

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        print(role)

        # Query the appropriate collection based on the selected role
        collection = db[role]
        # Check if the user exists in the collection
        user = collection.find_one({'email': email})
        if user and bcrypt.check_password_hash(user['password'], password):
            print("Foundddddd")
            # Authentication successful, store user information in session
            session['user'] = {'email': user['email'], 'role': role}

            # Redirect to the appropriate dashboard based on the role
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'management':
                return redirect(url_for('management_dashboard'))
            elif role == 'customers':
                return redirect(url_for('customer_dashboard'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    cust = db['customers']
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            print("wrong password")
            return render_template('register.html', error='Passwords do not match')


        # Hash the password before storing it
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        customer_data = {
            'name': name,
            'email': email,
            'mobile': mobile,
            'password': hashed_password
        }

        cust.insert_one(customer_data)

        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/cust_dashboard')
def customer_dashboard():
    if 'user' in session:
        user_info = session['user']
        email = user_info['email']
        role = user_info['role']
        customer_data = db.customers.find_one({'email': email})
        return render_template('customer_dashboard.html', email=email, role=role, customer_data=customer_data)
    else:
        return redirect(url_for('login'))

@app.route('/management_dashboard')
def management_dashboard():
    if 'user' in session:
        user_info = session['user']
        email = user_info['email']
        role = user_info['role']
        customer_data = db.management.find_one({'email': email})
        return render_template('management_dash.html', email=email, role=role, customer_data=customer_data)
    else:
        return redirect(url_for('login'))
@app.route('/create_room')
def create_room():
    management_collection =db['management']
    all_management = list(management_collection.find())
    return render_template('create_room.html', all_management=all_management)

@app.route('/submit_room', methods=['POST'])
def submit_room():
    room = db['rooms']
    if request.method == 'POST':
        room_number = int(request.form['roomNumber'])
        max_beds = int(request.form['maxBeds'])
        incharge = request.form['incharge']
        amenities = request.form.getlist('amenities')
        room_data = {
            'room_number': room_number,
            'max_beds': max_beds,
            'incharge': incharge,
            'amenities': amenities,
            'total_beds' : 0,
            'beds_left':0,
            'occupied':0
        }
        room.insert_one(room_data)
        return redirect(url_for('admin_dashboard'))
    
@app.route('/delete_manager', methods=['POST'])
def delete_manager():
    if request.method == 'POST':
        manager_id = request.form['manager_id']
        management_collection = db['management']
        management_collection.delete_one({'_id': ObjectId(manager_id)})
        return redirect(url_for('admin_dashboard'))
    
@app.route('/management_table')
def management_table():
    management=db['management']
    all_management = management.find()
    return render_template('manager_staff.html', all_management=all_management)


@app.route('/payment_table')
def payment_table():
    payment=db['payment']
    user_email = session['user']['email']
    print(user_email)
    user_payments = payment.find({'user_email': user_email})
    return render_template('applied_rooms.html', user_payments=user_payments)

@app.route('/get_rooms', methods=['GET'])
def get_rooms():
    rooms = db['rooms']

    room_list = []
    for room in rooms.find():
        room_data = {
            'room_number': room['room_number'],
            'incharge': room['incharge'],
            'max_beds': room['max_beds'],
            'amenities': room['amenities']
        }

        room_data['beds'] = room.get('beds', [])

        room_list.append(room_data)

    return render_template('view_rooms.html', rooms=room_list)
from flask import Flask, render_template, request, redirect, url_for
from flask_pymongo import PyMongo

@app.route('/del_rooms', methods=['POST'])
def del_rooms():
    rooms=db['rooms']
    beds=db['beds']
    room_id = request.form['room_id']
    rooms.delete_one({'_id': ObjectId(room_id)})
    beds.delete_many({'room_id': ObjectId(room_id)})

    redirect_destination = 'view_rooms'

    # Check the user role and update the redirect destination accordingly
    user_role = session['user']['role']
    if user_role == 'admin':
        redirect_destination = 'adm_view_rooms'
    return redirect(url_for(redirect_destination))

@app.route('/del_beds', methods=['POST'])
def del_beds():
    beds=db['beds']
    rooms=db['rooms']
    bed_id = request.form['bed_id']
    bed = beds.find_one({'_id': ObjectId(bed_id)})
    if bed:
        room_id = bed.get('room_id')

        # Fetch room using the room_id
        room = rooms.find_one({'_id': ObjectId(room_id)})
        if room:
            # Decrease total_beds by 1 in the room document
            rooms.update_one(
                {'_id': room_id},
                {'$inc': {'total_beds': -1}}
            )

        # Now you have the 'room' and 'bed' information, you can proceed with further actions

        # For example, delete the bed
        beds.delete_one({'_id': ObjectId(bed_id)})

    return redirect(url_for('view_beds'))

@app.route('/submit_bed', methods=['POST'])
def submit_bed():
    rooms = db['rooms']
    beds = db['beds']
    if request.method == 'POST':
        bed_number = request.form['bedNumber']
        bed_size = request.form['bedSize']
        room_number = request.form['room']
        price = int(request.form['price'])
        room = rooms.find_one({'room_number': int(room_number)})
        bed_data = {
                'bed_number': int(bed_number),
                'bed_size': bed_size,
                'status': 'available',
                'room_id': room['_id'],
                'price' : price,
                'last_checkin_date': int(0),
                "last_checkout_date":int(0)

        }
        beds.insert_one(bed_data)
        rooms.update_one(
            {'_id': ObjectId(room['_id'])},
            {
                '$inc': {'total_beds': 1}
            }
        )
        room = rooms.find_one({'room_number': int(room_number)})
        max=room['max_beds']
        total=room['total_beds']
        beds_left=int(max)-int(total)
        rooms.update_one(
            {'_id': ObjectId(room['_id'])},
            {
                '$set': {'beds_left': beds_left}
            }
        )
    return redirect(url_for('adm_view_rooms'))

@app.route('/create_bed', methods=['GET'])
def create_bed():
    rooms = db['rooms']
    all_rooms = rooms.find()
    available_rooms = [room for room in all_rooms if room['total_beds'] < room['max_beds']]
    return render_template('create_bed.html', available_rooms=available_rooms)

@app.route('/adm_view_rooms', methods=['GET'])
def adm_view_rooms():
    rooms_collection = db['rooms']
    all_rooms = rooms_collection.find()
    return render_template('view_rooms.html', all_rooms=all_rooms)


@app.route('/view_rooms', methods=['GET'])
def view_rooms():
    management=db['management']
    rooms=db['rooms']
    rooms_collection = db['rooms']
    all_rooms = rooms_collection.find()
    user_email = session['user']['email']
    user = management.find_one({'email': user_email})
    uname=user['name']
    matching_rooms = rooms_collection.find({'incharge': uname})
    return render_template('view_rooms.html', all_rooms=matching_rooms)

@app.route('/view_customers', methods=['GET'])
def view_customers():
    customers_collection = db['customers']
    beds_collection = db['beds']
    customers = customers_collection.find()
    user_dict = {}
    for customer in customers:
        customer_id = customer['_id']
        customer_name = customer['name']
        beds = beds_collection.find({'username': customer_name})
        bed_info = []
        for bed in beds:
            bed_info.append({
                'room_number': bed['room_number'],
                'bed_number': bed['bed_number'],
            })
        user_dict[customer_id] = {
            'customer_name': customer_name,
            'bed_info': bed_info
        }
    return render_template('view_customers.html', user_dict=user_dict)

@app.route('/view_beds', methods=['GET'])
def view_beds():
    beds_collection = db['beds']
    all_beds = beds_collection.find()
    return render_template('view_beds.html', all_beds=all_beds)

@app.route('/view_notices', methods=['GET'])
def view_notices():
    notices = db['notices']
    beds_collection = db['beds']
    notices = notices.find()
    return render_template('view_notices.html', notices=notices)

@app.route('/submit_notice', methods=['POST'])
def submit_notice():
    notices = db['notices']
    if request.method == 'POST':
        notice_text = request.form.get('noticeText')
        user_email = session['user']['email']
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        notices.insert_one({'text': notice_text, 'username': user_email, 'time': current_time})
    return redirect(url_for('view_notices'))
 
@app.route('/submit_management', methods=['POST'])
def submit_management():
    management = db['management']
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        position = request.form['position']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        management_data = {
            'name': name,
            'email': email,
            'position': position,
            'password': hashed_password 
        }
        management.insert_one(management_data)
        return redirect(url_for('admin_dashboard'))

@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/rooms')
def rooms():
    return render_template('rooms.html')

@app.route('/beds')
def beds():
    return render_template('beds.html')





@app.route('/main_notice')
def main_notice():
    return render_template('mian_notice.html')




@app.route('/add_management')
def add_management():
    return render_template('add_management.html')

@app.route('/notices')
def notices():
    return render_template('notice.html')

@app.route('/process_date', methods=['POST'])
def process_date():
    selected_date = request.form['selectedDate']
    return render_template('index.html', selected_date=selected_date, table_data=table_data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/room_selection')
def room_selection():
    rooms=db['rooms']
    all_rooms = rooms.find()
    available_rooms = [room for room in all_rooms if room['occupied'] < room['total_beds']]
    return render_template('room_selection.html', available_rooms=available_rooms)

@app.route('/submit_room_selection', methods=['POST'])
def submit_room_selection():
    rooms=db['rooms']
    beds=db['beds']
    room = request.form['selectedRoom']
    room = eval(room)
    room_id=room['_id']
    available_beds = beds.find({'room_id': ObjectId(room_id), 'status': 'available'})
    ab=beds.find({'room_id': ObjectId(room_id), 'status': 'available'})
    return render_template('selected_room.html', room=room,available_beds=available_beds,ab=ab)

@app.route('/confirm_bed', methods=['POST'])
def confirm_bed():
    rooms=db['rooms']
    beds=db['beds']
    selected_room_number = int(request.form['selectedRoomNumber'])
    selected_bed_number = int(request.form['selectedBed'])
    months=int(request.form['selectedDuration'])
    today = datetime.now().date()
    future_date = today + timedelta(days=30 * months)
    room = rooms.find_one({'room_number': selected_room_number})
    bed = beds.find_one({'bed_number': selected_bed_number, 'room_id': room['_id']}) # replace 'price' with the actual field storing the room price
    bed_price = int(bed.get('price', 0) )   # replace 'price' with the actual field storing the bed price
    total= int(bed_price)*int(months)
    print(total)
    return render_template('confirmation.html', room=room, bed=bed,months=months,total=total,today=today, future_date=future_date,)


@app.route('/process_payment', methods=['POST'])
def process_payment():
    payments = db['payment']
    rooms = db['rooms']
    beds = db['beds']
    users = db['customers']
    if request.method == 'POST':
        user_email = session['user']['email']
        card_number = request.form['cardNumber']
        expiration_date = request.form['expirationDate']
        cvv = request.form['cvv']
        card_holder_name = request.form['cardHolderName']
        address = request.form['address']
        months = request.form['months']
        total = request.form['total']
        roomnumber = int(request.form['roomnumber'])
        bednumber = int(request.form['bednumber'])
        current_date = datetime.now()
        next_payment_date = current_date + timedelta(days=30 * int(months))
        payment_data = {
            'user_email': user_email,
            'card_number': card_number,
            'expiration_date': expiration_date,
            'cvv': cvv,
            'card_holder_name': card_holder_name,
            'months': months,
            'total': total,
            'room_number': roomnumber,
            'bed_number': bednumber,
            'current_date': current_date,
            'next_payment_date': next_payment_date,
            'address': address

        }
        print(roomnumber)
        room = rooms.find_one({'room_number': roomnumber})
        current_user = users.find_one({'email': user_email})
        payments.insert_one(payment_data)


        if room:
            room_id = room['_id']
            bed = beds.find_one({'room_id': ObjectId(room_id), 'bed_number': bednumber})
            print(bed)
            beds.update_one({'_id': bed['_id']}, {'$set': {'username': current_user['name'], 'status': 'booked','booked_till':next_payment_date}})
            rooms.update_one(
            {'_id': room_id},
            {'$inc': {'occupied': 1}}
            )
        return redirect(url_for('customer_dashboard'))
    return render_template('checkin.html', checkin_data=checkin_data)


@app.route('/check')
def check():
    checks = db['checks']
    beds=db['beds']
    today_date = datetime.today().strftime('%Y-%m-%d')
    user_email = session['user']['email'] if 'user' in session and 'email' in session['user'] else None
    customer = db['customers'].find_one({'email': user_email})
    if customer:
        user_name = customer.get('name')
    else:
        user_name = 'Guest'
    
    res = checks.find_one({'date': today_date, 'username': user_name})
    bed_list = list(beds.find({'username': user_name}))
    num_checks = checks.count_documents({'date': today_date, 'username': user_name})
    num_beds = beds.count_documents({'username': user_name})
    print(num_checks)
    print(num_beds)
    if int(num_beds)== int(num_checks):
         results = list(checks.find({'date': today_date, 'username': user_name}))
    else:
        print("")
    if res:
        print('')
    else:
        print("creating")
        beds_numbers=[]
        bed_list = list(beds.find({'username': user_name}))
        for bed in bed_list:
                bed_number = bed['bed_number']
                beds_numbers.append(bed_number)
                check = {
                    'username': user_name,
                    'date': today_date,
                    'bed_number': bed_number,
                    'status': '-' 
                }
                checks.insert_one(check)
        print(f'Inserted new check: {check}')
    print(user_name)
    results=list(checks.find({'username': user_name}))
    return render_template('checkin.html', results=results)

@app.route('/chk')
def chk():
    management=db['management']
    rooms_collection=db['rooms']
    beds=db['beds']
    user_email = session['user']['email']
    user = management.find_one({'email': user_email})
    uname=user['name']
    results=[]
    today_date = datetime.now().strftime('%Y-%m-%d')

    matching_rooms = rooms_collection.find({'incharge': uname})
    for room in matching_rooms:
        room_id = room.get('_id')
        room_no = room.get('room_number')
        print(room_id)
        room_beds = beds.find({
        'room_id':  ObjectId(room_id),
        'status': {'$in': ['booked', 'checked-in', 'checked-out']}
    })
        for bed in room_beds:
            bed_info = {
                'date' : today_date,
                'bed_id': bed.get('_id'),
                'room_id': bed.get('room_id'),
                'status': bed.get('status'),
                'room_number': room_no,
                'user': bed.get('username'),
                'bed_no': bed.get('bed_number'),
                'last_checkin_date' : bed.get('last_checkin_date'),
                "last_checkout_date" : bed.get('last_checkout_date')

        }
            results.append(bed_info)
    return render_template('checkin.html', results=results)


@app.route('/checkin', methods=['POST'])
def checkin():
    beds_collection = db['beds']
    checks = db['checks']
    bed_id = ObjectId(request.form['bed_number'])
    current_datetime = datetime.utcnow()

    bed = beds_collection.find_one({'_id': bed_id})
    if bed:
        # Update the status to 'checked-in'
        beds_collection.update_one(
            {'_id': bed_id},
            {'$set': {'status': 'checked-in', 'last_checkin_date': current_datetime}}
        )

    return redirect(url_for('chk'))

@app.route('/checkout', methods=['POST'])
def checkout():
    beds_collection = db['beds']
    checks = db['checks']
    bed_id = ObjectId(request.form['bed_number'])
    current_datetime = datetime.utcnow()
    bed = beds_collection.find_one({'_id': bed_id})
    if bed:
        # Update the status to 'checked-in'
        beds_collection.update_one(
            {'_id': bed_id},
            {'$set': {'status': 'checked-out', 'last_checkout_date': current_datetime}}
        )

    return redirect(url_for('chk'))




@app.route('/process_checkin_checkout', methods=['POST'])
def process_checkin_checkout():
    selected_date = request.form['selectedDate']
    room_number = request.form['roomNumber']
    bed_number = request.form['bedNumber']
    action = request.form['action']
    print(f'Date: {selected_date}, Room Number: {room_number}, Bed Number: {bed_number}, Action: {action}')
    return render_template('checkin_checkout_form.html')

if __name__ == '__main__':
    app.run(debug=True)


#flask --app app.py --debug run 