import os
import json
from flask import Flask, request, jsonify, render_template
from flask_bcrypt import Bcrypt
import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore import FieldFilter
from firebase_admin import credentials
from firebase_admin import auth
import requests
from cryptography.fernet import Fernet


__name__ = 'LearnApp' 

app = Flask(__name__, instance_relative_config=True)
bcrypt = Bcrypt(app)
app.config.from_mapping(
    SECRET_KEY = 'absolute',
)
app.config.from_pyfile('config.py', silent=True)

cred = credentials.Certificate("key.json")

default_app = firebase_admin.initialize_app(cred)
db = firestore.client()

with open('fernetkey.txt', 'r') as file:
    fernetKey = file.read().rstrip()
        
fernet = Fernet(fernetKey)

try:
    os.makedirs(app.instance_path)
except OSError:
    pass
    
@app.route("/register", methods = ['POST']) 
def register_email_password():
    email = request.json.get('email')
    password = request.json.get('password')
    
    if(not email or not password):
        return("Please fill out all fields")
    
    try:
        user = auth.create_user(email = email, password = password)
        
        password = bcrypt.generate_password_hash(password=password)
        userInfo = {"email": email, "password": password, "responses": [], "goal": 0} #etc
        
        userDoc = db.collection("users").document(user.uid)
        userDoc.set(userInfo);
        
        return json.dumps(userDoc.get().to_dict)
    except Exception as e:
        return e.__str__()
    
    
@app.route("/signin", methods = ['POST']) 
def sign_into_email():
    email = request.json.get('email', None)
    password = request.json.get('password', None)
    
    if(not email or not password):
        return("Please fill out all fields")
    
    
    try:
        user = auth.get_user_by_email(email = email)
        userInfo = db.collection("users").document(user.uid).get()
        realPW = userInfo.get('password')
        if bcrypt.check_password_hash(realPW, password):
            #sign into queried account, set active sessionID to user
            sessionID = fernet.encrypt(user.uid.encode())
            return {'sessionID' :sessionID}
        else:
            return("incorrect password")
        
    except Exception as e:
        return e.__str__()


@app.route('/generate_paragraph', methods = ['GET'])
def get_paragraph():
    #given a paragraph id, probably random, making sure it isn't one the user hasn't read
    #return a paragraph JSON based on what we expect
    id = 0
    try:
        doc = db.collection("paragraphs").document(f"{id}").get()
        return jsonify(doc.to_dict())
    except Exception as e:
        return f"Error: {e}"
    

@app.route('/get_response', methods = ['POST'])
def get_response():
    id = request.json.get('id', None)
    sessionID = request.json.get('sessionID', None)
    userID = fernet.decrypt(sessionID).decode();
    
    try:
        if id:
            resp = db.collection("responses").document(f"{id}").get().to_dict()
            if resp['author'] == userID:
                return jsonify(resp)
            else:
                return "Unauthorized Access"
        else:
            docs = db.collection("responses").where(filter=FieldFilter("author", "==", userID)).stream()
            resps = {}
            for doc in docs:
                resps[f'{doc.id}'] = doc.to_dict
            json_data = json.dumps(resps);
            return json_data
    except Exception as e:
        return f"Exception occured: {e}"



@app.route('/analyze', methods = ['POST'])
def analyze():
    params = request.json
    #upon submission of text, get response
    try:
        summary = params['summary']
        textReadID = params['textReadID']
        readTime = params['readTime']
        readDuration = params['readDuration']
        userId = params['userId']
        #summary = "hello" #for debugging
        if(summary):
            doc = db.collection("paragraphs").document(f"{textReadID}").get()
            textRead = doc.to_dict()["text"]
            #analyze summary, get JSON form response
            response = json.dumps({"user_input" : summary, "text" : textRead}) #textRead needs to be sent as input to the user
            aiResponse = requests.post("https://aladnamedpat--sentence-comparison-response.modal.run/", data=response).json()
            aiGeneratesdSummary = aiResponse["model_summary"]
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
    
    
@app.route ('/addText', methods = ['POST'])
def addText():
    params = request.json
    try:
        skinned = {'difficulty':params['difficulty'], 'text':params['text'], 'length':params['length'], 'image':params['image']}
        db.collection("paragraphs").document(params['title']).set(skinned)
        return f"Text added: {params['title']}"
    except Exception as e:
        return f"Error: {e}"
    