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
    return jsonify(json.loads(attendance_data))

@app.route('/compare', methods=['POST'])
def compare_attendance_vs():
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({"error": "Invalid input. Expecting a list of student credentials."}), 400
    
    students_data = []
    subject_points = {}
    
    for student in data:
        student_id = student.get('student_id')
        password = student.get('password')
        if not student_id or not password:
            students_data.append({
                "student_id": student_id,
                "error": "Missing student_id or password"
            })
            continue

        attendance_data = fetch_attendance(student_id, password)
        attendance_data = json.loads(attendance_data)
        
        if "total_info" not in attendance_data:
            students_data.append({
                "student_id": student_id,
                "error": "Failed to fetch attendance data"
            })
            continue

        total_attended = attendance_data["total_info"]["total_attended"]
        total_held = attendance_data["total_info"]["total_held"]
        total_percentage = attendance_data["total_info"]["total_percentage"]
        additional_hours_needed = attendance_data["total_info"].get("additional_hours_needed", 0)
        hours_can_skip = attendance_data["total_info"].get("hours_can_skip", 0)

        subject_summary = attendance_data.get("subjectwise_summary", [])
        for subject in subject_summary:
            subject_name = subject["subject_name"]
            percentage = float(subject["percentage"].replace("%", ""))

            if subject_name not in subject_points:
                subject_points[subject_name] = []

            subject_points[subject_name].append({
                "student_id": student_id,
                "percentage": percentage
            })

        students_data.append({
            "student_id": student_id,
            "total_attended": total_attended,
            "total_held": total_held,
            "total_percentage": total_percentage,
            "hours_status": hours_can_skip if hours_can_skip > 0 else -additional_hours_needed
        })

    subject_points_summary = {}
    for subject, scores in subject_points.items():
        max_percentage = max(s["percentage"] for s in scores)
        top_students = [s["student_id"] for s in scores if s["percentage"] == max_percentage]

        for student in students_data:
            if student["student_id"] in top_students:
                student.setdefault("subject_points", 0)
                student["subject_points"] += 1

        subject_points_summary[subject] = {
            "max_percentage": max_percentage,
            "top_students": top_students
        }

    comparison_summary = {
        "students": students_data,
        "subject_points_summary": subject_points_summary
    }

    return jsonify(comparison_summary)


@app.route('/skip', methods=['GET'])
def calculate_attendance_after_skip():
    student_id = request.args.get('student_id')
    password = request.args.get('password')
    skip_hours = request.args.get('hours', type=int)

    if not student_id or not password or skip_hours is None:
        return jsonify({"error": "Missing student_id, password, or hours"}), 400

    attendance_data = fetch_attendance(student_id, password)
    attendance_dict = json.loads(attendance_data)

    total_attended = attendance_dict['total_info']['total_attended']
    total_held = attendance_dict['total_info']['total_held']

    # Adjust total held after skipping the given hours
    new_total_held = total_held + skip_hours
    new_percentage = round((total_attended / new_total_held) * 100, 2)

    # Determine status after skipping
    if new_percentage >= 75:
        status = "safe to skip"
        hours_can_skip = int((total_attended - 0.75 * new_total_held) / 0.75)
    else:
        status = "needs to attend more"
        additional_hours_needed = int((0.75 * new_total_held - total_attended) / (1 - 0.75))

    result = {
        "original_attendance_percentage": attendance_dict['total_info']['total_percentage'],
        "new_attendance_percentage": new_percentage,
        "status": status,
    }

    # Add additional info based on status
    if status == "safe to skip":
        result["hours_can_skip_after"] = hours_can_skip
    else:
        result["additional_hours_needed_after"] = additional_hours_needed

    return jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  
