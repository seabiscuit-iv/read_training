import os
import json
from flask import Flask, request, jsonify, render_template
import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials
<<<<<<< HEAD
from google.auth.transport import requests
=======
import requests
>>>>>>> 1b1c419e2ba011dfe8f158b9bcd9d0256a0964f3

__name__ = 'LearnApp'

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY = 'absolute',
)
app.config.from_pyfile('config.py', silent=True)

cred = credentials.Certificate("key.json")

default_app = firebase_admin.initialize_app(cred)
db = firestore.client()
db.collection("paragraphs").document("0").set({"Title": "Games at GDC", "Length": 24})
    
try:
    os.makedirs(app.instance_path)
except OSError:
    pass
    
@app.route("/signin") 
def sign_in_email_password():
    email = request.args.get('email')
    password = request.args.get('email')
    
    payload = json.dumps({"email":email, "password":password})
    FIREBASE_WEB_API_KEY = 'the web API key here' 
    rest_api_url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"

    r = requests.Request(["POST"], rest_api_url,
                  params={"key": FIREBASE_WEB_API_KEY},
                  data=payload)

    print(r.json())
    return r.json()
    

@app.route('/paragraph')
def hello():
    #given a paragraph id, probably random, making sure it isn't one the user hasn't read
    #return a paragraph JSON based on what we expect
    id = 0
    try:
        doc = db.collection("paragraphs").document(f"{id}").get()
        return jsonify(doc.to_dict())
    except Exception as e:
        return f"Error: {e}"



@app.route('/analyze')
def analyze():
    #upon submission of text, get response
    try: 
        summary = request.args.get('summary')
        #summary = "hello" #for debugging
        if(summary):
            
            #analyze summary, get JSON form response
            response = jsonify({"user_input" : summary, "text" : textRead}) #textRead needs to be sent as input to the user
            aiResponse = requests.post("https://aladnamedpat--sentence-comparison-response.modal.run/", data=data_to_send)
            aiGeneratedSummary = aiResponse["model_summary"]
            aiFeedback = aiResponse["model_response"]
            aiSemanticSimilarity = aiResponse["cosine_scores"]
            
            #store response in data
            doc = db.collection("responses").document()
            doc.set(response)
            id = doc.id
            
            #store response id with user(after getting active user with auth)
            
            #return response
            return aiGeneratedSummary, aiFeedback, aiSemanticSimilarity
        else:
            #reload site and present error msg
            return f"Please submit a summary"
    except Exception as e:
        return f"Error: {e}" 