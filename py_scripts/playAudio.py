import os
import json
import time
import subprocess
import re
import signal
from pydub import AudioSegment
import sqlite3

conn = sqlite3.connect('mole.db')
cursor = conn.cursor()    

sql = '''select * from config; '''
cursor.execute(sql)
results = cursor.fetchall()

columns = [description[0] for description in cursor.description]
config_data = dict(zip(columns, results[0]))
conn.close()

mac = config_data['ameba_mac']
url = config_data['url']
topic = config_data['topic']
rtmp_url = f'rtmp://{url}/live/{topic}'
allot_ip = ""
        
def get_ips_for_mac(target_mac, arp_output):
    pattern = re.compile(r"(\S+) \((\d+\.\d+\.\d+\.\d+)\) at (\S+)")
    ips = []

    for line in arp_output.splitlines():
        match = pattern.search(line)
        if match:
            _, ip, mac = match.groups()
            if mac.lower() == target_mac.lower():
                ips.append(ip)

    return ips

def find_ip_with_retry(target_mac):
    max_retries = 5
    retries = 0

    while True:
        result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
        if result.returncode == 0:
            arp_output = result.stdout
            ips = get_ips_for_mac(target_mac, arp_output)

            if ips:
                print(f"The IP addresses for MAC address {target_mac} are: {', '.join(ips)}", flush=True)
                return ips

        retries += 1
        time.sleep(5)  # Wait for 5 seconds before retrying

    print(f"Unable to find IP addresses for MAC address {target_mac} after {max_retries} retries.", flush=True)
    return []


def play_via_file():
	temp_audio_file = "audio.mp3"
    
	cmd = f"ffmpeg -re -i {temp_audio_file} -vn -ac 1 -ar 8000 -b:a 128k -c:a pcm_mulaw -f rtp rtp://{ip}:5004"
	print(f'{cmd}', flush=True)
	
	process = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
	process.wait()  # Wait for the subprocess to finish
	os.remove(temp_audio_file)

ip = find_ip_with_retry(mac)
allot_ip = ip[0]
   

process = None
last_message_time = time.time()


conn = sqlite3.connect('mole.db')
cursor = conn.cursor()

while True:
    sql = '''select * from stat order by id; '''
    cursor.execute(sql)
    results = cursor.fetchall()
    
    columns = [description[0] for description in cursor.description]
    json_data = dict(zip(columns, results[0]))
    #print(json_data, flush=True)
        
    time.sleep(1)
    
    if json_data["audio_flag"] == "1":
        print(f"Start playing audio", flush=True)
        play_via_file()
        
        sql = '''update stat set audio_flag = "0" where id = 1;'''
        cursor.execute(sql)
        conn.commit()

conn.close()
