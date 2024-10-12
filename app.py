from flask import Flask, request, jsonify
import json
from test import fetch_attendance

app = Flask(__name__)

@app.route('/attendance', methods=['GET'])
def get_attendance():
    student_id = request.args.get('student_id')
    password = request.args.get('password')
    
    if not student_id or not password:
        return jsonify({"error": "Missing student_id or password"}), 400

    attendance_data = fetch_attendance(student_id, password)
    return jsonify(json.loads(attendance_data))  # Convert JSON string to dict

if __name__ == '__main__':
    app.run()
