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

    pincode = str(int(context["parameters"]["pincode"]))
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
        origin = data["queryResult"]["fulfillmentMessages"][1]["payload"]["origin"]
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
    follow_up_event = "continue_house"
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


def validate_model_serial(data):
    """
    This function validates the serial number, model number and product type.
    :param data:
    :return:
    """
    print("Validating model and serial number.")
    firebase_uid = data['session'].split('/')[-1]
    db = firebase.database()
    serial_number = data["queryResult"]["parameters"]["serial_number"]
    model_number = data["queryResult"]["parameters"]["model_number"]
    for i in data["queryResult"]["outputContexts"]:
        if "visit_data" in i["name"] or "call_data" in i["name"]:
            product = i["parameters"]["product_type"]
            if "call_data" in i["name"]:
                support_type = "_call"
                follow_up_event = "confirm-call"
            else:
                support_type = "_visit"
                follow_up_event = "confirm-house"

    product_data = db.child("Products").get().val()
    if serial_number in product_data.keys():
        # Serial number exists.
        if product == product_data[serial_number]["Product Type"]:
            if model_number == product_data[serial_number]["Model Number"]:
                # Model number exists and matches with the serial number
                # Model number and serial number match with product type
                message = "Confirm ticket?"
            else:
                # Model number and serial number do not match with the product type.
                message = "The model number you have entered is incorrect."
                follow_up_event = "request_model_serial" + support_type
        else:
            # Model number is not matching with serial number
            message = "The serial number you have entered doesn't match with the product type."
            follow_up_event = "request_model_serial" + support_type
    else:
        message = "The serial number you have entered is incorrect."
        follow_up_event = "request_model_serial" + support_type

    response = {
        "fulfillmentText": message,
        "followupEventInput": {
            "name": follow_up_event,
            "languageCode": "en-US"
        }
    }
    return response


def view_tickets(data):

    firebase_uid = data["session"].split('/')[-1]
    db = firebase.database()
    user_data = db.child("user_data").child(firebase_uid).child("Complaints").get().val()
    if len(user_data) == 0:
        message = "You don't have any tickets."
    else:
        message = "The details of your tickets are: \n"
        for i in user_data:
            message += "ID: " + str(i) + "\n"+\
                       "Progress: " + user_data[i]["Progress"] + "\n" +\
                       "Product: " + user_data[i]["Product Type"] + "\n" +\
                       "Issue Type: " + user_data[i]["Issue Type"] + "\n"
            if user_data[i]["Type"] == "Phone Call":
                if user_data[i]["Details of Call"]["Date"] == "0":
                    message += "Details of Call: To be confirmed.\n\n"
                else:
                    message += "Details of Call: \n" +\
                               "\t\tTime: " + user_data[i]["Details of Call"]["Time"] +\
                               "\t\tDate: " + user_data[i]["Details of Call"]["Date"] + "\n\n"
            else:
                if user_data[i]["Time Slots"]["Slot 1"]["Date"] == "0":
                    message += "Available Time Slots: To be confirmed.\n\n"
                else:
                    message += "Available Time Slots: \n" +\
                               "\t\tSlot 1 - " +\
                               "\n\t\t\t\tDate: " + user_data[i]["Time Slots"]["Slot 1"]["Date"] +\
                               "\n\t\t\t\tTime: " + user_data[i]["Time Slots"]["Slot 1"]["Time"] + \
                               "\n\t\tSlot 2 - " + \
                               "\n\t\t\t\tDate: " + user_data[i]["Time Slots"]["Slot 2"]["Date"] + \
                               "\n\t\t\t\tTime: " + user_data[i]["Time Slots"]["Slot 2"]["Time"] + \
                               "\n\t\tSlot 3 - " + \
                               "\n\t\t\t\tDate: " + user_data[i]["Time Slots"]["Slot 3"]["Date"] + \
                               "\n\t\t\t\tTime: " + user_data[i]["Time Slots"]["Slot 3"]["Time"] + "\n"
                    if user_data[i]["Time Slot Chosen"] == "0":
                        message += "Time Slot Chosen: None"
                    else:
                        message += "Time Slot Chosen: Slot " + user_data[i]["Time Slot Chosen"] + "\n\n"
    response = {
        "fulfillmentText": message
    }
    return response


def delete_ticket(data):
    firebase_uid = data["session"].split('/')[-1]
    for i in data["queryResult"]["outputContexts"]:
        if "ticket_params" in i["name"]:
            ticket_id = i["parameters"]["ticket_id"]
            db = firebase.database()
            db.child("user_data").child(firebase_uid).child("Complaints").child(ticket_id).remove()
    response = {
        "fulfillmentText": "Ticket removed."
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
        response = create_ticket(req)
    elif action == "check_address":
        response = check_address(req)
    elif action == "save_address":
        response = save_address(req)
    elif action == "check_mobile":
        response = check_mobile(req)
    elif action == "save_mobile":
        response = save_mobile(req)
    elif "validate_model_serial" in action:
        response = validate_model_serial(req)
    elif action == "save_call_ticket":
        response = create_call_ticket(req)
    elif action == "view_tickets":
        response = view_tickets(req)
    elif action == "delete_ticket":
        response = delete_ticket(req)
    else:
        response = {
            "fulfillmentText": "Something went wrong. Please try again later."
        }
    print("Response to Dialogflow: ")
    pprint.pprint(response)
    return jsonify(response)


def create_call_ticket(data):
    """
    This function creates a record of the complaint issued by the user.
    :param data:
    :return:
    """
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
        "Time": raw_params["free_time"]["time"],
        "Date": raw_params["free_date"]["date"]
    }
    ticket_params = {
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

    ticket_id = str(uuid.uuid4())[:8]
    pprint.pprint(ticket_params)
    db = firebase.database()
    db.child(
        'user_data').child(
        firebase_uid).child(
        'Complaints').child(ticket_id).set(ticket_params)

    fulfillment_response = {
        "fulfillmentText":
            "You appointment was successfully registered. The reference number for this ticket is " + ticket_id +
            ". The timings of your call would be confirmed soon. You check the status by asking me or by going to the "
            "\"Tickets\" section of the app."}
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


def create_ticket(data):
    """
    This creates a record of a ticket for a house call.
    :param data:
    :return:
    """
    firebase_uid = data['session'].split('/')[-1]
    contexts = data['queryResult']['outputContexts']
    for i in contexts:
        if 'visit_data' in i['name']:
            context = i
            break

    date = datetime.datetime.now()
    date = date.strftime("%d-%m-%Y")

    raw_params = context['parameters']
    ticket_params = {
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
    ticket_id = str(uuid.uuid4())[:8]
    db = firebase.database()
    db.child(
        'user_data').child(
        firebase_uid).child(
        'Complaints').child(ticket_id).set(ticket_params)

    fulfillment_response = {
        "fulfillmentText":
            "You ticket was successfully registered. The reference number is " + ticket_id +
            ". Based on the availability of our agents, we will give you three time slots to choose from. You can "
            "either go to the \"Tickets\" section of the app and update your preference or do so by talking to me."}
    return fulfillment_response


@app.route('/choosetimeslot/', methods=["POST"])
def choose_time_slot():
    req = request.json
    firebase_uid = req["firebase_uid"]
    ticket_id = req["complaint_id"]
    db = firebase.database()
    db.child("user_data").child(
        firebase_uid).child(
        "Complaints").child(
        ticket_id).update({"Time Slot Chosen": req["time_slot"]
                           })
    return jsonify({"Status": "200", "Message": "successfully chosen time"})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3000, debug=True)
