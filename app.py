from flask import Flask, request, jsonify
import pyrebase
import datetime
import json

with open('credentials/firebase.json') as f:
    auth = json.load(f)
    f.close()

config = {
    "apiKey": auth["private_key"],
    "authDomain": auth["project_id"]+".firebaseapp.com",
    "databaseURL": "https://" + auth["project_id"] + ".firebaseio.com/",
    "storageBucket": auth["project_id"]+ ".appspot.com",
    "serviceAccount": "credentials/firebase.json"}

firebase = pyrebase.initialize_app(config)

app = Flask(__name__)


@app.route('/')
def healthCheck():
    return jsonify({"Status": "OK"})


@app.route('/dialogflow', methods=['POST'])
def firebase_fulfillment():
    req = request.json
    print (req)
    action = req["queryResult"]["action"]
    print (action)
    if action == "save_complaint":
        response = create_complaint(req)
    elif action == "initiate_call":
        response = check_mobile(req);
    elif action == "save_mobile":
        response = save_mobile(req)
    elif action == "save_call":
        response = create_call_complaint(req)
    else:
        response = {
        "fulfillmentText": "Something went wrong. Please try again later."
        }
    return jsonify(response)


def save_mobile(data):
    firebase_uid = data['session'].split('/')[-1]
    db = firebase.database()
    mobile = data["queryResult"]["parameters"]["phone_number"]
    db.child("users").child(firebase_uid).child("Mobile Number").set(str(mobile))
    response = {
    "fulfillmentText": "I've saved your phone number.",
    "followupEventInput": {
    "name": "continue_call_details",
    "languageCode": "en-US"
    }
    }
    return response


def create_call_complaint(data):
    firebase_uid = data['session'].split('/')[-1]
    firebase_uid = data['session'].split('/')[-1]
    contexts = data['queryResult']['outputContexts']
    for i in contexts:
        if ('call_data' in i['name']):
            context = i
            break

    date = datetime.datetime.now()
    date = date.strftime("%d-%m-%Y")

    raw_params = context['parameters']

    free_time = dict({})

    free_time = {
    "Time": raw_params["time"],
    "Date": raw_params["date"]
    }
    complaint_params = {
        "Product Type": raw_params["product_type"],
        "Type": "Phone Call",
        "Issue Type": raw_params["issue_type"],
        "Model Number": raw_params["model_number"],
        "Serial Number": raw_params["serial_number"],
        "Status": "Open",
        "Date": date,
        "Time Slot Chosen": "0",
        "Time Slots": {"Slot 1": {"Time": "0", "Date": "0"},
            "Slot 2": {"Time": "0", "Date": "0"},
            "Slot 3": {"Time": "0", "Date": "0"}},
        "Progress": "Under review.",
        "Free Time": free_time,
        "Details of Call": {
        "Time": "0",
        "Date": "0"}
        }
    db = firebase.database()
    firebase_response = db.child(
        'user_data').child(
        firebase_uid).child(
        'Complaints').push(complaint_params)

    fulfillment_response = {
        "fulfillmentText":
        "You appointment was successfully registered. The reference number for this complaint is " + firebase_response["name"]}
    return fulfillment_response



def check_mobile(data):
    firebase_uid = data['session'].split('/')[-1]
    db = firebase.database()
    mobile = db.child("users").child(firebase_uid).child("Mobile Number").get().val()
    if mobile == "0" or mobile == None:
        response = {
        "followupEventInput": {
        "name": "request_mobile",
        "languageCode": "en-US"
        }}
    else:
        print (mobile)
        response = {
        "followupEventInput": {
        "name": "continue_call_details",
        "languageCode": "en-US"
        }
        }
    return response



@app.route('/getcomplaint/', methods=['GET'])
def return_complaints():

    user_id = request.args.get('firebase_uid')
    db = firebase.database()
    data = db.child("user_data").child(user_id).child("Complaints").get().val()
    return jsonify({"Status": "OK", "Data": data, "Response": 200})


def create_complaint(data):

    firebase_uid = data['session'].split('/')[-1]
    contexts = data['queryResult']['outputContexts']
    for i in contexts:
        if ('globals' in i['name']):
            context = i
            break

    date = datetime.datetime.now()
    date = date.strftime("%d-%m-%Y")

    raw_params = context['parameters']
    complaint_params = {
        "Product Type": raw_params["product_type"],
        "Type": "House Call",
        "Issue Type": raw_params["issue_type"],
        "Description": raw_params["description"],
        "Model Number": raw_params["model_number"],
        "Serial Number": raw_params["serial_number"],
        "Status": "Open",
        "Date": date,
        "Time Slot Chosen": "0",
        "Time Slots": {"Slot 1": {"Time": "0", "Date": "0"},
            "Slot 2": {"Time": "0", "Date": "0"},
            "Slot 3": {"Time": "0", "Date": "0"}},
        "Progress": "Under review.",
        "Free Time": {
        "Date": ["0"],
        "Time": ["0"],
        },
        "Details of Call": {
        "Time": "0",
        "Date": "0"}
        }

    db = firebase.database()
    firebase_response = db.child(
        'user_data').child(
        firebase_uid).child(
        'Complaints').push(complaint_params)

    fulfillment_response = {
        "fulfillmentText":
        "You complaint was successfully registered. The reference number for this complaint is " + firebase_response["name"]}
    return fulfillment_response


@app.route('/choosetimeslot/', methods=["POST"])
def chooseTimeSlot():

    req = request.json
    firebase_uid = req["firebase_uid"]
    complaint_id = req["complaint_id"]
    db = firebase.database();
    db.child("user_data").child(
        firebase_uid).child(
        "Complaints").child(
        complaint_id).update({
        "Time Slot Chosen": req["time_slot"]
        })
    return jsonify({"Status": "200", "Message": "successfully chosen time"})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3000, debug=True)
