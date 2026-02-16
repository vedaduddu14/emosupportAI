from flask import Flask, send_from_directory
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import os, json

from agents import *

from langchain_core.messages import AIMessage, HumanMessage
from langchain.schema import messages_from_dict, messages_to_dict
from sentiment import analyze_sentiment_decision

import config as common

# from pymongo import MongoClient
# from flask_pymongo import PyMongo
# import redis

from dotenv import load_dotenv
from uuid import uuid4
import datetime
from flask_session import Session
import fcntl
import random
load_dotenv("project.env")

DB_NAME = "test"

# Debug: Verify OpenAI API key is loaded (shows only first/last few chars for security)
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"OpenAI API Key loaded: {api_key[:7]}...{api_key[-4:]}")
else:
    print("WARNING: OpenAI API Key not found!")

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = 'your_secret_key1'  # Required for session to work
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

### Redis
app.config['SESSION_TYPE'] = 'filesystem'   ### Default Flask approach
# app.config['SESSION_TYPE'] = 'redis'
# app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379')

Session(app)

# Data storage directory
DATA_DIR = "study_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Participant count management
COUNTS_FILE = "participant_counts.json"
MAX_PER_CONDITION_PER_TYPE = 4

def save_session_data(session_id, data_type, data):
    """Save session data to JSON file"""
    try:
        # Create participant directory
        participant_dir = os.path.join(DATA_DIR, session_id)
        if not os.path.exists(participant_dir):
            os.makedirs(participant_dir)

        # Save data with timestamp
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        data['session_id'] = session_id
        data['timestamp'] = timestamp

        # Save to specific file based on data type
        filename = f"{data_type}.json"
        filepath = os.path.join(participant_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Saved {data_type} data for session {session_id}")
        return True
    except Exception as e:
        print(f"Error saving {data_type} data: {str(e)}")
        return False

def save_ai_suggestion(session_id, client_id, turn_number, support_type, support_content, round_num=None):
    """Append AI agent suggestion to ai_suggestions file"""
    try:
        participant_dir = os.path.join(DATA_DIR, session_id)
        if not os.path.exists(participant_dir):
            os.makedirs(participant_dir)

        filepath = os.path.join(participant_dir, 'ai_suggestions.json')

        # Load existing suggestions or create new
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                suggestions = json.load(f)
        else:
            suggestions = []

        # Append new suggestion
        suggestion_data = {
            'session_id': session_id,
            'client_id': client_id,
            'round': round_num or 'unknown',
            'turn_number': turn_number,
            'support_type': support_type,
            'support_content': support_content,
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        suggestions.append(suggestion_data)

        # Save updated suggestions
        with open(filepath, 'w') as f:
            json.dump(suggestions, f, indent=2)

        return True
    except Exception as e:
        print(f"Error saving AI suggestion: {str(e)}")
        return False

def save_slider_feedback(session_id, client_id, turn_number, support_type, slider_value, round_num=None):
    """Append slider feedback to ai_feedback file"""
    try:
        participant_dir = os.path.join(DATA_DIR, session_id)
        if not os.path.exists(participant_dir):
            os.makedirs(participant_dir)

        filepath = os.path.join(participant_dir, 'ai_feedback.json')

        # Load existing feedback or create new
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                feedback = json.load(f)
        else:
            feedback = []

        # Append new feedback
        feedback_data = {
            'session_id': session_id,
            'client_id': client_id,
            'round': round_num or 'unknown',
            'turn_number': turn_number,
            'support_type': support_type,
            'slider_value': slider_value,
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        feedback.append(feedback_data)

        # Save updated feedback
        with open(filepath, 'w') as f:
            json.dump(feedback, f, indent=2)

        return True
    except Exception as e:
        print(f"Error saving slider feedback: {str(e)}")
        return False

def save_chat_message(session_id, client_id, turn_number, sender, receiver, message, round_num=None):
    """Append chat message to chat history file"""
    try:
        participant_dir = os.path.join(DATA_DIR, session_id)
        if not os.path.exists(participant_dir):
            os.makedirs(participant_dir)

        filepath = os.path.join(participant_dir, 'chat_history.json')

        # Load existing chat history or create new
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                chat_history = json.load(f)
        else:
            chat_history = []

        # Append new message
        message_data = {
            'session_id': session_id,
            'client_id': client_id,
            'round': round_num or 'unknown',
            'turn_number': turn_number,
            'sender': sender,
            'receiver': receiver,
            'message': message.strip(),
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        chat_history.append(message_data)

        # Save updated chat history
        with open(filepath, 'w') as f:
            json.dump(chat_history, f, indent=2)

        return True
    except Exception as e:
        print(f"Error saving chat message: {str(e)}")
        return False

def load_participant_counts():
    """Load participant counts from JSON with file locking"""
    try:
        with open(COUNTS_FILE, 'r') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
            counts = json.load(f)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock
            return counts
    except FileNotFoundError:
        # Initialize if file doesn't exist
        initial_counts = {
            "no_agents": {"Suppressor": 0, "NonSuppressor": 0},
            "emo_only": {"Suppressor": 0, "NonSuppressor": 0},
            "info_only": {"Suppressor": 0, "NonSuppressor": 0},
            "both_agents": {"Suppressor": 0, "NonSuppressor": 0}
        }
        save_participant_counts(initial_counts)
        return initial_counts

def save_participant_counts(counts):
    """Save participant counts to JSON with file locking"""
    with open(COUNTS_FILE, 'w') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
        json.dump(counts, f, indent=2)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock

def is_study_full():
    """
    Check if ALL 240 slots are filled (4 conditions × 30 suppressors × 2 types).
    Returns True if study is at full capacity.
    """
    counts = load_participant_counts()
    for condition, type_counts in counts.items():
        if type_counts["Suppressor"] < MAX_PER_CONDITION_PER_TYPE or \
           type_counts["NonSuppressor"] < MAX_PER_CONDITION_PER_TYPE:
            return False
    return True

def assign_condition(emotion_regulation_type):
    """
    Assign participant to a condition based on availability for their suppressor type.
    First determines which conditions have space for this type, then randomly picks one.
    Returns condition name or None if all conditions are full for this type.
    """
    counts = load_participant_counts()

    # Find available conditions (< 30 for this emotion regulation type)
    available_conditions = []
    for condition, type_counts in counts.items():
        if type_counts[emotion_regulation_type] < MAX_PER_CONDITION_PER_TYPE:
            available_conditions.append(condition)

    # If no conditions available, return None
    if not available_conditions:
        return None

    # Randomly pick from available conditions
    chosen_condition = random.choice(available_conditions)

    # Increment count and save
    counts[chosen_condition][emotion_regulation_type] += 1
    save_participant_counts(counts)

    return chosen_condition

### Mongo DB
# db = client[DB_NAME]
# print(client.list_databases())
# client = MongoClient('localhost', 27017)

# db = client.flask_db
# chat_post_task = db.chat_post_task
# chat_history_collection = db.chat_history
# chat_client_info = db.chat_client_info
# chat_in_task = db.chat_in_task
# chat_pre_task = db.chat_pre_task
# summative_writing = db.summative_writing
# summative_scoring = db.summative_scoring

sender_agent = None
chat_history = [
]

# clientQueue = common.randomQueue.copy()
clientQueue = []



sender_initial = agent_sender_fewshot_twitter_categorized()
sender_agent = mAgentCustomer()
# perspective / thoughts

# reframing
emo_agent = mAgentER()
# shoes
ep_agent = mAgentEP()
info_agent = mAgentInfo()
trouble_agent = mAgentTrouble()



@app.route('/')
def hello():
    return render_template('landing.html')

@app.route('/launch/')
def launch():
    # Password check temporarily disabled for testing
    # val_pwd = request.args.get('pwd')
    # if val_pwd == common.ADMIN_PWD:
    return redirect(url_for('start_chat', scenario='Airline'))
    # else:
    #     return "Access restricted to participants", 401

@app.route('/study-full/')
def study_full():
    """Display when study is at full capacity (all 240 slots filled)"""
    return render_template('study_full.html')

@app.route('/condition-full/<session_id>/')
def condition_full(session_id):
    """Display when participant's assigned condition is full for their suppressor type"""
    # Get info for display (optional - for logging/debugging)
    condition = "unknown"
    emotion_type = "unknown"
    if session_id in session:
        condition = session[session_id].get('assigned_condition', 'unknown')
        emotion_type = session[session_id].get('emotion_regulation_type', 'unknown')
    print(f"[REDIRECT] Condition full - session: {session_id}, condition: {condition}, type: {emotion_type}")
    return render_template('condition_full.html', session_id=session_id)

@app.route('/chat/<scenario>/')
def start_chat(scenario):
    # Password check temporarily disabled for testing
    # val_pwd = request.args.get('pwd')
    # if val_pwd != common.ADMIN_PWD:
    #     return "Access restricted to participants", 401

    # ===== CHECK IF STUDY IS FULL =====
    if is_study_full():
        return redirect(url_for('study_full'))

    # Condition will be assigned AFTER the pre-task survey determines suppressor type.
    # For now, create queue with a placeholder for Round 2 (flags will be updated later).
    full_queue = common.get_study_queue(scenario)

    session_id = str(uuid4())   ### unique to each user/participant/representative
    current_client = full_queue[0]  # Round 1 client (don't pop yet)
    session[session_id] = {}
    session[session_id]['current_client'] = current_client
    session[session_id]['scenario'] = scenario  # Store scenario for later use
    session[session_id]['full_queue'] = full_queue  # Store FULL queue with both clients
    session[session_id]['client_queue'] = [full_queue[1]]  # Queue shows Round 2 client waiting
    session[session_id]['current_round'] = 1  # Start with Round 1

    client = current_client  # For building clientParam below

    clientParam = f"?name={client['name']}&domain={client['domain']}&category={client['category']}&grateful={client['grateful']}&ranting={client['ranting']}&expression={client['expression']}&civil={client['civil']}&info={client['info']}&emo={client['emo']}"

    return redirect(url_for('getPreSurvey', session_id=session_id) + clientParam)

@app.route('/summative/phase1/get-tsv/')
def get_tsv():
    return send_from_directory('', 'phase1_scenarios.tsv')

# End-point for summative survey
@app.route('/summative/phase1/writing/')
def start_writing():
    val_prolific = request.args.get('PROLIFIC_PID')
    session[val_prolific] = 0
    return render_template('summative_survey.html')

@app.route('/store-summative-writing/<prolific_id>/', methods=['POST'])
def store_summative_writing(prolific_id):
    if prolific_id not in session:
        return jsonify({"message": "Invalid session or session expired"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"message": "No data received"}), 400

    data['prolific_id'] = prolific_id
    data['timestamp'] = datetime.datetime.now(datetime.timezone.utc)

    try:
        # result = summative_writing.insert_one(data)
        # if result.inserted_id:
        #     session[prolific_id] += 1
        #     return jsonify({"message": "Survey data saved successfully", "id": str(result.inserted_id)}), 200
        if True:
            return jsonify({"message": "Survey data received (no storage)"}), 200
        else:
            return jsonify({"message": "Failed to save data"}), 500
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/summative/phase1/complete/<prolific_id>/', methods=['GET'])
def complete_summative_writing(prolific_id):
    completion_count = session[prolific_id]
    if prolific_id not in session or completion_count < 6:
        return jsonify({"message": "Invalid session or session expired"}), 400

    redirect_url = "https://app.prolific.co/submissions/complete?cc=C19F0ZME"
    return jsonify({"url": redirect_url})

@app.route('/summative/phase2/get-tsv/<filetype>/')
def get_tsv2(filetype):
    if filetype == 'scenarios':
        return send_from_directory('', 'phase1_scenarios.tsv')
    elif filetype == 'ai_msgs':
        # Read TSV file and remove newline in the "coworker_empathetic_msg" column


        return send_from_directory('', 'empathetic_msgs_ai_v2.tsv')
    elif filetype == 'human_msgs':
        return send_from_directory('', 'empathetic_msg_human.tsv')
@app.route('/summative/phase2/writing/')
def start_scoring():
    val_prolific = request.args.get('PROLIFIC_PID')
    session[val_prolific] = 0
    return render_template('summative_survey_p2.html')

@app.route('/store-summative-scoring/<prolific_id>/', methods=['POST'])
def store_summative_scoring(prolific_id):
    if prolific_id not in session:
        return jsonify({"message": "Invalid session or session expired"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"message": "No data received"}), 400

    data['prolific_id'] = prolific_id
    data['timestamp'] = datetime.datetime.now(datetime.timezone.utc)

    try:
        # result = summative_scoring.insert_one(data)
        # if result.inserted_id:
        #     session[prolific_id] += 1
        #     return jsonify({"message": "Survey data saved successfully", "id": str(result.inserted_id)}), 200
        if True:
            return jsonify({"message": "Survey data received (no storage)"}), 200
        else:
            return jsonify({"message": "Failed to save data"}), 500
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/summative/phase2/complete/<prolific_id>/', methods=['GET'])
def complete_summative_scoring(prolific_id):
    completion_count = session[prolific_id]
    if prolific_id not in session or completion_count < 10:
        return jsonify({"message": "Invalid session or session expired"}), 400

    redirect_url = "https://app.prolific.co/submissions/complete?cc=C19F0ZME"
    return jsonify({"url": redirect_url})


# End-point to test the pre-survey HTML
@app.route('/pre-task-survey/<session_id>/')
def getPreSurvey(session_id):
    if session_id not in session:
        return "Invalid session", 401
    return render_template('pre_task_survey.html', session_id=session_id)


@app.route('/store-pre-task-survey/<session_id>/', methods=['POST'])
def storePreSurvey(session_id):
    if session_id in session:

        data = request.get_json()
        clientParam = "?"+data['client_param']

        # Store emotion regulation type in session for later use
        emotion_regulation_type = data.get('emotion_regulation_type', 'NonSuppressor')
        supp_score = data.get('supp_score', 0)

        session[session_id]['emotion_regulation_type'] = emotion_regulation_type
        session[session_id]['supp_score'] = supp_score
        session[session_id]['pre_task_survey'] = data

        print(f"[DEBUG] Pre-task survey - Emotion Type: {emotion_regulation_type}, SuppScore: {supp_score}")

        # ===== ASSIGN CONDITION BASED ON SUPPRESSOR TYPE =====
        # Now that we know the participant's suppressor type, find conditions
        # that still have space for this type and randomly pick one.
        # TESTING: Force specific condition (uncomment one):
        # assigned_condition = "no_agents"
        # assigned_condition = "emo_only"
        # assigned_condition = "info_only"
        # assigned_condition = "both_agents"
        # PRODUCTION:
        assigned_condition = assign_condition(emotion_regulation_type)

        if assigned_condition is None:
            # No conditions have space for this suppressor type - redirect out
            print(f"[DEBUG] No conditions available for {emotion_regulation_type} - redirecting out")
            data['session_id'] = session_id
            data['timestamp'] = datetime.datetime.now(datetime.timezone.utc)
            data['redirected_out'] = True
            data['redirect_reason'] = f"No conditions available for {emotion_regulation_type}"
            save_session_data(session_id, 'pre_task_survey', data)
            return redirect(url_for('condition_full', session_id=session_id))

        print(f"[DEBUG] Assigned condition: {assigned_condition} for {emotion_regulation_type}")

        # Store assigned condition in session
        session[session_id]['assigned_condition'] = assigned_condition
        session[session_id]['round2_condition'] = assigned_condition

        # Update Round 2 client's agent flags based on assigned condition
        # Use the SAME clients from the original queue (no re-shuffle!)
        full_queue = session[session_id]['full_queue']
        round2_client = full_queue[1]  # Get existing Round 2 client

        # Update only the info/emo flags based on condition
        condition_config = common.ROUND_2_CONDITIONS[assigned_condition]
        round2_client['info'] = condition_config['info']
        round2_client['emo'] = condition_config['emo']

        print(f"[DEBUG] Round 1 client: {full_queue[0]['name']}, info={full_queue[0]['info']}, emo={full_queue[0]['emo']}")
        print(f"[DEBUG] Round 2 client: {round2_client['name']}, info={round2_client['info']}, emo={round2_client['emo']}")

        # Update queue with the modified Round 2 client
        session[session_id]['client_queue'] = [round2_client]
        print(f"[DEBUG] Updated Round 2 client flags: {round2_client['name']}, info={round2_client['info']}, emo={round2_client['emo']}")

        for k in data:  # Convert string values into appropriate types
            if k not in ["client_param", "emotion_regulation_type"]:
                if k == "supp_score":
                    data[k] = float(data[k])
                else:
                    data[k] = int(data[k])

        if not data:
            return jsonify({"message": "No data received"}), 400

        data['session_id'] = session_id
        data['timestamp'] = datetime.datetime.now(datetime.timezone.utc)
        data['assigned_condition'] = assigned_condition

        # Save pre-task survey data (after conversion and metadata addition)
        save_session_data(session_id, 'pre_task_survey', data)

        try:
            # result = chat_pre_task.insert_one(data)
            # if result.inserted_id:
            #     jsoninfo = {
            #         "message": "Survey data saved successfully",
            #         "id": str(result.inserted_id)
            #     }
            #     return redirect(url_for('index', session_id=session_id) + clientParam, 302, jsoninfo)
            if True:
                return redirect(url_for('index', session_id=session_id) + clientParam, 302)
            else:
                return jsonify({"message": "Failed to save data"}), 500
        except Exception as e:
            return jsonify({"message": str(e)}), 500
    else:
        return jsonify({"message": "Invalid session or session expired"}), 400


# Post-Round 1 Survey Routes
@app.route('/post-round1-survey/<session_id>/')
def getPostRound1Survey(session_id):
    if session_id not in session:
        return "Invalid session", 401
    return render_template('post_round1_survey.html', session_id=session_id)


@app.route('/store-post-round1-survey/<session_id>/', methods=['POST'])
def storePostRound1Survey(session_id):
    if session_id in session:
        data = request.get_json()

        # Convert string values to integers (except attention_check which is categorical)
        for k in data:
            if k != "attention_check":
                data[k] = int(data[k])

        if not data:
            return jsonify({"message": "No data received"}), 400

        data['session_id'] = session_id
        data['timestamp'] = datetime.datetime.now(datetime.timezone.utc)

        # Store in session for now
        session[session_id]['post_round1_survey'] = data

        # Save post-round-1 survey data
        save_session_data(session_id, 'post_round1_survey', data)

        try:
            # Get Round 2 client (already set up from pre-task survey)
            clientQueue = session[session_id].get('client_queue', [])
            print(f"[DEBUG] Post-round-1 survey submitted")
            print(f"[DEBUG] client_queue length: {len(clientQueue)}")
            print(f"[DEBUG] current_round BEFORE increment: {session[session_id].get('current_round', 'NOT SET')}")

            # CRITICAL: Increment to Round 2 before starting Round 2 chat
            session[session_id]['current_round'] = 2
            print(f"[DEBUG] current_round AFTER increment: {session[session_id].get('current_round')}")

            if len(clientQueue) > 0:
                client = clientQueue.pop(0)  # Pop the Round 2 client from queue
                print(f"[DEBUG] Round 2 client: {client['name']}, info={client['info']}, emo={client['emo']}, civil={client['civil']}")
            else:
                # Fallback: use current_client if queue is empty
                print(f"[DEBUG] WARNING: client_queue is empty, using fallback")
                client = session[session_id].get('current_client')
                if not client:
                    return jsonify({"message": "No Round 2 client found"}), 400

            # CRITICAL: Update current_client for Round 2
            session[session_id]['current_client'] = client
            session[session_id]['client_queue'] = clientQueue  # Update queue (now empty)
            print(f"[DEBUG] Updated current_client to: {client['name']}")
            print(f"[DEBUG] client_queue is now empty (length: {len(clientQueue)})")

            # Build parameters for Round 2 chat
            clientParam = f"?name={client['name']}&domain={client['domain']}&category={client['category']}&grateful={client['grateful']}&ranting={client['ranting']}&expression={client['expression']}&civil={client['civil']}&info={client['info']}&emo={client['emo']}"
            print(f"[DEBUG] Redirecting to Round 2 chat with: {clientParam}")
            return redirect(url_for('index', session_id=session_id) + clientParam, 302)

        except Exception as e:
            return jsonify({"message": str(e)}), 500
    else:
        return jsonify({"message": "Invalid session or session expired"}), 400


@app.route('/attention-check-failed/<session_id>/')
def attention_check_failed(session_id):
    """Show failed attention check page and log the failure"""
    print(f"[ATTENTION CHECK] Failed for session {session_id}")

    # Save attention check failure to participant data
    if session_id in session:
        participant_dir = os.path.join(DATA_DIR, session_id)
        if not os.path.exists(participant_dir):
            os.makedirs(participant_dir)

        failure_data = {
            'session_id': session_id,
            'failed_check': 'post_round1_attention_check',
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'reason': 'Incorrect answer to "What AI agents did you use?" question'
        }

        failure_file = os.path.join(participant_dir, 'attention_check_failed.json')
        with open(failure_file, 'w') as f:
            json.dump(failure_data, f, indent=2)
        print(f"[ATTENTION CHECK] Failure logged to {failure_file}")

    return render_template('attention_check_failed.html', session_id=session_id)


@app.route('/index/<session_id>')
def index(session_id):
    if session_id in session:
        current_client = session[session_id]['current_client']
        current_round = session[session_id].get('current_round', 1)
    else:
        current_client = 'Guest'
        current_round = 1

    print(f"[DEBUG] Loading chat page - Round: {current_round}, Client: {current_client}")
    return render_template('index_chat.html', session_id=session_id, current_client=current_client, current_round=current_round, common_strings=common.SUPPORT_TYPE_STRINGS)


@app.route('/get-reply/<session_id>/', methods=['GET','POST'])
def getReply(session_id):
    if session_id not in session:
        return "Invalid session", 401
    clientQueue = session[session_id]['client_queue']
    if request.method == 'GET':
        val_name = request.args.get('name')
        val_domain = request.args.get('domain')
        val_category = request.args.get('category')
        val_grateful = request.args.get('grateful')
        val_ranting = request.args.get('ranting')
        val_expression = request.args.get('expression')
        val_civil = request.args.get('civil')
        show_info = request.args.get('info')
        show_emo = request.args.get('emo')

        complaint_parameters = {
            "domain": val_domain,
            "category": val_category,
            "is_grateful": 'grateful' if val_grateful==1 else 'NOT grateful',
            "is_ranting": 'ranting' if val_ranting==1 else 'NOT ranting',
            "is_expression": 'expressive' if val_expression==1 else 'NOT expressive'
        }

        response = sender_initial.invoke(complaint_parameters)

        # Clean up any prefixes that AI might have added
        for prefix in ["Client:", "Customer:", "Representative:", "client:", "customer:", "representative:"]:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
                break

        client_id = str(uuid4())
        current_client = session[session_id]['current_client']
        session[session_id][client_id] = {"current_client": current_client, "domain": val_domain, "category": val_category, "civil": val_civil, "chat_history": []}
        session[session_id][client_id]["chat_history"] = messages_to_dict([AIMessage(content="Client: "+response)])
        

        turn_number = len(session[session_id][client_id]["chat_history"])
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        current_round = session[session_id].get('current_round', 1)

        # Save initial complaint message
        save_chat_message(session_id, client_id, turn_number, 'client', 'representative', response, current_round)

        # chat_client_info.insert_one({
        #     "session_id": session_id,
        #     "client_id": client_id,
        #     "client_name":val_name,
        #     "domain": val_domain,
        #     "category": val_category,
        #     "grateful": val_grateful,
        #     "ranting": val_ranting,
        #     "expression": val_expression,
        #     "civil": val_civil,
        #     "emo": show_emo,
        #     "timestamp": timestamp
        # })

        # Inserting first complaint message
        # chat_history_collection.insert_one({
        #     "session_id": session_id,
        #     "client_id": client_id,
        #     "turn_number": turn_number,
        #     "sender": "client",
        #     "receiver": "representative",
        #     "message": response.strip(),
        #     "timestamp": timestamp
        # })


    elif request.method == 'POST':
        prompt = request.json.get("prompt")
        client_id = request.json.get("client_id")
        show_info = request.json.get("show_info")
        show_emo = request.json.get("show_emo")

        retrieve_from_session = json.loads(json.dumps(session[session_id][client_id]["chat_history"]))
        chat_history = messages_from_dict(retrieve_from_session)

        # Count representative messages (HumanMessage objects in chat history)
        rep_message_count = sum(1 for msg in chat_history if isinstance(msg, HumanMessage))

        # Force FINISH after 12 representative turns
        if rep_message_count >= 12:
            response = "FINISH:999"
        else:
            result = sender_agent.invoke({"input": prompt, "chat_history": chat_history, "civil": session[session_id][client_id]["civil"]})
            response = result

        # Clean up any prefixes that AI might have added
        for prefix in ["Client:", "Customer:", "Representative:", "client:", "customer:", "representative:"]:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
                break

        chat_history.extend([HumanMessage(content="Representative: "+prompt), AIMessage(content="Client: "+response)])
        session[session_id][client_id]["chat_history"] = messages_to_dict(chat_history)

        turn_number = len(chat_history) // 2 + 1
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        current_round = session[session_id].get('current_round', 1)

        # Save representative message
        save_chat_message(session_id, client_id, turn_number - 1, 'representative', 'client', prompt, current_round)

        # Save client reply
        save_chat_message(session_id, client_id, turn_number, 'client', 'representative', response, current_round)

        # Insert representative response
        # chat_history_collection.insert_one({
        #     "session_id": session_id,
        #     "client_id": client_id,
        #     "turn_number": turn_number - 1,
        #     "sender": "representative",
        #     "receiver": "client",
        #     "message": prompt.strip(),
        #     "timestamp": timestamp
        # })

        # Insert client reply to the response
        # chat_history_collection.insert_one({
        #     "session_id": session_id,
        #     "client_id": client_id,
        #     "turn_number": turn_number,
        #     "sender": "client",
        #     "receiver": "representative",
        #     "message": response.strip(),
        #     "timestamp": timestamp
        # })

    return jsonify({
        "client": client_id,
        "message": response,
        "show_info": show_info,
        "show_emo": show_emo,
        "clientQueue": clientQueue

    })

@app.route('/update-clientQueue/<session_id>/')
def update_client_queue(session_id):
    if session_id not in session:
        return "Invalid session", 401

    # Check if we just finished Round 1 or Round 2
    current_round = session[session_id].get('current_round', 1)

    print(f"[DEBUG] update_client_queue called - current_round: {current_round}")

    if current_round == 1:
        # Redirect to post-round-1 survey (DON'T increment round yet - that happens after survey)
        print(f"[DEBUG] Round 1 completed, redirecting to post-round-1 survey (current_round stays at 1)")
        new_url = url_for('getPostRound1Survey', session_id=session_id)
        return jsonify({"url": new_url})

    # If Round 2 just completed, go to final post-task survey
    elif current_round == 2:
        print(f"[DEBUG] Round 2 completed, redirecting to post-task survey")
        new_url = url_for('getSurvey', session_id=session_id)
        return jsonify({"url": new_url})

    # Otherwise, there's an issue - shouldn't reach here
    else:
        print(f"[DEBUG] ERROR: Invalid round state - current_round: {current_round}")
        return jsonify({"message": "Invalid round state"}), 400

# End-point to test the survey HTML
@app.route('/post-task-survey/<session_id>/')
def getSurvey(session_id):
    if session_id not in session:
        return "Invalid session", 401
    return render_template('feedback.html', session_id=session_id)

@app.route('/store-survey/<session_id>/', methods=['POST'])
def storePostSurvey(session_id):
    if session_id in session:
        data = request.get_json()
        reverseLabels = ["support_effective", "support_helpful", "support_beneficial",
                         "support_adequate", "support_sensitive", "support_caring",
                         "support_understanding", "support_supportive"]
        for k in data:  # Convert string values into integers

            if k != "client_id":
                data[k] = int(data[k])

            if k in reverseLabels:
                data[k] = data[k] * (-1)
                
        if not data:
            return jsonify({"message": "No data received"}), 400

        data['session_id'] = session_id
        data['timestamp'] = datetime.datetime.now(datetime.timezone.utc)
        data['condition'] = session[session_id].get('round2_condition', 'unknown')
        data['emotion_regulation_type'] = session[session_id].get('emotion_regulation_type', 'unknown')
        data['supp_score'] = session[session_id].get('supp_score', 0)

        # Save post-task survey data
        save_session_data(session_id, 'post_task_survey', data)

        try:
            # result = chat_post_task.insert_one(data)
            # if result.inserted_id:
            #     return jsonify({"message": "Survey data saved successfully", "id": str(result.inserted_id)}), 200
            if True:
                return jsonify({"message": "Survey data saved successfully"}), 200
            else:
                return jsonify({"message": "Failed to save data"}), 500
        except Exception as e:
            return jsonify({"message": str(e)}), 500
    else:
        return jsonify({"message": "Invalid session or session expired"}), 400

# Demographics Survey Routes
@app.route('/demographics-survey/<session_id>/')
def getDemographicsSurvey(session_id):
    if session_id not in session:
        return "Invalid session", 401
    return render_template('demographics_survey.html', session_id=session_id)


@app.route('/store-demographics-survey/<session_id>/', methods=['POST'])
def storeDemographicsSurvey(session_id):
    if session_id in session:
        data = request.get_json()

        if not data:
            return jsonify({"message": "No data received"}), 400

        # Convert numeric fields to integers
        if 'genai_familiarity' in data:
            data['genai_familiarity'] = int(data['genai_familiarity'])
        if 'genai_attitude' in data:
            data['genai_attitude'] = int(data['genai_attitude'])

        data['session_id'] = session_id
        data['timestamp'] = datetime.datetime.now(datetime.timezone.utc)
        data['condition'] = session[session_id].get('round2_condition', 'unknown')
        data['emotion_regulation_type'] = session[session_id].get('emotion_regulation_type', 'unknown')

        # Save demographics survey data
        save_session_data(session_id, 'demographics_survey', data)

        try:
            return jsonify({
                "message": "Demographics survey saved successfully",
                "redirect_url": f"/complete/?session_id={session_id}"
            }), 200
        except Exception as e:
            return jsonify({"message": str(e)}), 500
    else:
        return jsonify({"message": "Invalid session or session expired"}), 400


@app.route('/store-trouble-feedback/<session_id>/',methods=['POST'])
def storeTroubleFeedback(session_id):
    if session_id in session:
        client_id = request.json.get("client_id")
        rating = int(request.json.get("rate"))  # 0-100 scale (no need to reverse)
        support_type = request.json.get("type")

        turn_number = len(session[session_id][client_id]["chat_history"])//2+1
        current_round = session[session_id].get('current_round', 1)

        # Save slider feedback to file
        save_slider_feedback(session_id, client_id, turn_number, support_type, rating, current_round)

        return jsonify({"message": "Trouble feedback received"}), 200
    return jsonify({"message": "Invalid session or session expired"}), 400
   
@app.route('/store-sentiment-feedback/<session_id>/',methods=['POST'])
def storeSentimentFeedback(session_id):
    if session_id in session:
        client_id = request.json.get("client_id")
        rating = int(request.json.get("rate"))  # 0-100 scale (no need to reverse)
        support_type = request.json.get("type")

        turn_number = len(session[session_id][client_id]["chat_history"])//2+1
        current_round = session[session_id].get('current_round', 1)

        # Save slider feedback to file
        save_slider_feedback(session_id, client_id, turn_number, support_type, rating, current_round)

        return jsonify({"message": "Sentiment feedback received"}), 200
    return jsonify({"message": "Invalid session or session expired"}), 400

@app.route('/store-emo-feedback/<session_id>/', methods=['POST'])
def storeEmoFeedback(session_id):
    if session_id in session:
        client_id = request.json.get("client_id")
        rating = int(request.json.get("rate"))  # 0-100 scale (no need to reverse)
        support_type = request.json.get("type")

        turn_number = len(session[session_id][client_id]["chat_history"]) // 2 + 1
        current_round = session[session_id].get('current_round', 1)

        # Save slider feedback to file
        save_slider_feedback(session_id, client_id, turn_number, support_type, rating, current_round)

        return jsonify({"message": "Emo feedback received"}), 200
    return jsonify({"message": "Invalid session or session expired"}), 400


@app.route('/store-mouse-tracking/<session_id>/', methods=['POST'])
def storeMouseTracking(session_id):
    """Store mouse tracking data (position, quadrants, agent hovers)"""
    if session_id in session:
        try:
            data = request.get_json()

            if not data:
                print(f"[Mouse Tracking] No data received for session {session_id}")
                return jsonify({"message": "No data received"}), 400

            print(f"[Mouse Tracking] Received data for session {session_id}:")
            print(f"  - Movements: {len(data.get('movements', []))}")
            print(f"  - Quadrant Events: {len(data.get('quadrantEvents', []))}")
            print(f"  - Agent Hovers: {len(data.get('agentHovers', []))}")
            print(f"  - Total Duration: {data.get('totalDuration', 0)}ms")

            # Add metadata
            data['session_id'] = session_id
            data['timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            data['round'] = session[session_id].get('current_round', 1)
            data['condition'] = session[session_id].get('round2_condition', 'unknown')

            # Store in session
            round_key = f"mouse_tracking_round_{data['round']}"
            session[session_id][round_key] = data

            # Save to participant directory
            participant_dir = os.path.join(DATA_DIR, session_id)
            if not os.path.exists(participant_dir):
                os.makedirs(participant_dir)

            tracking_file = os.path.join(participant_dir, f"mouse_tracking_round_{data['round']}.json")
            try:
                with open(tracking_file, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"[Mouse Tracking] Saved to {tracking_file}")
            except Exception as e:
                print(f"[Mouse Tracking] Error saving tracking file: {e}")

            return jsonify({"message": "Tracking data received", "movements": len(data.get('movements', [])), "quadrantEvents": len(data.get('quadrantEvents', [])), "agentHovers": len(data.get('agentHovers', []))}), 200

        except Exception as e:
            print(f"[Mouse Tracking] Error storing mouse tracking: {e}")
            return jsonify({"message": str(e)}), 500

    return jsonify({"message": "Invalid session or session expired"}), 400


@app.route('/get-emo-support/<session_id>/', methods=['POST'])
def getEmoSupport(session_id):
    if session_id in session:
        client_id = request.json.get("client_id")
        reply = request.json.get("client_reply")
        support_type = request.json.get("type")

        retrieve_from_session = json.loads(json.dumps(session[session_id][client_id]["chat_history"]))
        chat_history = messages_from_dict(retrieve_from_session)

        turn_number = len(chat_history) // 2 + 1
        timestamp = datetime.datetime.now(datetime.timezone.utc)

        if support_type=="TYPE_EMO_REFRAME":
            response_cw_emo = emo_agent.invoke({'complaint':reply, "chat_history": chat_history})
            thought = response_cw_emo['thought']
            reframe = response_cw_emo['reframe']
            # Thought
            # chat_in_task.insert_one({
            #     "session_id": session_id,
            #     "client_id": client_id,
            #     "turn_number": turn_number,
            #     "support_type": "TYPE_EMO_THOUGHT",
            #     "support_content": thought.strip(),
            #     "timestamp_arrival":timestamp
            # })
            # Reframe
            # chat_in_task.insert_one({
            #     "session_id": session_id,
            #     "client_id": client_id,
            #     "turn_number": turn_number,
            #     "support_type": "TYPE_EMO_REFRAME",
            #     "support_content": reframe.strip(),
            #     "timestamp_arrival": timestamp
            # })

            # Save AI suggestions to file
            current_round = session[session_id].get('current_round', 1)
            save_ai_suggestion(session_id, client_id, turn_number, "TYPE_EMO_THOUGHT", thought.strip(), current_round)
            save_ai_suggestion(session_id, client_id, turn_number, "TYPE_EMO_REFRAME", reframe.strip(), current_round)

            return jsonify({
                "message": {
                    'thought':thought,
                    'reframe': reframe
                }
            })
        elif support_type=="TYPE_EMO_SHOES":
            response_cw_emo = ep_agent.invoke({'complaint':reply, "chat_history": chat_history})
            response = response_cw_emo
            # chat_in_task.insert_one({
            #     "session_id": session_id,
            #     "client_id": client_id,
            #     "turn_number": turn_number,
            #     "support_type": "Put Yourself in the Client's Shoes",
            #     "support_content": response.strip(),
            #     "timestamp_arrival": timestamp
            # })

            # Save AI suggestion to file
            current_round = session[session_id].get('current_round', 1)
            save_ai_suggestion(session_id, client_id, turn_number, "TYPE_EMO_SHOES", response.strip(), current_round)

            return jsonify({
                "message": response
            })
        else:
            return jsonify({"error": "Invalid support_type"}), 400

    return jsonify({"error": "Invalid session_id"}), 400

@app.route('/sentiment/<session_id>/', methods=['POST'])
def sentiment(session_id):
    if session_id in session:
        client_id = request.json.get("client_id")
        reply = request.json.get("client_reply")
        turn_number = len(session[session_id][client_id]["chat_history"]) // 2 + 1

        # Perform sentiment analysis
        # sentiment_category = analyze_sentiment_transformer(reply)
        sentiment_category = analyze_sentiment_decision(reply)

        # Save AI suggestion to file
        current_round = session[session_id].get('current_round', 1)
        save_ai_suggestion(session_id, client_id, turn_number, "TYPE_SENTIMENT", sentiment_category, current_round)

        return jsonify({'message': sentiment_category})
    else:
        return jsonify({"error": "Invalid session_id"}), 400



@app.route('/get-info-support/<session_id>/', methods=['POST'])
def getInfoSupport(session_id):
    if session_id in session:
        client_id = request.json.get("client_id")
        reply = request.json.get("client_reply")

        retrieve_from_session = json.loads(json.dumps(session[session_id][client_id]["chat_history"]))
        chat_history = messages_from_dict(retrieve_from_session)

        response_cw_info = info_agent.invoke({'domain': session[session_id][client_id]["domain"],'message':reply, 'sender':'client', "chat_history": chat_history})

        turn_number = len(chat_history) // 2 + 1
        current_round = session[session_id].get('current_round', 1)

        # Save AI suggestion to file
        save_ai_suggestion(session_id, client_id, turn_number, "TYPE_INFO_CUE", response_cw_info, current_round)

        return jsonify({
            "message": response_cw_info
        })
    return jsonify({"message": "Invalid session or session expired"}), 400


@app.route('/get-trouble-support/<session_id>/', methods=['POST'])
def getTroubleSupport(session_id):
    if session_id in session:
        client_id = request.json.get("client_id")
        reply = request.json.get("client_reply")

        retrieve_from_session = json.loads(json.dumps(session[session_id][client_id]["chat_history"]))
        chat_history = messages_from_dict(retrieve_from_session)

        response_cw_trouble = trouble_agent.invoke({'domain': session[session_id][client_id]["domain"],'message':reply, 'sender':'client', "chat_history": chat_history})
        response = response_cw_trouble

        turn_number = len(chat_history) // 2 + 1
        current_round = session[session_id].get('current_round', 1)

        # Save AI suggestion to file
        save_ai_suggestion(session_id, client_id, turn_number, "TYPE_INFO_GUIDE", response, current_round)

        return jsonify({
            "message": response
        })
    return jsonify({"message": "Invalid session or session expired"}), 400

@app.route('/conversation_history/')
def conversation_history():
    session_id = request.args.get('session_id')
    if not session_id:
        return "Session ID is missing", 400
    return render_template('conversation_history.html', session_id=session_id)

@app.route('/complete/')
def complete():
    session_id = request.args.get('session_id')
    if not session_id:
        return "Session ID is missing", 400
    return render_template('complete.html', session_id=session_id)

@app.route('/history/<session_id>/<client_id>/')
def getClientHistory(session_id, client_id):
    # chat_history = list(chat_history_collection.find({"session_id": session_id, "client_id": client_id}, {"_id": 0}))
    chat_history = []
    return jsonify({"chat_history": chat_history})

@app.route('/history/<session_id>/')
def getClientList(session_id):
    # clients_info = list(chat_client_info.find({"session_id": session_id}, {"_id": 0, "client_name": 1, "client_id": 1, "category":1}))
    clients_info = []
    return jsonify({"chat_history": chat_history, "clients_info": clients_info})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8443, threaded=True)
#%%








