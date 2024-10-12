import requests
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
from datetime import datetime
import json


def encrypt_password(plaintext, key, iv):
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    padded_plaintext = pad(plaintext.encode('utf-8'), AES.block_size)
    encrypted_bytes = cipher.encrypt(padded_plaintext)
    encrypted_base64 = base64.b64encode(encrypted_bytes).decode('utf-8')
    return encrypted_base64

def fetch_attendance(student_id, password):
    login_url = "https://webprosindia.com/vignanit/default.aspx"
    session = requests.Session()

    login_page = session.get(login_url)
    soup = BeautifulSoup(login_page.text, "html.parser")

    viewstate = soup.find("input", {"name": "__VIEWSTATE"})["value"]
    viewstate_generator = soup.find("input", {"name": "__VIEWSTATEGENERATOR"})["value"]
    event_validation = soup.find("input", {"name": "__EVENTVALIDATION"})["value"]

    # Encrypt the password (like in encryptJSText function in JS)
    key = "8701661282118308"  # Same key as used in JS
    iv = "8701661282118308"   # Same IV as used in JS
    encrypted_password = encrypt_password(password, key, iv)

    data = {
        "__VIEWSTATE": viewstate,
        "__VIEWSTATEGENERATOR": viewstate_generator,
        "__EVENTVALIDATION": event_validation,
        "txtId2": student_id,
        "txtPwd2": password,
        "imgBtn2.x": "0",
        "imgBtn2.y": "0",
        "hdnpwd2": encrypted_password,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://webprosindia.com",
        "Referer": login_url,
        "User-Agent": "Mozilla/5.0",
    }

    response = session.post(login_url, headers=headers, data=data)
    cookies = session.cookies.get_dict()
    frm_auth = cookies.get("frmAuth")
    session_id = cookies.get("ASP.NET_SessionId")

    if not (frm_auth and session_id):
        return {"error": "Failed to retrieve login cookies"}

    attendance_url = "https://webprosindia.com/vignanit/Academics/studentacadamicregister.aspx"
    attendance_headers = {
        'cookie': f'ASP.NET_SessionId={session_id}; frmAuth={frm_auth}',
        'referer': 'https://webprosindia.com/vignanit/StudentMaster.aspx',
        'user-agent': 'Mozilla/5.0'
    }

    attendance_response = session.get(attendance_url, headers=attendance_headers, params={'scrid': 2})
    if attendance_response.status_code != 200:
        return {"error": "Failed to fetch attendance data"}

    soup = BeautifulSoup(attendance_response.text, "html.parser")
    attendance_table = soup.select_one('#tblReport table')

    data = []
    for row in attendance_table.find_all('tr'):
        row_data = [cell.text.strip() for cell in row.find_all('td')]
        data.append(row_data)

    if len(data) < 4:
        return {"error": "Failed to parse attendance data"}

    roll_number = data[3][1].replace('\u00a0', '')

    cleaned_data = [[cell.replace('\xa0', '') for cell in row] for row in data[7:]]

    today = datetime.today().strftime('%d/%m')
    attendance_summary = []
    attendance_posted = False
    subjectwise_summary = []

    for row in cleaned_data[1:]:
        subject_name = row[1]
        attended_held = row[-2]
        percentage = row[-1]


        if attended_held != '0/0':
            subjectwise_summary.append({
            "subject_name": subject_name,
            "attended_held": attended_held,
            "percentage": percentage
            })

        if today in cleaned_data[0]:
            today_index = cleaned_data[0].index(today)
            attendance_today = row[today_index]
            
            if attendance_today != '-':
                attendance_posted = True
                attendance_summary.append({
                "subject": subject_name,
                "attendance_today": attendance_today
                })

    if not attendance_posted:
        attendance_summary.append({
            "message": f"Today {today} attendance is not posted."
        })

    total_attended = 0
    total_held = 0

    for row in cleaned_data[1:]:
        att_held = row[-2]
        attended, held = map(int, att_held.split('/'))
        total_attended += attended
        total_held += held

    total_percentage = round(total_attended / total_held * 100, 2)

    total_info = {
        "total_attended": total_attended,
        "total_held": total_held,
        "total_percentage": total_percentage
    }

    if total_percentage < 75:
        additional_hours = (0.75 * total_held - total_attended) / (1 - 0.75)
        total_info["additional_hours_needed"] = int(additional_hours)
    else:
        hours_can_skip = (total_attended - 0.75 * total_held) / 0.75
        total_info["hours_can_skip"] = int(hours_can_skip)

    result = {
        "roll_number": roll_number,
        "attendance_summary": attendance_summary,
        "subjectwise_summary": subjectwise_summary,
        "total_info": total_info
    }

    return json.dumps(result, indent=4)


student_id=""
student_pw=""

json_result = fetch_attendance(student_id, student_pw)
print(json_result)
