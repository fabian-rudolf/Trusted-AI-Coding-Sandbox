import yaml
import requests
import os
import logging
from urllib.parse import parse_qs
from typing import Dict, List
from flask import Flask, request, render_template, jsonify, session
from code_tokenizer_ast import tokenize, detokenize

# Configure logging
logs_dir = "logs"
os.makedirs(logs_dir, exist_ok=True)

# Flask Application
def load_config():
    try:
        with open('config.yaml', 'r') as config_file:
            return yaml.safe_load(config_file)
    except (FileNotFoundError, yaml.YAMLError) as e:
        logging.error(f"Error loading configuration: {e}")
        return None

def setup_logging():
    config = load_config()
    if config:
        logs_dir = "logs"
        os.makedirs(logs_dir, exist_ok=True)
        logging.basicConfig(filename=os.path.join(logs_dir, f"{config.get('INSTANCE_NAME')}.log"), level=logging.INFO)
setup_logging()

import requests
import logging
from typing import Dict, List

def send_openai_chat_completion(api_key: str, messages: List[Dict[str, str]]) -> Dict:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": messages
    }
    logging.info(f"{url=}, {headers=}, {data=}")
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        logging.error(f"Error in sending request to OpenAI: {e}")
        return {}
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return {}


# Flask Application
app = Flask(__name__)
app.secret_key = load_config().get('FLASK_APP_SECRET_KEY')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        form_data = request.get_json()
        confirm = form_data.get('confirm', False)
        code_message = form_data.get('code')
        instruction_message = form_data.get('instruction')

        if not confirm:
            # Anonymize the code without sending to OpenAI
            if code_message is None:
                return jsonify(error="Unable to parse the provided empty code."), 400

            deanonymize_mapping, anonymized_code = tokenize(code_message)

            # Store for later use
            session['anonymized_code'] = anonymized_code
            session['deanonymize_mapping'] = deanonymize_mapping
            session['instruction_message'] = instruction_message
            return jsonify(anonymized_code=anonymized_code, deanonymize_mapping=str(deanonymize_mapping), instruction_message=str(instruction_message))

        elif confirm:
            anonymized_code = session['anonymized_code']
            logging.info(f"{anonymized_code=}")
            messages = [
                {'role': 'system', 'content':  load_config().get('SYSTEM_PROMPT')},
                {'role': 'user', 'content': instruction_message},
                {'role': 'user', 'content': f"Apply to code: ```{anonymized_code}```"},
            ]
            detokenization_dict = session.get('deanonymize_mapping')
            api_key = load_config().get('OPENAI_API_KEY')
            if api_key and messages:
                logging.info(f"{request=}")
                response = send_openai_chat_completion(api_key, messages)
                logging.info(f"{response=}")
                if 'choices' in response:
                    anonymized_response = response['choices'][0]['message']['content']
                    detokenized_response = detokenize(detokenization_dict=detokenization_dict, anonymized_code=anonymized_response)
                    return jsonify(anonymized_response=anonymized_response, detokenized_response=detokenized_response)
                else:
                    return jsonify(error="Unexpected response from OpenAI API."), 500
            else:
                return jsonify(error="Unable to load API key from the environment variables."), 500
    
    elif request.method == 'GET':
        default_code = """
def add(secret_name, other_secret):
    return secret_name + other_secret
    """
        default_instruction = load_config().get('TASK_PROMPT')

        return render_template('index.html', code=default_code, instruction=default_instruction)

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=8080)