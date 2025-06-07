from supabase import create_client, Client
import datetime

url = "https://jtqxscwmjjaandwujsxq.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp0cXhzY3dtamphYW5kd3Vqc3hxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkxNDM2MDUsImV4cCI6MjA2NDcxOTYwNX0.OlugtCsxjpHsU6EWjNcJsETj852TDZ0ykQVWFcS9lfo"

supabase: Client = create_client(url, key)

data = {
    "596322": {
        "name": "Yago França",
        "major": "IA",
        "starting_year": 2020,
        "total_attendance": 7,
        "standing": "G",
        "year": 2,
        "last_attendance_time": "2022-12-11 00:54:34"
    }
}

for student_id, info in data.items():
    dt = datetime.datetime.strptime(info["last_attendance_time"], "%Y-%m-%d %H:%M:%S")
    supabase.table("FaceAttendenceRealTime").upsert({
        "id": student_id,
        **info,
        "last_attendance_time": dt.isoformat()
    }).execute()
