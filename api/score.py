import json

def handler(request):
    try:
        data = request.get_json()
        correct = int(data.get("correct", 0))
        time_used = float(data.get("time", 1))
        wpm = round(correct / time_used * 60, 2)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"wpm": wpm})
        }
    except Exception as e:
        return {"statusCode": 400, "body": f"Error: {e}"}