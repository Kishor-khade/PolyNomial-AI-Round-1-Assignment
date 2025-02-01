from flask import Flask, request, jsonify, render_template
import json
import os
from pymongo import MongoClient
import openai 
from datetime import datetime

app = Flask(__name__)

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client.faq_assistant
logs_collection = db.logs
knowledge_base_collection = db.knowledge_base


# OpenAI API Key (Set this in environment variables for security)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY


############################################################
# Knowledge Base Integration
def load_knowledge_base():
    try:
        # Fetch all documents from the MongoDB collection
        knowledge_base = list(knowledge_base_collection.find({}, {'_id': 0}))  # Exclude MongoDB's _id field
        # Check if the Database is present
        if not knowledge_base:
            print("Warning: Knowledge base is empty.")
        return knowledge_base
    except Exception as e:
        print(f"Error loading knowledge base: {e}")
        return []


############################################################
# Dynamic Query Handling:
def query_llm(user_query):
    """
    Queries an LLM (OpenAI GPT) to generate a response if MongoDB has no answer.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Change model as needed
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": user_query}],
            max_tokens=200
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error querying LLM: {e}")
        return "I'm sorry, but I couldn't generate an answer at this time."


############################################################
# Fallback Mechanism
def find_answer(user_query):
    knowledge_base = load_knowledge_base()
    # print(knowledge_base)
    for entry in knowledge_base:
        # print(entry["question"].lower())
        if user_query.lower() in entry["question"].lower():
            return entry["answer"]
    # If the query is not found in MongoDB then redirect to LLM
    return query_llm(user_query)
    # return "I can't able to find any answers through the DB"


############################################################
# Interaction Logging
def log_interaction(user_query, response):
    logs_collection.insert_one({"question": user_query, "answer": response, 'time':datetime.now()})


############################################################
## Flask Application Features
############################################################
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    user_query = data.get("query", "")
    print(user_query)
    answer = find_answer(user_query)
    # print(answer)
    log_interaction(user_query, answer)
    return jsonify({"response": answer})

# Upload some question & answer to DB
@app.route('/admin/upload', methods=['POST'])
def upload_knowledge():
    data = request.json
    question = data.get("question", "").strip()
    answer = data.get("answer", "").strip()

    if not question or not answer:
        return jsonify({"error": "Both 'question' and 'answer' fields are required."}), 400

    knowledge_base_collection.insert_one({"question": question, "answer": answer})
    return jsonify({"message": "Knowledge base updated successfully."})

# View the logs
@app.route('/admin/logs', methods=['GET'])
def get_logs():
    logs = list(logs_collection.find({}, {"_id": 0}))
    return jsonify(logs)

# View the DataBase 
@app.route('/admin/view_db', methods=['POST'])
def view_db():
    db = list(knowledge_base_collection.find({},{"_id":0}))
    return jsonify(db)


if __name__ == '__main__':
    app.run(debug=True)
