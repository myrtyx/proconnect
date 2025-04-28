import uuid
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template

# ─── OpenAI Configuration ─────────────────────────────────────────────────────
OPENAI_API_KEY = "sk-proj- sike))"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

def call_openai_chat(messages, model="gpt-4"):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7
    }
    resp = requests.post(OPENAI_API_URL, headers=headers, json=payload)
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI API error: {resp.status_code} {resp.text}")
    return resp.json()["choices"][0]["message"]["content"].strip()

# ─── Bot 1: Extract Facts ─────────────────────────────────────────────────────
def bot1_extract_facts(user_input):
    messages = [
        {"role": "system", "content": (
            "You are a helpful assistant. "
            "Given free-form biography text, extract:\n"
            "- name: the person's name or null\n"
            "- age: integer or null\n"
            "- location: {city, country}\n"
            "- achievements: list of key achievements\n"
            "Return ONLY the JSON object."
        )},
        {"role": "user", "content": user_input}
    ]
    result = call_openai_chat(messages)
    return json.loads(result)

# ─── Bot 2: Categorize & Level Skills ─────────────────────────────────────────
def bot2_categorize(achievements):
    messages = [
        {"role": "system", "content": (
            "You are a helpful assistant. "
            "Given an array of achievements, identify skill categories and assign a level 1–5 each. "
            "Return JSON with:\n"
            "- categories: [\"skill1\",…]\n"
            "- category_levels: {\"skill1\": level, …}\n"
            "Return ONLY the JSON object."
        )},
        {"role": "user", "content": json.dumps({"achievements": achievements})}
    ]
    result = call_openai_chat(messages)
    return json.loads(result)

# ─── Bot 3: Generate Summary ──────────────────────────────────────────────────
def bot3_generate_summary(user_input, raw_facts):
    messages = [
        {"role": "system", "content": (
            "You are a helpful assistant. "
            "Write a 1–2 sentence summary of the profile based on bio and extracted facts. "
            "Return ONLY the summary."
        )},
        {"role": "user", "content": json.dumps({"text": user_input, "facts": raw_facts})}
    ]
    return call_openai_chat(messages)

# ─── Bot 4: Extract Languages ─────────────────────────────────────────────────
def bot4_extract_languages(user_input):
    messages = [
        {"role": "system", "content": (
            "You are a helpful assistant. "
            "Extract all languages mentioned in the biography text. "
            "Return a JSON array of names."
        )},
        {"role": "user", "content": user_input}
    ]
    result = call_openai_chat(messages)
    return json.loads(result)

# ─── Assemble Final Profile ──────────────────────────────────────────────────
def assemble_profile(data):
    return {
        "session_id": data["session_id"],
        "user_input": data["user_input"],
        "name": data["raw_facts"].get("name"),
        "age": data["raw_facts"].get("age"),
        "location": data["raw_facts"].get("location"),
        "summary": data.get("summary"),
        "categories": data.get("categories"),
        "category_levels": data.get("category_levels"),
        "achievements": data["raw_facts"].get("achievements"),
        "languages": data.get("languages"),
        "created_at": data["created_at"],
        "notes": None
    }

# ─── Flask App Setup ──────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="static", template_folder="templates")
pipeline_sessions = {}

@app.route('/')
def index():
    return render_template('index.html')  # Your existing index.html

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/generate_profile', methods=['POST'])
def generate_profile():
    req = request.get_json()
    user_input = req.get('user_input')
    if not user_input:
        return jsonify({"error": "No user_input provided"}), 400

    session_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat() + 'Z'
    pipeline_sessions[session_id] = {
        "session_id": session_id,
        "user_input": user_input,
        "created_at": created_at
    }

    try:
        raw = bot1_extract_facts(user_input)
        pipeline_sessions[session_id]['raw_facts'] = raw

        cat = bot2_categorize(raw.get('achievements', []))
        pipeline_sessions[session_id].update(cat)

        summary = bot3_generate_summary(user_input, raw)
        pipeline_sessions[session_id]['summary'] = summary

        langs = bot4_extract_languages(user_input)
        pipeline_sessions[session_id]['languages'] = langs

        final = assemble_profile(pipeline_sessions[session_id])
        pipeline_sessions[session_id]['final_profile'] = final
        return jsonify(final)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
