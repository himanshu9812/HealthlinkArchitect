from flask import Flask, request, render_template, jsonify,redirect, url_for, session, flash
from pymongo import MongoClient
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import random
from datetime import datetime, timedelta
import threading
import time
import googlemaps
from geopy.geocoders import Nominatim
from collections import Counter
# from datetime import datetime

# sppech to text
from flask import Flask, render_template

#final Code


api_key='AIzaSyDbwtf_dATwlZNIgG6UqcVrPwsFheNK0os'

app = Flask(__name__)
app.secret_key = os.urandom(24)

client = MongoClient('mongodb+srv://Ambulance:hello1234@ambulance0.oajhybc.mongodb.net/?retryWrites=true&w=majority')
db = client['SIH']

# Store the latest pin codes in this set
latest_pin_codes = set()

# Initialize geolocator
geolocator = Nominatim(user_agent="your_app_name")

@app.route('/')
def index():
    red_alert_zones = calculate_red_alert_zones()

    feedback_data = db.app_feedback.find({}, {'user': 1, 'rating': 1, 'feedback_text': 1, '_id': 0})

    return render_template('index.html', red_alert_zones=red_alert_zones, feedback_data=feedback_data)

def get_coordinates_from_pin(pin_code):
    location = geolocator.geocode(pin_code)
    if location:
        return location.latitude, location.longitude
    return None, None

@app.route('/get_red_alert_zones')
def get_red_alert_zones():
    red_alert_zones = calculate_red_alert_zones()
    return jsonify(red_alert_zones)

def calculate_red_alert_zones():
    global latest_pin_codes
    red_alert_zones = []

    try:
        current_time = datetime.now().strftime('%H:%M')
        current_date = datetime.now().strftime('%Y-%m-%d')

        # Fetch new entry data from the database
        new_entries_cursor = db.Booking.find()

        # Convert the cursor to a list to get all documents
        new_entries = list(new_entries_cursor)

        print(new_entries)
        all_pincodes = []
        # Extract pin codes and store them in the latest_pin_codes set
        for entry in new_entries:
            location = entry.get('Location', '')
            if location:
                # Split the location by ',' and get the last element, then strip whitespaces
                pin_code = location.split(',')[-2].strip()
                pin_code = pin_code.split()[-1]
                all_pincodes.append(pin_code)
                latest_pin_codes.add(pin_code)

        print(all_pincodes)

        # Count occurrences of each pin code in the all_pincodes list
        pin_code_counts = {pin_code: all_pincodes.count(pin_code) for pin_code in set(all_pincodes)}

        # Filter pin codes occurring more than 5 times
        red_alert_pin_codes = [pin_code for pin_code, count in pin_code_counts.items() if count > 5]

        # Convert red alert pin codes to coordinates
        for pin_code in red_alert_pin_codes:
            latitude, longitude = get_coordinates_from_pin(pin_code)
            if latitude is not None and longitude is not None:
                red_alert_zones.append({'latitude': latitude, 'longitude': longitude, 'pin_code': pin_code, 'count': pin_code_counts[pin_code]})

        print(red_alert_zones)
    except Exception as e:
        print(f"Error calculating red alert zones: {str(e)}")

    return red_alert_zones


@app.route('/get_accidents_data')
def get_accidents_data():
    try:
        # Process the data for analysis
        analysis_data = process_accidents_data()

        return jsonify(analysis_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def process_accidents_data():
    try:
        new_entries_cursor = db.Booking.find()
        new_entries = list(new_entries_cursor)

        all_states = []

        for entry in new_entries:
            location = entry.get('Location', '')
            if location:
                # Splitting the location string to extract the state
                location_parts = location.split(',')
                state = ''
                if len(location_parts) > 1:
                    state = location_parts[-2].strip()
                    if state.lower() == 'bengal':
                        state = 'West Bengal'
                all_states.append(state)

        state_counts = Counter(all_states)

        # Remove the count for 'West Bengal'
        if 'West Bengal' in state_counts:
            del state_counts['West Bengal']

        print(state_counts)

        return state_counts

    except Exception as e:
        print(f"Error calculating states: {str(e)}")
        return {'error': str(e)}

# @app.route('/notice_board')
# def notice_board():
#     # Fetch data from MongoDB
#     data = db.app_feedback.find({}, {'user': 1, 'rating': 1, 'feedback_text': 1})

#     # Pass data to the template
#     return render_template('index.html', data=data)

@app.route('/contactus')
def contactus():
    return render_template('contactus.html')

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

def generate_userUID():
    while True:
        random_number = ''.join(str(random.randint(0, 9)) for _ in range(5))
        if random_number != '00000' and not db.user_reg.find_one({'uid': random_number}):
            return 'u' + random_number

def generate_ambulanceUID():
    while True:
        random_number = ''.join(str(random.randint(0, 9)) for _ in range(5))
        if random_number != '00000' and not db.ambulance_reg.find_one({'uid': random_number}):
            return 'a' + random_number

def generate_hospitalUID():
    while True:
        random_number = ''.join(str(random.randint(0, 9)) for _ in range(5))
        if random_number != '00000' and not db.hospital_reg.find_one({'uid': random_number}):
            return 'h' + random_number

@app.route('/user_reg', methods=["GET", "POST"])
def user_reg():
    if request.method == 'POST':
        name = request.form["name"]
        address = request.form["address"]
        userAge = request.form["userAge"]
        phone = request.form["phone"]
        userEmail = request.form["userEmail"]
        username = request.form["username"]
        password = request.form["password"]

        uid = generate_userUID()
        existing_user = db.user_reg.find_one({'username': username})

        if existing_user:
            flash('Username already exists, please choose another username.')
        else:
            db.user_reg.insert_one({
                'name': name,
                'address': address,
                'age': userAge,
                'phone': phone,
                'email': userEmail,
                'username': username,
                'password': password,
                'uid': uid
            })

            flash('Account created successfully! You can now Login')
            # return "Account created successfully! You can now go to index page <a href='/user_login'>User Login</a>."
    return render_template("index.html")

@app.route('/ambulance_reg', methods=["GET", "POST"])
def ambulance_reg():
    if request.method == 'POST':
        driverName = request.form['driverName']
        carNumber = request.form['carNumber']
        driverAge = request.form['driverAge']
        phone = request.form["phone"]
        driverEmail = request.form["userEmail"]
        panNumber = request.form['panNumber']
        license = request.form['license']
        username = request.form['username']
        password = request.form['password']
        latitude=request.form['Latitude']
        longitude=request.form['longitude']
        print(latitude);
        uid = generate_ambulanceUID()
        existing_user = db.ambulance_reg.find_one({'username': username})
        print(latitude)
        print(longitude)
        if existing_user:
            flash('Username already exists, please choose another username.')
        else:
            db.ambulance_reg.insert_one({
                'driverName': driverName,
                'carNumber': carNumber,
                'driverAge': driverAge,
                'phone': phone,
                'email': driverEmail,
                'panNumber': panNumber,
                'license': license,
                'username': username,
                'password': password,
                'uid': uid,
                'latitude':latitude,
                'longitude':longitude
            })

            flash('Account created successfully! You can now Login')
            # return "Account created successfully! You can now go to ambulance page <a href='/ambulance_login'>Ambulance Login</a>."
    return render_template('index.html')

@app.route('/hospital_reg', methods=["GET", "POST"])
def hospital_reg():
    if request.method == 'POST':
        inchargeName = request.form['inchargeName']
        hospitalLocation = request.form['hospitalLocation']
        hospitalName = request.form['hospitalName']
        hospitalEmail = request.form["userEmail"]
        username = request.form['username']
        password = request.form['password']

        uid = generate_hospitalUID()
        existing_user = db.hospital_reg.find_one({'username': username})

        if existing_user:
            flash('Username already exists, please choose another username.')
        else:
            db.hospital_reg.insert_one({
                'inchargeName': inchargeName,
                'hospitalLocation': hospitalLocation,
                'hospitalName': hospitalName,
                'email': hospitalEmail,
                'username': username,
                'password': password,
                'uid': uid
            })

            flash('Account created successfully! You can now Login')
            # return "Account created successfully! You can now go to hospital page <a href='/hospital_login'>Hospital login</a>."
    return render_template('index.html')

@app.route("/user_login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = db.user_reg.find_one({'username': username, 'password': password})

        if user:
            session['user_id'] = user['username']
            flash("Login Successful", "success")
            return redirect(url_for('user_booking', username = username, password = password))
        else: 
            flash("Invalid username or password. Please try again.", "error")

    return render_template("index.html")

@app.route("/ambulance_login", methods=["GET", "POST"])
def ambulance_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = db.ambulance_reg.find_one({'username': username, 'password': password})

        if user:
            session['user_id'] = user['username']
            flash("Login Successful", "success")
            return redirect(url_for('ambulance_notification', username = username, password = password))
        else:  
            flash("Invalid username or password. Please try again.", "error")

    return render_template("index.html")

@app.route("/hospital_login", methods=["GET", "POST"])
def hospital_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = db.hospital_reg.find_one({'username': username, 'password': password})

        if user:
            session['user_id'] = user['username']
            flash("Login Successful", "success")
            return redirect(url_for('hospital_notification', username = username, password = password))
        else: 
            flash("Invalid username or password. Please try again.", "error")

    return render_template("index.html")

@app.route('/user_booking/<string:username>/<string:password>', methods=["GET", "POST"])
def user_booking(username, password):
    user_data = db.user_reg.find_one({'username': username, 'password': password})

    hospital_names = []
    for hosp_name in db.hospital_data.find():
        hospital_names.append(hosp_name["Hospital Name"])
    hospital_names.sort()
    
    # print(user_data)  # Check if user_data is retrieved correctly
    if request.method == 'POST':
        selected_hospitals = request.form.getlist('hosp_name')
        selected_hospitals = selected_hospitals if selected_hospitals else []
        temp_id = []
        # print(selected_hospitals)
        try:
            for h_name in selected_hospitals:
                print(h_name)
                results = db.hospital_reg.find({'hospitalName': h_name})
                for result in results:
                    print(result)  # This will print each document that matches the hospitalName
                    temp_id.append(result['uid'])
        except Exception as e:
            flash(f'Error fetching hospital details: {str(e)}', 'error')

        if temp_id:
            ref_id = temp_id
            booking_type = "Scheduled"
            # print(request.form.get('bed_avail'))
            if request.form.get('bed_avail'):
                avail_bed = "Yes"
            else:
                avail_bed = "No"
        else:
            ref_id = ["00000"]
            booking_type = "Accident"
            avail_bed = "Yes"

        book_person = request.form['book-person']
        if book_person == "self":
            name = user_data['name']
            phone = user_data['phone']
        elif book_person == "else":
            name = request.form['name']
            phone = request.form['phone']
        username = user_data['username']
        book_method = request.form['book-method']
        print(book_method)
        email = user_data['email']
        address = user_data['address']
        reason = request.form['reason']
        latitude = request.form['latitude']
        longitude = request.form['longitude']
        location = request.form['location']
        date = request.form['date']
        time = request.form['time']
        # booking_type = request.form['bookingType']
        if book_method == "full":
            db.ambulance_pending.insert_one({
                'name': name,
                'user_username': username,
                'reason': reason,
                'phone': phone,
                'address': address,
                'email': email,
                'pickup_location': location,
                'password':password,
                'latitude': latitude,
                'longitude': longitude,
                'date': date,
                'time': time,
                'booking_type': booking_type
            })
            avail_ambulance = "No"
        elif book_method == "direct":
            if request.form.get('ambulance_avail'):
                avail_ambulance = "Yes"
            else:
                avail_ambulance = "No"
        db.hospital_pending.insert_one({
            'name': name,
            'user_username': username,
            'reason': reason,
            'phone': phone,
            'address': address,
            'email': email,
            'pickup_location': location,
            'latitude': latitude,
            'longitude': longitude,
            'date': date,
            'time': time,
            'avail_ambulance': avail_ambulance,
            'avail_bed': avail_bed,
            'booking_type': booking_type,
            'ref_id': ref_id
        })
        if booking_type == "Accident":
            db.Booking.insert_one({
                'Date':date,
                'Time':time,
                'Location':location
            })


        # flash('Booking successful', 'success')
        if book_method == "full":
            return redirect(url_for('getwellsoon', username=username, password=password))
        elif book_method == "direct":
            return redirect(url_for('user_nav', username=username, password=password))

    return render_template('user_booking.html', username=username, password=password, hospital_names=hospital_names)

@app.route('/get_address',methods=['GET'])
def get_address():
    device1=[]
    result=db.hospital_data.find()
    big_address=[]
    for document in result:
        list=[]
        list.append(document['Hospital Name'])
        list.append(document['Address'])
        big_address.append(list)
    device1=big_address
    # print(big_address)
    return jsonify(result=device1)

@app.route('/get_list', methods=['GET'])
def get_list():
    devices = []
    result = db.ambulance_reg.find()
    big_list = []
    for document in result:
          list = []
          list.append(document['username'])
          list.append(document['latitude'])
          list.append(document['longitude'])
          big_list.append(list)

     # Assign the big_list variable to the devices variable
    devices = big_list
    return jsonify(result=devices)

@app.route("/hospital_data_show", methods=['GET'])
def hospital_data_show():
    hospital_name = request.args.get('hospital_name')
    medical_category = request.args.get('medical_category')
    
    print(hospital_name)
    result = db.hospital_data.find_one({"Hospital Name": hospital_name})
    if result:
        data = result.get(medical_category, [])
        return jsonify(data=data)
    else:
        return jsonify(error="Hospital not found"), 404
    # hospital_names = db.hospital_data.distinct("Hospital Name")
    # medical_categories = db.hospital_data.distinct("Medical Category")
    # if request.method=="POST":
    #     hospital = request.form.get("hospital")
    #     medical_need = request.form.get("medicalNeed")
    #     print(hospital)
    #     print(medical_need)
    #     # Query MongoDB to get bed availability
    #     bed_data = db.hospital_data.find_one({"Hospital Name": hospital })
    #     available_beds = bed_data[medical_need]
    #     print(bed_data)
    #     print(available_beds)

    #     return render_template("user_booking.html", username=username, password=password, hospital_names=hospital_names, medical_categories=medical_categories, available_beds=available_beds, bed_data=bed_data)

    # return render_template("user_booking.html", username=username, password=password, hospital_names=hospital_names, medical_categories=medical_categories)

@app.route('/ambulance_notification/<string:username>/<string:password>', methods=["GET", "POST"])
def ambulance_notification(username, password):
    ambu_data = db.ambulance_reg.find_one({'username': username, 'password': password})
    pending_data = db.ambulance_pending.find()
    accepted_data = db.ambulance_accepted.find({'ref_id': ambu_data['uid']})

    # result = db.ambulance_accepted.find_one({"ref_id": ambu_data['uid']})
    # latitude = result['latitude']
    # longitude = result['longitude']
    try:
        result = db.ambulance_accepted.find_one({"ref_id": ambu_data['uid']})
        if result:
            latitude = result['latitude']
            longitude = result['longitude']
        else:
            raise TypeError('Data not found in this collection')
    except TypeError:
        # result = db.ambulance_pending.find_one({"ref_id": ambu_data['uid']})
        latitude = 0.0
        longitude = 0.0

    # try:
    #     result = db.ambulance_accepted.find_one({"ref_id": ambu_data['uid']})
    #     temp = db.hospital_accepted.find_one({"user_username": result['user_username']})
    #     data = db.hospital_reg.find_one({'uid': temp['ref_id']})
    #     result = db.hospital_data.find_one({"Hospital Name": data["hospitalName"]})
    #     if result:
    #         address = result['Address']
    #     else:
    #         raise TypeError('Data not found in this collection')
    # except TypeError:
    #     # result = db.ambulance_pending.find_one({"ref_id": ambu_data['uid']})
    #     address = 'Address'

    # return render_template('ambulance_notification.html', username=username, password=password, pending_data=pending_data, accepted_data=accepted_data, lati=latitude, longi=longitude, address=address)
    return render_template('ambulance_notification.html', username=username, password=password, pending_data=pending_data, accepted_data=accepted_data, lati=latitude, longi=longitude)


@app.route('/ambulance_notification/ambulance_delete/<string:user_username>')
def ambulance_delete(user_username):
    db.ambulance_accepted.delete_one({'user_username': user_username})
    return redirect(url_for('ambulance_notification'))

@app.route('/ambulance_notification/ambulance_accept/<string:user_username>/<string:username>/<string:password>')
def ambulance_accept(user_username, username, password):
    data = db.ambulance_pending.find_one({'user_username': user_username})

    ref_data = db.ambulance_reg.find_one({'username': username})
    if not db.ambulance_accepted.find_one({'ref_id': ref_data['uid']}):
        db.ambulance_accepted.insert_one({
            'name': data['name'],
            'user_username': data['user_username'],
            'reason': data['reason'],
            'phone': data['phone'],
            'address': data['address'],
            'email': data['email'],
            'pickup_location': data['pickup_location'],
            'latitude': data['latitude'],
            'longitude': data['longitude'],
            'date': data['date'],
            'time': data['time'],
            'booking_type': data['booking_type'],
            'ref_id': ref_data['uid']
        })
        db.ambulance_pending.delete_one({'user_username': user_username})

    
    return redirect(url_for('ambulance_notification', username=username, password=password))

@app.route('/ambulance_notification/ambulance_end/<string:username>/<string:password>/<string:user_username>')
def ambulance_end(username, password, user_username):
    return redirect(url_for('payment_portal', username=username, password=password, user_username=user_username))

@app.route('/update_location/<string:username>/<string:password>', methods=['POST'])
def update_location(username,password):
    global updating_location
    while True:
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        db.ambulance_reg.update_one(
            {'username': username, 'password': password},
            {'$set': {'latitude': latitude, 'longitude': longitude, 'timestamp': datetime.now()}}
        )
        if username and password:
            print(f"Location updated for user: {username}, Latitude {latitude}, Longitude {longitude} and the {datetime.now()}")
        else:
            print("Invalid username or password")

        time.sleep(10)

@app.route('/hospital_notification/<string:username>/<string:password>', methods=["GET", "POST"])
def hospital_notification(username, password):
    hosp_data = db.hospital_reg.find_one({'username': username, 'password': password})
    pending_data=None
    accepted_data=None
    if hosp_data is not None:
        pending_data = db.hospital_pending.find({'ref_id': {'$elemMatch': {'$in': [hosp_data['uid'], '00000']}}})
        accepted_data = db.hospital_accepted.find({'ref_id': hosp_data['uid']})
    else:
        # Handle the case where the hosp_data object is None
        pass

    return render_template('hospital_notification.html',username=username, password=password, pending_data=pending_data, accepted_data=accepted_data)

@app.route('/hospital_notification/hospital_delete/<string:user_username>')
def hospital_delete(user_username):
    db.hospital_accepted.delete_one({'user_username': user_username})
    return redirect(url_for('hospital_notification'))

@app.route('/hospital_notification/hospital_accept//<string:user_username>/<string:username>/<string:password>')
def hospital_accept(user_username, username, password):
    data = db.hospital_pending.find_one({'user_username': user_username})


    ref_data = db.hospital_reg.find_one({'username': username})
    hosp_address = db.hospital_data.find_one({'Hospital Name': ref_data['hospitalName']})
    if data['reason'] == "SOS":
        db.sos_booking.update_one({'ref_id': data['name']}, {'$set': {'hosp_ad': hosp_address['Address']}})
    db.hospital_accepted.insert_one({
        'name': data['name'],
        'user_username': data['user_username'],
        'reason': data['reason'],
        'phone': data['phone'],
        'address': data['address'],
        'email': data['email'],
        'pickup_location': data['pickup_location'],
        'latitude': data['latitude'],
        'longitude': data['longitude'],
        'date': data['date'],
        'time': data['time'],
        'avail_ambulance': data['avail_ambulance'],
        'avail_bed': data['avail_bed'],
        'booking_type': data['booking_type'],
        'ref_id': ref_data['uid']
    })

    db.hospital_pending.delete_one({'user_username': user_username})

    return redirect(url_for('hospital_notification', username=username, password=password))

@app.route('/hospital_notification/hospital_recieved//<string:user_username>/<string:username>/<string:password>')
def hospital_recieved(user_username, username, password):
    data = db.hospital_accepted.find_one({'user_username': user_username})
    db.recieved_patients.insert_one({
        'name': data['name'],
        'user_username': data['user_username'],
        'reason': data['reason'],
        'phone': data['phone'],
        'address': data['address'],
        'email': data['email'],
        'pickup_location': data['pickup_location'],
        'latitude': data['latitude'],
        'longitude': data['longitude'],
        'date': data['date'],
        'time': data['time'],
        'booking_type': data['booking_type'],
        'ref_id': data['ref_id']
    })
    current_date = datetime.strptime(data['date'], "%Y-%m-%d")
    feedback_data = db.app_feedback.find_one({'ref_id': data['ref_id']})
    if feedback_data is None:
        days_difference = None
    else:
        previous_date = datetime.strptime(feedback_data['date'], "%Y-%m-%d")
        days_difference = (current_date - previous_date).days
    if days_difference is None or days_difference > 30:
        db.app_feedback.delete_one({'ref_id': data['ref_id']})
        return redirect(url_for('hospital_feedback', user_username=user_username, username=username,password=password))
    else:
        db.hospital_accepted.delete_one({'user_username': user_username})
        return redirect(url_for('hospital_notification',username=username,password=password))
        

@app.route('/hospital_feedback/<string:user_username>/<string:username>/<string:password>', methods=["GET", "POST"])
def hospital_feedback(user_username, username, password):
    ref_data = db.hospital_accepted.find_one({'user_username': user_username})
    hosp_data = db.hospital_reg.find_one({'username': username})
    if request.method == 'POST':
        rating = int(request.form['feedback-star']) + 1
        feedback_text = request.form['feedback-text']
        
        feedback_data = {
            'user': hosp_data['hospitalName'],
            'date': ref_data['date'],
            'time': ref_data['time'],
            'rating': rating,
            'feedback_text': feedback_text,
            'ref_id': ref_data['ref_id']
        }
        db.app_feedback.insert_one(feedback_data)
        db.hospital_accepted.delete_one({'user_username': user_username})
        return redirect(url_for('hospital_notification',username=username,password=password))
    return render_template('hospital_feedback.html', user_username=user_username, username=username, password=password)
    
@app.route('/hospital_bed_management/<string:username>/<string:password>', methods=["GET", "POST"])
def hospital_bed_management(username, password):
    hosp_name = db.hospital_reg.find_one({'username': username, 'password': password})
    hosp_data = db.hospital_data.find_one({'Hospital Name': hosp_name['hospitalName']})
    if request.method == 'POST':
        ORTHO = int(request.form['ORTHO'])
        GYNE = int(request.form['GYNE'])
        CARDIO = int(request.form['CARDIO'])
        PULMO = int(request.form['PULMO'])
        OPTHALMO = int(request.form['OPTHALMO'])
        SURGERY = int(request.form['SURGERY'])
        MEDICINE = int(request.form['MEDICINE'])
        EMERGENCY = int(request.form['EMERGENCY'])

        # Connect to the database
        db.hospital_data.update_one(
            {'Hospital Name': hosp_name['hospitalName']},
            {'$set': {
                'ORTHO': ORTHO,
                'GYNE': GYNE,
                'CARDIO': CARDIO,
                'PULMO': PULMO,
                'OPTHALMO': OPTHALMO,
                'SURGERY': SURGERY,
                'MEDICINE': MEDICINE,
                'EMERGENCY': EMERGENCY
            }}
        )

        return redirect(url_for('hospital_bed_management', username=username, password=password))
    return render_template('hospital_bed_management.html', username=username, password=password, hosp_data=hosp_data)


@app.route('/ambulance_email/<string:username>/<string:password>/<string:user_username>', methods=["GET", "POST"])
def ambulance_email(username, password, user_username):
    gmaps=googlemaps.Client(key=api_key)

    result_ambulance=db.ambulance_reg.find_one({'username':username})
    ambulance_lat=0.0
    ambulance_lon=0.0
    if result_ambulance:
        ambulance_lat=result_ambulance['latitude']
        ambulance_lon=result_ambulance['longitude']
    uid=result_ambulance['uid']
    result_user=db.ambulance_accepted.find_one({"ref_id":uid})
    user_lat=0.0
    user_lon=0.0
    if result_user:
        user_lat=result_user['latitude']
        user_lon=result_user['longitude']
    # print(user_lat)
    # print(user_lon)
    origin=(user_lat,user_lon)
    destination=(ambulance_lat,ambulance_lon)

    directions_result=gmaps.directions(
        origin,
        destination,
        mode='driving',
        # departure_time=datetime.now(),
    )

    distance = directions_result[0]['legs'][0]['distance']['text']
    duration = directions_result[0]['legs'][0]['duration']['text']

    print(distance)
    print(duration)
    

    gmail_user = 'healthlinkarchitects@gmail.com'
    gmail_password = 'hzex zsht hnkk ephu'
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(gmail_user, gmail_password)

    # name = request.args.get('name')
    user = db.ambulance_accepted.find_one({'user_username': user_username})
    print(user)
    if user:
        to_email = user['email']
        print(to_email)

        subject = 'Ambulance Confirmed'
        body = f'Ambulance has confirmed your ride. Your ambulance is on its way and it is {distance} away from you.It will arrive in just {duration}. Please hang tight.'
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        text = msg.as_string()
        server.sendmail(gmail_user, to_email, text)

        server.quit()

        flash("Email sent successfully")
    else:
        flash("User not found")

    return redirect(url_for('ambulance_notification', username=username, password=password))


@app.route('/hospital_email/<string:username>/<string:password>/<string:user_username>', methods=["GET", "POST"])
def hospital_email(username, password, user_username):
    gmail_user = 'healthlinkarchitects@gmail.com'
    gmail_password = 'hzex zsht hnkk ephu'
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(gmail_user, gmail_password)

    # user_username = request.args.get('user_username')
    user = db.hospital_accepted.find_one({'user_username': user_username})
    hosp = db.hospital_reg.find_one({'uid': user['ref_id']})
    if user:
        to_email = user['email']

        subject = 'Hospital Confirmed'
        body = hosp['hospitalName'] + ' has confirmed your booking. We will be waiting for your arrival.'
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        text = msg.as_string()
        server.sendmail(gmail_user, to_email, text)

        server.quit()

        flash("Email sent successfully")
    else:
        flash("User not found")

    return redirect(url_for('hospital_notification', username=username, password=password))

@app.route('/getwellsoon/<string:username>/<string:password>', methods=["GET", "POST"])
def getwellsoon(username,password):
    
    ans=0
    ambulance_latitude=0.0
    ambulance_longitude=0.0
    msg_flag = 0
    data = db.user_reg.find_one({"username": username})
    try:
        result = db.ambulance_accepted.find_one({"user_username": username})
        back_to_form = db.ambulance_pending.find_one({"user_username": username})
   
        if back_to_form is None and result is None:
            raise TypeError('Data not found anywhere')
        elif result is None and back_to_form is not None:
            raise ValueError('Data not found in collection1')
        ans = result['ref_id']
        ambulance_result=db.ambulance_reg.find_one({"uid":ans})
        if ambulance_result:
            ambulance_latitude=ambulance_result['latitude']
            ambulance_longitude=ambulance_result['longitude']
        msg_flag = 1
        # flash("Please wait, Your ambulance will be arriving soon")
    except ValueError:
        result = db.ambulance_pending.find_one({"user_username": username})
        ambulance_latitude=result['latitude']
        ambulance_longitude=result['longitude']
        msg_flag = 2
        # flash("Please wait while we find you an ambulance")
    except TypeError:
        msg_flag = 0
        # return redirect(url_for('user_booking', username=username, password=password))
        current_date = datetime.strptime(datetime.now().strftime("%Y-%m-%d"), "%Y-%m-%d")
        feedback_data = db.app_feedback.find_one({'ref_id': data['uid']})
        if feedback_data is None:
            days_difference = None
        else:
            previous_date = datetime.strptime(feedback_data['date'], "%Y-%m-%d")
            days_difference = (current_date - previous_date).days
        if days_difference is None or days_difference > 30:
            db.app_feedback.delete_one({'ref_id': data['uid']})
            # return redirect(url_for('user_feedback', username=username,password=password))
        else:
            return redirect(url_for('user_booking', username=username, password=password))

    # result = db.ambulance_accepted.find_one({"user_username": username})
    print("hello")
    print(result)
    # ans=0
    if result is not None:
        # ans = result['ref_id']
        print("Found result:", ans)
    else:
        print("No matching document found.")
    user_latitude=result['latitude']
    user_longitude=result['longitude']
    print(user_latitude)
    print(user_longitude)
    # ambulance_result=db.ambulance_reg.find_one({"uid":ans})
    # ambulance_latitude=0.0
    # ambulance_longitude=0.0
    # if ambulance_result:
    #     ambulance_latitude=ambulance_result['latitude']
    #     ambulance_longitude=ambulance_result['longitude']
    print(ambulance_latitude)
    print(ambulance_longitude)


    if request.method == "POST":
        username_form = request.form.get('username')  # Get username from the form
        password_form = request.form.get('password')
        action = request.form.get('action')  # Get the action value
        print(action)
        if action == 'cancel':
            collection_pairs = [(db.ambulance_pending, db.hospital_pending), (db.ambulance_pending, db.hospital_accepted),
                        (db.ambulance_accepted, db.hospital_pending), (db.ambulance_accepted, db.hospital_accepted)]
            for c1, c2 in collection_pairs:
                c1.delete_one({"user_username": username_form})
                c2.delete_one({"user_username": username_form})
            msg_flag = 0
            # return redirect(url_for('user_booking', username = username, password = password))
            # current_date = datetime.strftime(datetime.now(), "%Y-%m-%d")
            # feedback_data = db.app_feedback.find_one({'ref_id': data['uid']})
            # if feedback_data is None:
            #     days_difference = None
            # else:
            #     previous_date = datetime.strftime(feedback_data['date'], "%Y-%m-%d")
            #     days_difference = (current_date - previous_date).days
            # if days_difference is None or days_difference > 30:
            #     db.app_feedback.delete_one({'ref_id': data['uid']})
            #     return redirect(url_for('user_feedback', username=username,password=password))
            # else:
            return redirect(url_for('user_booking', username=username, password=password))
        elif action == 'rebooking':
            print("hi")
            data = db.ambulance_accepted.find_one({"user_username": username_form})
            if data:
                del data['ref_id']
                db.ambulance_pending.insert_one(data)
                db.ambulance_accepted.delete_one({"user_username": username_form})
            msg_flag = 3
            # flash("Ambulance Rebooked Successfully")
            # Handle rebooking logic here
             # Placeholder, replace with actual logic
            
    if msg_flag == 0:
        flash("Please Rebook again")
    elif msg_flag == 1:
        flash("Please wait, Your ambulance will be arriving soon")
    elif msg_flag == 2:
        flash("Please wait while we find you an ambulance")
    elif msg_flag == 3:
        flash("Ambulance Rebooked Successfully\nPlease wait while we find you an ambulance")
    print(user_latitude)
    print(ambulance_latitude)
    print(ambulance_longitude)
    return render_template('getwellsoon.html', username=username, password=password, user_latitude=user_latitude,user_longitude=user_longitude,ambulance_latitude=ambulance_latitude,ambulance_longitude=ambulance_longitude)

@app.route('/user_nav/<string:username>/<string:password>', methods=["GET", "POST"])
def user_nav(username,password):
    
    # ans=0
    msg_flag = 0
    data = db.user_reg.find_one({"username": username})
    try:
        result = db.hospital_accepted.find_one({"user_username": username})
        
        back_to_form = db.hospital_pending.find_one({"user_username": username})
        if back_to_form is None and result is None:
            raise TypeError('Data not found anywhere')
        elif result is None and back_to_form is not None:
            raise ValueError('Data not found in collection1')
        # ans = result['ref_id']
        hospital_temp = db.hospital_reg.find_one({"uid": result['ref_id']})
        if hospital_temp is None:
            # Handle the case where hospital_temp is None
            # raise ValueError('Hospital data not found for the given uid')
            hospital_address= "AMRI Hospitals Dhakuria, Block-A, Scheme-L11, P-4&5, Gariahat Rd, Dhakuria, Ward Number 90, Kolkata, West Bengal 700029"
        else:
            hospital_result = db.hospital_data.find_one({"Hospital Name": hospital_temp['hospitalName']})
            if hospital_result:
                hospital_address=hospital_result['Address']
        msg_flag = 1
        # flash("Please wait, Your ambulance will be arriving soon")
    except ValueError:
        result = db.hospital_pending.find_one({"user_username": username})
        hospital_temp = db.hospital_reg.find_one({"uid": result['ref_id'][0]})
        if hospital_temp is None:
            # Handle the case where hospital_temp is None
            # raise ValueError('Hospital data not found for the given uid')
            hospital_address= "AMRI Hospitals Dhakuria, Block-A, Scheme-L11, P-4&5, Gariahat Rd, Dhakuria, Ward Number 90, Kolkata, West Bengal 700029"
        else:
            hospital_result = db.hospital_data.find_one({"Hospital Name": hospital_temp['hospitalName']})
            if hospital_result:
                hospital_address=hospital_result['Address']
        msg_flag = 2
        # flash("Please wait while we find you an ambulance")
    except TypeError:
        msg_flag = 0
        # return redirect(url_for('user_booking', username=username, password=password))
        current_date = datetime.strptime(datetime.now().strftime("%Y-%m-%d"), "%Y-%m-%d")
        feedback_data = db.app_feedback.find_one({'ref_id': data['uid']})
        if feedback_data is None:
            days_difference = None
        else:
            previous_date = datetime.strptime(feedback_data['date'], "%Y-%m-%d")
            days_difference = (current_date - previous_date).days
        if days_difference is None or days_difference > 30:
            db.app_feedback.delete_one({'ref_id': data['uid']})
            return redirect(url_for('user_feedback', username=username,password=password))
        else:
            return redirect(url_for('user_booking', username=username, password=password))

    # result = db.ambulance_accepted.find_one({"user_username": username})
    
    print("hello")
    print(result)
    # ans=0
    if result is not None:
        # ans = result['ref_id']
        print("Found result:", result['ref_id'])
    else:
        print("No matching document found.")
    user_latitude=result['latitude']
    user_longitude=result['longitude']
    print(user_latitude)
    print(user_longitude)
    # ambulance_result=db.ambulance_reg.find_one({"uid":ans})
    # ambulance_latitude=0.0
    # ambulance_longitude=0.0
    # if ambulance_result:
    #     ambulance_latitude=ambulance_result['latitude']
    #     ambulance_longitude=ambulance_result['longitude']
    print(hospital_address)
    # print(hospital_longitude)


    if request.method == "POST":
        username_form = request.form.get('username')  # Get username from the form
        password_form = request.form.get('password')
        action = request.form.get('action')  # Get the action value
        print(action)
        if action == 'cancel':
            collection_pairs = [db.hospital_pending, db.hospital_accepted]
            for c1 in collection_pairs:
                c1.delete_one({"user_username": username_form})
            msg_flag = 0
            # return redirect(url_for('user_booking', username = username, password = password))
            # current_date = datetime.strftime(datetime.now(), "%Y-%m-%d")
            # feedback_data = db.app_feedback.find_one({'ref_id': data['uid']})
            # if feedback_data is None:
            #     days_difference = None
            # else:
            #     previous_date = datetime.strftime(feedback_data['date'], "%Y-%m-%d")
            #     days_difference = (current_date - previous_date).days
            # if days_difference is None or days_difference > 30:
            #     db.app_feedback.delete_one({'ref_id': data['uid']})
            #     return redirect(url_for('user_feedback', username=username,password=password))
            # else:
            return redirect(url_for('user_booking', username=username, password=password))
        # elif action == 'rebooking':
        #     print("hi")
        #     data = db.ambulance_accepted.find_one({"user_username": username_form})
        #     if data:
        #         del data['ref_id']
        #         db.ambulance_pending.insert_one(data)
        #         db.ambulance_accepted.delete_one({"user_username": username_form})
        #     msg_flag = 3
            # flash("Ambulance Rebooked Successfully")
            # Handle rebooking logic here
             # Placeholder, replace with actual logic
            
    if msg_flag == 0:
        flash("")
    elif msg_flag == 1:
        flash("Appointment has been accpeted")
    elif msg_flag == 2:
        flash("Appointment is pending")
    print(user_latitude)
    # print(hospital_latitude)
    # print(hospital_longitude)
    return render_template('user_nav.html', username=username, password=password, user_latitude=user_latitude,user_longitude=user_longitude,hospital_address=hospital_address)

@app.route('/user_feedback/<string:username>/<string:password>', methods=["GET", "POST"])
def user_feedback(username, password):
    # ref_data = db.hospital_accepted.find_one({'user_username': user_username})
    ref_data = db.user_reg.find_one({'username': username})
    if request.method == 'POST':
        rating = int(request.form['feedback-star']) + 1
        feedback_text = request.form['feedback-text']
        
        feedback_data = {
            'user': ref_data['name'],
            'date': datetime.strftime(datetime.now(), "%Y-%m-%d"),
            'time': datetime.strftime(datetime.now(), "%H:%M"),
            'rating': rating,
            'feedback_text': feedback_text,
            'ref_id': ref_data['uid']
        }
        db.app_feedback.insert_one(feedback_data)

        return redirect(url_for('user_booking',username=username,password=password))
    return render_template('user_feedback.html', username=username, password=password)

# @app.route('/user_map/<string:username>')
# def user_map(username):
#     print(username)

#         # Check if the form data is being received correctly
#     print("Received username:", username)
#         # print("Received password:", password)

#         # Attempt to find a document in the MongoDB collection
#     result = db.ambulance_accepted.find_one({"user_username": username})
#     print(result)
#     ans=0
#     if result is not None:
#         ans = result['ref_id']
#         print("Found result:", ans)
#     else:
#         print("No matching document found.")
#     user_latitude=result['latitude']
#     user_longitude=result['longitude']
#     print(user_latitude)
#     print(user_longitude)
#     ambulance_result=db.ambulance_reg.find_one({"uid":ans})
#     ambulance_latitude=0.0
#     ambulance_longitude=0.0
#     if ambulance_result:
#         ambulance_latitude=ambulance_result['latitude']
#         ambulance_longitude=ambulance_result['longitude']
#     print(ambulance_latitude)
#     print(ambulance_longitude)
        
#     return render_template('user_map.html',user_latitude=user_latitude,user_longitude=user_longitude,ambulance_latitude=ambulance_latitude,ambulance_longitude=ambulance_longitude,username=username)

@app.route('/payment_portal/<string:username>/<string:password>/<string:user_username>', methods=["GET", "POST"])
def payment_portal(username, password, user_username):
    if request.method == "POST":
        hospitalName = request.form.get('hospitalName')
        print(hospitalName)
        result = db.hospital_data.find_one({"Hospital Name": hospitalName})
        print(result)
        destination = " "
        if result:
            destination = result['Address']
            print(destination)
        else:
            return 'Hospital not found'
        print(destination)
        return render_template('payment_portal.html', username=username, password=password, user_username=user_username, destination=destination)
    
    # Handle GET requests for the same route
    return render_template('payment_portal.html', username=username, password=password, user_username=user_username, destination=None)

@app.route('/calculate/<string:username>/<string:password>/<string:user_username>', methods=["GET", "POST"])
def calculate(username, password, user_username):
    if request.method == "POST":
        result = request.form.get("result")  # Get the result from the hidden input field
        cost=request.form.get("cost")
        username=request.form.get("username")
        password=request.form.get("password")
        user_username=request.form.get("user_username")
        payment_method = request.form.get("paymentMethod")
        print("hello")
        print(result)
        print(payment_method)

        user_data = db.ambulance_accepted.find_one({'user_username': user_username})
        if result and payment_method:
            data = {
                "name": user_data['name'],
                "user_username": user_data['user_username'],
                "reason": user_data['reason'],
                "phone": user_data['phone'],
                "address": user_data['address'],
                "email": user_data['email'],
                "pickup_location": user_data['pickup_location'],
                "latitude": user_data['latitude'],
                "longitude": user_data['longitude'],
                "date": user_data['date'],
                "time": user_data['time'],
                "booking_type": user_data['booking_type'],
                "ambulance_id": user_data['ref_id'],
                "result": result,  # Store the result in your database
                "cost":cost,
                "paymentMethod": payment_method,  # Store the payment method in your database
            }

            # Store data in MongoDB
            db.trip_history.insert_one(data)
            gmail_user = 'healthlinkarchitects@gmail.com'
            gmail_password = 'hzex zsht hnkk ephu'
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(gmail_user, gmail_password)

                # user_username = request.args.get('user_username')
                # hosp = db.hospital_reg.find_one({'uid': user['ref_id']})
            if user_data:
                to_email = user_data['email']

                subject = 'Payment Confirmation'
                body = "Payment Successful, Thank You. We hope you get well soon."
                msg = MIMEMultipart()
                msg['From'] = gmail_user
                msg['To'] = to_email
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))

                text = msg.as_string()
                server.sendmail(gmail_user, to_email, text)

                server.quit()

                flash("Email sent successfully")
            else:
                flash("User not found")

            current_date = datetime.strptime(user_data['date'], "%Y-%m-%d")
            feedback_data = db.app_feedback.find_one({'ref_id': user_data['ref_id']})
            if feedback_data is None:
                days_difference = None
            else:
                previous_date = datetime.strptime(feedback_data['date'], "%Y-%m-%d")
                days_difference = (current_date - previous_date).days
            if days_difference is None or days_difference > 30:
                db.app_feedback.delete_one({'ref_id': user_data['ref_id']})
                return redirect(url_for('ambulance_feedback', user_username=user_username, username=username,password=password))
            else:
                db.ambulance_accepted.delete_one({'user_username': user_username})
                return redirect(url_for('ambulance_notification',username=username,password=password))

            # return redirect(url_for("ambulance_feedback", user_username=user_username, username = username, password = password))

    # Handle GET requests for the /calculate route
    return render_template("payment_portal.html", username=username, password=password, user_username=user_username)


@app.route('/ambulance_feedback/<string:user_username>/<string:username>/<string:password>', methods=["GET", "POST"])
def ambulance_feedback(user_username, username, password):
    ref_data = db.ambulance_accepted.find_one({'user_username': user_username})
    ambu_data = db.ambulance_reg.find_one({'username': username})
    if request.method == 'POST':
        rating = int(request.form['feedback-star']) + 1
        feedback_text = request.form['feedback-text']
        
        feedback_data = {
            'user': ambu_data['driverName'],
            'date': ref_data['date'],
            'time': ref_data['time'],
            'rating': rating,
            'feedback_text': feedback_text,
            'ref_id': ref_data['ref_id']
        }
        db.app_feedback.insert_one(feedback_data)
        db.ambulance_accepted.delete_one({'user_username': user_username})
        return redirect(url_for('ambulance_notification',username=username,password=password))
    return render_template('ambulance_feedback.html', user_username=user_username, username=username, password=password)
    
# @app.route('/getuserLoc/<string:user_username>')
# def getuserLoc(user_username):
#     result = db.ambulance_accepted.find_one({"user_username": user_username})
#     if result:
#         latitude = result['latitude']
#         longitude = result['longitude']
#         return render_template('getuserLoc.html', lati=latitude, longi=longitude)
#     else:
#         return "Location not available"

# @app.route('/getuserLoc1/<string:name>')
# def getuserLoc1(name):
#     result = db.ambulance1_accepted.find_one({"name": name})
#     if result:
#         latitude = result['latitude']
#         longitude = result['longitude']
#         return render_template('getuserLoc1.html', lati=latitude, longi=longitude)
#     else:
#         return "Location not available"

# @app.route('/getuserLoc2/<string:name>')
# def getuserLoc2(name):
#     result = db.ambulance2_accepted.find_one({"name": name})
#     if result:
#         latitude = result['latitude']
#         longitude = result['longitude']
#         return render_template('getuserLoc2.html', lati=latitude, longi=longitude)
#     else:
#         return "Location not available"

@app.route('/gethospitalLoc/<string:user_username>')
def gethospitalLoc(user_username):
    temp = db.hospital_accepted.find_one({"user_username": user_username})
    data = db.hospital_reg.find_one({'uid': temp['ref_id']})
    result = db.hospital_data.find_one({"Hospital Name": data["hospitalName"]})
    if result:
        address = result['Address']
        return jsonify(address=address)
    else:
        return "Location not available"

# @app.route('/gethospitalLoc1')
# def gethospitalLoc1():
#     result = db.hospital_list.find_one({"Hospital Name": "AMRI -Dhakuria"})
#     if result:
#         address = result['Address']
#         return render_template('gethospitalLoc1.html', address=address)
#     else:
#         return "Location not available"

# @app.route('/gethospitalLoc2')
# def gethospitalLoc2():
#     result = db.hospital_list.find_one({"Hospital Name": "IRIS Health Services Limited"})
#     if result:
#         address = result['Address']
#         return render_template('gethospitalLoc2.html', address=address)
#     else:
#         return "Location not available"



# Reset Password Function Starts Here

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        ref_tag = request.form['ref_id']
        if ref_tag == 'u':
            data = db.user_reg.find_one({'email': email})
            if data:
                # Generate a password reset token (you can use a library like itsdangerous for this)
                # Send reset password email
                token = generate_reset_token()
                db.reset_password.insert_one({'email': email, 'ref_tag': 'u', 'otp': token})
                send_reset_email(email, token)
                return redirect(url_for('change_password'))
            else:
                flash('Email not registered')
        elif ref_tag == 'a':
            data = db.ambulance_reg.find_one({'email': email})
            if data:
                # Generate a password reset token (you can use a library like itsdangerous for this)
                # Send reset password email
                token = generate_reset_token()
                db.reset_password.insert_one({'email': email, 'ref_tag': 'a', 'otp': token})
                send_reset_email(email, token)
                return redirect(url_for('change_password'))
            else:
                flash('Email not registered')
        elif ref_tag == 'h':
            data = db.hospital_reg.find_one({'email': email})
            if data:
                # Generate a password reset token (you can use a library like itsdangerous for this)
                # Send reset password email
                token = generate_reset_token()
                db.reset_password.insert_one({'email': email, 'ref_tag': 'h', 'otp': token})
                send_reset_email(email, token)
                return redirect(url_for('change_password'))
            else:
                flash('Email not registered')
    return render_template('index.html')

def generate_reset_token():
    # Implement token generation logic here
    otp = ''.join(str(random.randint(0, 9)) for _ in range(6))
    if otp != '00000' and not db.reset_password.find_one({'otp': otp}):
        return otp

def send_reset_email(email, otp):

    gmail_user = 'healthlinkarchitects@gmail.com'
    gmail_password = 'hzex zsht hnkk ephu'
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(gmail_user, gmail_password)

                # user_username = request.args.get('user_username')
                # hosp = db.hospital_reg.find_one({'uid': user['ref_id']})
    if email:
        subject = 'Password Reset OTP'
        body = "Here is the OTP for your account password reset. OTP: " + otp + " Please do not share this with anyone."
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        text = msg.as_string()
        server.sendmail(gmail_user, email, text)

        server.quit()
    return "Email sent"

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    # Validate the token (itsdangerous can be used for this)
    if request.method == 'POST':
        otp = request.form['OTP']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        data = db.reset_password.find_one({'otp': otp})
        if data:
            if new_password == confirm_password:
                if data['ref_tag'] == 'u':
                    db.user_reg.update_one({'email': data['email']}, {'$set': {'password': new_password}})
                elif data['ref_tag'] == 'a':
                    db.ambulance_reg.update_one({'email': data['email']}, {'$set': {'password': new_password}})
                elif data['ref_tag'] == 'h':
                    db.hospital_reg.update_one({'email': data['email']}, {'$set': {'password': new_password}})
                flash("Password reset successfully")
                db.reset_password.delete_one({'otp': otp})
                return redirect(url_for('index'))
            else:
                flash("Passwords do not match")
        else:
            flash("Invalid or expired OTP")
    
    return render_template('change_password.html')

# Reset Pawword Function Ends Here



if __name__ == '__main__':
    location_thread = threading.Thread(target=update_location)
    location_thread.daemon = True
    location_thread.start()

    app.run(debug=True)
