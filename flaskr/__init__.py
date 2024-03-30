import os
import json
from flask import Flask, request, jsonify, render_template
import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials
from firebase_admin import auth
import requests

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
    
@app.route("/register") 
def register_email_password():
    email = "test@gmail.com" #request.args.get('email')
    password = "testpassword"#request.args.get('email')
    
    try:
        user = auth.create_user(email = email, password = password)
        
        userInfo = {"email": email, "password": password, "responses": [], "goal": ""} #etc
        
        userDoc = db.collection("users").document(user.uid)
        userDoc.set(userInfo);
        
        return "User successfully created" 
    except Exception as e:
        return e.__str__()
    
    
@app.route("/signin") 
def sign_into_email():
    email = "test@gmail.com" #request.args.get('email')
    password = "testpassword"#request.args.get('email')
    
    try:
        user = auth.get_user_by_email(email = email)
        userInfo = db.collection("users").document(user.uid).get();
        realPW = userInfo.__getattribute__("password");
        if password == realPW:
            #sign into queried account, set active sessionID to user
            return(f"Successfully signed into {email}")
        else:
            return("incorrect password")
        
    except Exception as e:
        return e.__str__()
    

@app.route('/paragraph')
def get_paragraph():
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
        textReadID = request.args.get('textReadID')
        #summary = "hello" #for debugging
        if(summary):
            doc = db.collection("paragraphs").document(f"{textReadID}").get()
            textRead = doc.to_dict()["text"]
            #analyze summary, get JSON form response
            response = jsonify({"user_input" : summary, "text" : textRead}) #textRead needs to be sent as input to the user
            aiResponse = requests.post("https://aladnamedpat--sentence-comparison-response.modal.run/", data=response)
            aiGeneratedSummary = aiResponse["model_summary"]
            aiFeedback = aiResponse["model_response"]
            aiSemanticSimilarity = aiResponse["cosine_scores"]
            
            #store response in data
            doc = db.collection("responses").document()
            doc.set(aiResponse)
            id = doc.id
            
            #store response id with user(after getting active user with auth)
            
            #model summary : the summary that the model generated,
            #model_response : the feedback that the model provides, 
            #semantic similarity : the feedback that the model provides

            #return response
            return aiResponse 
        else:
            #reload site and present error msg
            return f"Please submit a summary"
    except Exception as e:
        return f"Error: {e}" 