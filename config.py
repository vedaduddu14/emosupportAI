'''
A single file for string literals that are being used across files.
This ensures that we only need to make changes in one location to reflect it across multiple scripts.
Reduces risk of errors when changing code or introducing new types.
'''
import random
import copy

ADMIN_PWD = "491062"

TYPE_EMO_THOUGHT = "You might be thinking"
TYPE_EMO_SHOES = "Put Yourself in the Client's Shoes"
TYPE_EMO_REFRAME = "Be Mindful of Your Emotions"
TYPE_SENTIMENT = "Client's Sentiment"
TYPE_INFO_CUE = "Response Suggestions"
TYPE_INFO_GUIDE = "Guidance for Complaint Resolution"

SUPPORT_TYPE_STRINGS = {
    "TYPE_EMO_THOUGHT" : TYPE_EMO_THOUGHT,
    "TYPE_EMO_SHOES" : TYPE_EMO_SHOES,
    "TYPE_EMO_REFRAME" : TYPE_EMO_REFRAME,
    "TYPE_SENTIMENT" : TYPE_SENTIMENT,
    "TYPE_INFO_CUE" : TYPE_INFO_CUE,
    "TYPE_INFO_GUIDE": TYPE_INFO_GUIDE
}

### Only for testing/debugging
randomQueue = [
    { "id": 1, "name": "Luis H", "domain": "Airline" , "grateful": 0, "ranting": 0, "expression":0, "civil": 0, "info": 1, "emo": 1},
    { "id": 2, "name": "Jamal K", "domain": "Hotel", "grateful": 1, "ranting": 0, "expression": 1, "civil": 1, "info": 1, "emo": 0},
    { "id": 3, "name": "Maria N", "domain": "Airline",  "grateful": 1, "ranting": 1, "expression": 1, "civil": 1, "info": 0, "emo": 1},
    { "id": 4, "name": "Elijah P", "domain": "Hotel" , "grateful": 0, "ranting": 1, "expression":0, "civil": 0, "info": 0, "emo": 0},
    { "id": 5, "name": "Anna Z", "domain": "Hotel" , "grateful": 0, "ranting": 1, "expression":0, "civil": 1, "info": 0, "emo": 1},
    { "id": 6, "name": "Samantha K", "domain": "Hotel" , "grateful": 0, "ranting": 1, "expression":0, "civil": 1, "info": 0, "emo": 1}
]

'''
For actual study scenario.
2 rounds per participant:
- Round 1: No agents (baseline)
- Round 2: One of 4 conditions (no agents, emo only, info only, both agents)
Client behavior: "grateful": 0, "ranting": 1, "expression": 1, "civil": 0
'''

# Round 1 is always the same (no agents)
ROUND_1 = { "id": 1, "grateful": 0, "ranting": 1, "expression": 1, "civil": 0, "info": 0, "emo": 0}

# Round 2 - Four possible conditions
ROUND_2_CONDITIONS = {
    "no_agents": { "id": 2, "grateful": 0, "ranting": 1, "expression": 1, "civil": 0, "info": 0, "emo": 0},
    "emo_only": { "id": 2, "grateful": 0, "ranting": 1, "expression": 1, "civil": 0, "info": 0, "emo": 1},
    "info_only": { "id": 2, "grateful": 0, "ranting": 1, "expression": 1, "civil": 0, "info": 1, "emo": 0},
    "both_agents": { "id": 2, "grateful": 0, "ranting": 1, "expression": 1, "civil": 0, "info": 1, "emo": 1}
}

# Default study queue (will be customized based on condition assignment)
studyQueue = [
    ROUND_1,
    ROUND_2_CONDITIONS["both_agents"]  # Default to both agents, will be overridden
]

complaintTypes = [
    "Service Quality",
    "Product Issues",
    "Pricing and Charges",
    "Policy",
    "Resolution"
]

def get_study_queue(scenario, round2_condition="both_agents"):
    """
    Create a 2-round study queue for the given scenario.

    Args:
        scenario: "Hotel" or "Airline"
        round2_condition: One of "no_agents", "emo_only", "info_only", "both_agents"

    Returns:
        List with 2 client configurations (Round 1 and Round 2)
    """
    names = [client['name'] for client in randomQueue]
    random.shuffle(names)
    random.shuffle(complaintTypes)

    # Create 2-round queue
    queue = [
        copy.deepcopy(ROUND_1),
        copy.deepcopy(ROUND_2_CONDITIONS[round2_condition])
    ]

    # Assign names, domains, categories, and avatars
    for client_id in range(2):
        client_name = names[client_id]
        complaint_type = complaintTypes[client_id]

        queue[client_id]['category'] = complaint_type
        queue[client_id]['name'] = client_name
        queue[client_id]['domain'] = scenario
        queue[client_id]['avatar'] = "https://avatar.iran.liara.run/username?username="+client_name.replace(' ','+')

    return queue
