from flask import Flask, request, jsonify
import pyrebase
import datetime
import json
import pprint
import uuid

with open('credentials/firebase.json') as f:
    auth = json.load(f)
    f.close()

config = {
    "apiKey": auth["private_key"],
    "authDomain": auth["project_id"] + ".firebaseapp.com",
    "databaseURL": "https://" + auth["project_id"] + ".firebaseio.com/",
    "storageBucket": auth["project_id"] + ".appspot.com",
    "serviceAccount": "credentials/firebase.json"}

firebase = pyrebase.initialize_app(config)

app = Flask(__name__)


@app.route('/')
def health_check():
    return jsonify({"Status": "OK"})


def check_address(data):
    """
    Checks if the address is present in the database. If the address is
    there, it checks if the mobile number is present.
    :param data:
    :return:
    """

    firebase_uid = data['session'].split('/')[-1]
    db = firebase.database()
    pincode = db.child("user_data").child(firebase_uid).child("Address").child("Pincode").get().val()
    if pincode == "0" or pincode is None:
        print("Address not found.")
        response = {
            "followupEventInput": {
                "name": "request_address",
                "languageCode": "en-US"
            }}
    else:
        response = check_mobile(data)
    return response


def save_address(data):
    """
    This saves the address entered by the user and then
    checks if the mobile number is there.
    :param data:
    :return:
    """
    print("Saving address.")
    firebase_uid = data['session'].split('/')[-1]
    db = firebase.database()
    contexts = data['queryResult']['outputContexts']
    for i in contexts:
        if 'address_data' in i['name']:
            context = i
            break

    pincode = str(context["parameters"]["pincode"])
    address = context["parameters"]["address"]
    temp = {
        "Main": address,
        "Pincode": pincode
    }
    db.child("user_data").child(firebase_uid).child("Address").set(temp)
    print("Address saved. Checking if mobile number is present.")
    response = check_mobile(data)
    print("Response from Check Mobile function = ")
    pprint.pprint(response)
    return response


def check_mobile(data):

    """
    It checks if the mobile number is present in the database. If it is, it
    continues the conversation, otherwise it asks the user.
    :param data:
    :return:
    """

    firebase_uid = data['session'].split('/')[-1]
    db = firebase.database()
    follow_up_event = "continue_house"
    mobile = db.child("user_data").child(firebase_uid).child("Mobile Number").get().val()
    try:
        origin = data["queryResult"]["fulfillmentMessages"][1]["payload"]
        if origin == "confirmedCall":
            follow_up_event = "continue_call"
    except:
        pass
    if mobile == "0" or mobile is None:
        print("Mobile number not found.")
        response = {
            "followupEventInput": {
                "name": "request_mobile",
                "languageCode": "en-US"
            }}
    else:
        print("Mobile number found: " + mobile)
        response = {
            "followupEventInput": {
                "name": follow_up_event,
                "languageCode": "en-US"
            }
        }
    return response


def save_mobile(data):

    """
    This function saves the mobile number provided by the user to the database.
    :param data:
    :return:
    """
    firebase_uid = data['session'].split('/')[-1]
    db = firebase.database()
    mobile = data["queryResult"]["parameters"]["phone_number"]
    follow_up_event: str = "continue_house"
    for i in data["queryResult"]["outputContexts"]:
        if "confirm-call-followup" in i["name"]:
            follow_up_event = "continue_call"
    db.child("user_data").child(firebase_uid).child("Mobile Number").set(str(mobile))
    response = {
        "fulfillmentText": "Great! It looks like I have everything needed to contact you.",
        "followupEventInput": {
            "name": follow_up_event,
            "languageCode": "en-US"
        }
    }
    return response


@app.route('/dialogflow', methods=['POST'])
def firebase_fulfillment():

    """
    This function all the fulfillment requests from Dialogflow.
    :return:
    """
    req = request.json
    pprint.pprint(req)
    action = req["queryResult"]["action"]
    print("Dialogflow action = " + action)
    if action == "save_house_ticket":
        response = create_complaint(req)
    elif action == "check_address":
        response = check_address(req)
    elif action == "save_address":
        response = save_address(req)
    elif action == "check_mobile":
        response = check_mobile(req)
    elif action == "save_mobile":
        response = save_mobile(req)
    elif action == "save_call_ticket":
        response = create_call_complaint(req)
    else:
        response = {
            "fulfillmentText": "Something went wrong. Please try again later."
        }
    print("Response to Dialogflow: ")
    pprint.pprint(response)
    return jsonify(response)


def create_call_complaint(data):
    firebase_uid = data['session'].split('/')[-1]
    contexts = data['queryResult']['outputContexts']
    for i in contexts:
        if 'call_data' in i['name']:
            context = i
            break

    date = datetime.datetime.now()
    date = date.strftime("%d-%m-%Y")

    raw_params = context['parameters']

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

    complaint_id = str(uuid.uuid4())[:8]
    db = firebase.database()
    db.child(
        'user_data').child(
        firebase_uid).child(
        'Complaints').child(complaint_id).set(complaint_params)

    fulfillment_response = {
        "fulfillmentText":
            "You appointment was successfully registered. The reference number for this complaint is " + complaint_id}
    return fulfillment_response


@app.route('/getcomplaint/', methods=['GET'])
def return_complaints():

    """
    This function returns all the complaints for a particular user.
    :return:
    """
    user_id = request.args.get('firebase_uid')
    db = firebase.database()
    data = db.child("user_data").child(user_id).child("Complaints").get().val()
    return jsonify({"Status": "OK", "Data": data, "Response": 200})


def create_complaint(data):
    firebase_uid = data['session'].split('/')[-1]
    contexts = data['queryResult']['outputContexts']
    for i in contexts:
        if 'visit_data' in i['name']:
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

    complaint_uid = str(uuid.uuid4())[:8]
    db = firebase.database()
    db.child(
        'user_data').child(
        firebase_uid).child(
        'Complaints').child(complaint_uid).set(complaint_params)

    fulfillment_response = {
        "fulfillmentText":
            "You complaint was successfully registered. The reference number for this complaint is " + complaint_uid}
    return fulfillment_response


@app.route('/choosetimeslot/', methods=["POST"])
def choose_time_slot():
    req = request.json
    firebase_uid = req["firebase_uid"]
    complaint_id = req["complaint_id"]
    db = firebase.database()
    db.child("user_data").child(
        firebase_uid).child(
        "Complaints").child(
        complaint_id).update({"Time Slot Chosen": req["time_slot"]
                              })
    return jsonify({"Status": "200", "Message": "successfully chosen time"})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3000, debug=True)
