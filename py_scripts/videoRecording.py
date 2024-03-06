import os
import json
import shutil
from datetime import datetime, timedelta
import subprocess
import sqlite3

conn = sqlite3.connect('mole.db')
cursor = conn.cursor()    

sql = '''select * from config; '''
cursor.execute(sql)
results = cursor.fetchall()

columns = [description[0] for description in cursor.description]
config_data = dict(zip(columns, results[0]))
conn.close()


url = config_data['url']
topic = config_data['topic']
output_folder_base = config_data['recording_path']
fps = config_data['fps']
width = config_data['width']
height = config_data['height']
duration = config_data['duration']

rtmp_url = "rtmp://localhost:1935/live"

role_back_days = 7

if not os.path.exists(output_folder_base):
    os.makedirs(output_folder_base)

try:
    while True:
        timestamp_now = datetime.now()
        seven_days_ago = timestamp_now - timedelta(days=role_back_days)
        base_folder_to_delete = os.path.join(output_folder_base)

        for folder_name in os.listdir(base_folder_to_delete):
            folder_path = os.path.join(base_folder_to_delete, folder_name)

            if os.path.isdir(folder_path):
                folder_date = datetime.strptime(folder_name, "%Y-%m-%d")

                if folder_date <= seven_days_ago:
                    print(f"Deleting folder from 7 days ago: {folder_path}")
                    shutil.rmtree(folder_path)

        timestamp_now = datetime.now()
        date_folder = timestamp_now.strftime("%Y-%m-%d")
        output_folder = os.path.join(output_folder_base, date_folder)

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        timestamp = timestamp_now.strftime("%Y-%m-%d_%H-%M-%S")
        output_filename = os.path.join(output_folder, f"video_{timestamp}.mp4")

        ffmpeg_cmd = (
            f"ffmpeg -i {rtmp_url} -t {duration} -r {fps} "
            f"-vf scale={width}:{height} -c:a copy -c:v libx264 -preset ultrafast {output_filename}"
        )

        subprocess.run(ffmpeg_cmd, shell=True)

except KeyboardInterrupt:
    print("Recording interrupted by user.")
