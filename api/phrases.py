import json
import random

phrases = [
    "Hello world!",
    "Typing is fun.",
    "Practice makes perfect.",
    "Keep going!",
    "I love learning new things.",
    "Small steps every day.",
    "Focus and type fast!"
]

def handler(request):
    phrase = random.choice(phrases)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"phrase": phrase})
    }