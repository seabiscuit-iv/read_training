from math import ceil
import os
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_bcrypt import Bcrypt
import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore import FieldFilter
from firebase_admin import credentials
from firebase_admin import auth
import requests
from datetime import datetime
from random import Random


__name__ = 'LearnApp' 

app = Flask(__name__, instance_relative_config=True)
CORS(app)
bcrypt = Bcrypt(app)
app.config.from_mapping(
    SECRET_KEY = 'absolute',
)
app.config.from_pyfile('config.py', silent=True)

cred = credentials.Certificate("../key.json")

default_app = firebase_admin.initialize_app(cred)
db = firestore.client()

try:
    os.makedirs(app.instance_path)
except OSError:
    pass
    
@app.route("/register", methods = ['POST']) 
def register_email_password():
    email = request.json.get('email')
    password = request.json.get('password')
    
    if(not email or not password):
        jsonify('Please fill out all fields', 400)
        
    user = auth.create_user(email = email, password = password)
    
    password = bcrypt.generate_password_hash(password=password)
    userInfo = {"email": email, "password": password, "responses": [], "goal": 0} #etc
    
    userDoc = db.collection("users").document(user.uid)
    userDoc.set(userInfo)
    print(userDoc.get().to_dict())
    return jsonify({"email": userDoc.get().to_dict()["email"]})
    
    
@app.route("/signin", methods = ['POST']) 
def sign_into_email():
    email = request.json.get('email', None)
    password = request.json.get('password', None)
    
    if(not email or not password):
        return jsonify('Please fill out all fields', 400)


    user = auth.get_user_by_email(email = email)
    userInfo = db.collection("users").document(user.uid).get()
    realPW = userInfo.get('password')
    if bcrypt.check_password_hash(realPW, password):
        #sign into queried account, set active sessionID to user
        sessionID = user.uid
        return {'sessionID' :sessionID}
    else:
        return jsonify("incorrect password")
    
    return jsonify(e.__str__())


@app.route('/generate_paragraph', methods = ['GET'])
def get_paragraph():
    #given a paragraph id, probably random, making sure it isn't one the user hasn't read
    #return a paragraph JSON based on what we expect
    docs = db.collection("paragraphs").get()
    c = len(docs)
    random = Random()
    i = random.randint(0, c-1)
    return docs[i].to_dict()

@app.route('/get_all_paragraphs', methods = ['GET'])
def get_all_paragraphs():
    #given a paragraph id, probably random, making sure it isn't one the user hasn't read
    #return a paragraph JSON based on what we expect
    docs = db.collection("paragraphs").get()
    paragraphs = []
    for doc in docs:
        id = doc.id
        dct = doc.to_dict()
        dct['id'] = id
        paragraphs.append(dct)
    return paragraphs
    
    

@app.route('/get_response', methods = ['POST'])
def get_response():
    id = request.json.get('id', None)
    userID = request.json.get('sessionID', None)

    if id:
        resp = db.collection("responses").document(f"{id}").get().to_dict()
        if resp['author'] == userID:
            return json.dumps(resp)
        else:
            return jsonify("Unauthorized Access")
    else:
        docs = db.collection("responses").where(filter=FieldFilter("author", "==", userID)).stream()
        resps = []
        for doc in docs:
            m = doc.to_dict()
            m['id'] = doc.id
            resps.append(doc.to_dict()) 
        return {'list':resps}


@app.route('/analyze', methods = ['POST'])
def analyze():
    params = request.json   
    #upon submission of text, get response
    summary = params['summary']
    textReadID = params['textReadID']
    readTime = datetime.now()
    weekday = datetime.weekday(readTime)
    readDuration = params['readDuration']
    userId = params['sessionID']
    
    if not userId: return jsonify("No active session")
    #summary = "hello" #for debugging
    if(summary):
        doc = db.collection("paragraphs").document(textReadID).get()
        id = doc.id
        textRead = doc.to_dict()["text"]
        title = doc.to_dict()["title"]
        #analyze summary, get JSON form response
        response = json.dumps({"user_input" : summary, "text" : textRead}) #textRead needs to be sent as input to the user
        aiResponse = requests.post("https://aladnamedpat--sentence-comparison-response.modal.run/", data=response).json()
        aiGeneratesdSummary = aiResponse["model_summary"]
        aiFeedback = aiResponse["model_response"]
        aiSemanticSimilarity = aiResponse["cosine_scores"]
        con = len(textRead)/len(summary)
        resp = {'aiResponse':aiResponse, 'id':id, 'title':title, 'author':userId, 'readTime':readTime, 'weekday':weekday, 'conciseness':con}

        #store response in data
        doc = db.collection("responses").document()
        doc.set(resp)
        id = doc.id
        
        #store response id with user(after getting active user with auth)
        users = db.collection("users").document(str(userId)).get().to_dict()
        users['responses'].append(id)
        doc = db.collection("users").document(str(userId)).set(users)
        
        #model summary : the summary that the model generated,
        #model_response : the feedback that the model provides, 
        #semantic similarity : the feedback that the model provides

        #return response
        return resp 
    else:
        #reload site and present error msg
        return jsonify(f"Please submit a summary")
    
    
@app.route ('/addText', methods = ['POST'])
def addText():
    params = request.json
    text = params['text']
    topic = params['topic']
    title = params['title']
    difficulty = requests.post("https://aladnamedpat--sentence-comparison-readability.modal.run/", json.dumps({'text':text})).json()['grade_level']
    tags = requests.post("https://aladnamedpat--sentence-comparison-find-topics.modal.run/", json.dumps({'text':text})).json()['Passage_topics']
    image = requests.post("https://andrewy8--stable-diffusion-xl-image-generation.modal.run", json.dumps({'text':text})).json()['url']
    length = ceil(len(str.split(text, " "))/250)
    skinned = {'title': title, 'difficulty':difficulty, 'text':text, 'length':length, 'image':image, 'topic':topic, 'tags':tags}
    db.collection("paragraphs").document().set(skinned)
    return jsonify(f"Text added: {title}")
    

@app.route('/globalMetrics', methods = ['POST'])
def globalMetrics():
    params = request.json
    userId = params['userId']
    count = 0
    conciseness = 0
    difficulty = 0
    accuracy = 0
    docs = db.collection("responses").where(filter=FieldFilter("author", "==", userId)).stream()
    for doc in docs:
        m = doc.to_dict()
        conciseness += m['conciseness']
        accuracy += m['aiResponse']['cosine_scores']
        m = db.collection("paragraphs").document(id).get().to_dict()
        difficulty += m['difficulty']
        count += 1
    
    conciseness /= count
    difficulty /= count
    accuracy /= count
    
    return jsonify({'conciseness':conciseness, 'difficulty':difficulty, 'accuracy':accuracy})
    
        
    