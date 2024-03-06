import subprocess
import json
import os
import sqlite3

conn = sqlite3.connect('mole.db')
cursor = conn.cursor()    

sql = '''select * from config; '''
cursor.execute(sql)
results = cursor.fetchall()

columns = [description[0] for description in cursor.description]
config_data = dict(zip(columns, results[0]))
conn.close()

output_folder = config_data['recording_path']

if not os.path.exists(output_folder):
    os.makedirs(output_folder)
    
command = ["python3", "-m", "http.server", "3030"]

with subprocess.Popen(command, cwd=output_folder) as server_process:
    try:
        server_process.wait()

    except KeyboardInterrupt:
        pass
