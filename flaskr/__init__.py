import os
import json
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials

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
        if(summary):
            #analyze summary, get JSON form response
            response = {"Text": "Feedback", "Reading time"}
            
            #store response in data
            
            #return response
            return 
        else:
            #reload site and present error msg
            return f"Please submit a summary"
    except Exception as e:
        return f"Error: {e}" 