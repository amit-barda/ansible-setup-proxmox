import os
import random

from flask import Flask, jsonify

app = Flask(__name__)

WORD = None

def load_random_word():
    words_file = "/usr/share/dict/words"
    if os.path.exists(words_file):
        with open(words_file, "r") as f:
            words = [line.strip() for line in f if line.strip()]
        return random.choice(words)
    return "hello"

@app.route("/")
def get_word():
    return jsonify({"word": WORD, "hostname": os.environ.get("HOSTNAME", "unknown")})

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

WORD = load_random_word()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
