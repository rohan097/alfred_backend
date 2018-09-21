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
    response = create_complaint(req)
    fulfillment_response = {
        "fulfillmentText": "You complaint was successfully registered. The reference number for this complaint is " + response["name"]}
    return jsonify(fulfillment_response)


@app.route('/getcomplaint/', methods=['GET'])
def return_complaints():

    user_id = request.args.get('firebase_uid')
    db = firebase.database()
    data = db.child("user_data").child(user_id).child("Complaints").get().val()
    complaint_ids = data.keys()
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
        "Issue Type": raw_params["issue_type"],
        "Description": raw_params["description"],
        "Model Number": raw_params["model_number"],
        "Serial Number": raw_params["serial_number"],
        "Status": "Open",
        "Date": date
        }

    db = firebase.database()
    firebase_response = db.child(
        'user_data').child(
        firebase_uid).child(
        'Complaints').push(complaint_params)
    return firebase_response



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3000, debug=True)
