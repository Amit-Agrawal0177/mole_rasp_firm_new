import RPi.GPIO as GPIO
import time
import os
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import subprocess
import serial
import re
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

output_folder = config_data['movement_path']
mac = config_data['ameba_mac']

buffer_time = config_data['buffer_time']
width = config_data['width']
height = config_data['height']
#fps = config_data['fps']
fps = 5.0
chunk_duration = 60  

#rtmp_url = f'rtmp://{url}/live/{topic}'
rtmp_url = "rtmp://localhost:1935/live"
#rtmp_url = "rtsp://192.168.1.15"
upload_url = 'https://moleapi.9930i.com/s3/uploadFile'

input_pin = 17
output_pin = 27

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(input_pin, GPIO.IN)
GPIO.setup(output_pin, GPIO.OUT)

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

        
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

ip = find_ip_with_retry(mac)
allot_ip = ip[0]

try:
    #GPIO.output(output_pin, GPIO.HIGH)

    start_time = None
    recording = False
    out = None
    chunk_start_time = time.time()
    pir_time = None
    
    conn = sqlite3.connect('mole.db')
    cursor = conn.cursor()

    while True:        
        input_state = GPIO.input(input_pin)
        
        print(input_state, flush="True")
        sql = '''select * from stat where id = 1; '''
        cursor.execute(sql)
        results = cursor.fetchall()
        
        columns = [description[0] for description in cursor.description]
        json_data = dict(zip(columns, results[0]))
        #print(json_data, flush=True)
        
    
        if json_data["alert_mode"] == "1":
            GPIO.output(output_pin, input_state)

            if input_state == GPIO.HIGH:
                sql = f'''update stat set pir_status = "1" where id = 1;'''
                cursor.execute(sql)                        
                conn.commit() 
                    
                start_time = time.time()
                pir_time = time.time()

                if not recording:
                    print("Starting to record...", flush=True)
                    #publish_mqtt(f'R/{topic}', json.dumps({"status": "movement start"}))
                    recording = True
                    start_time = time.time()
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    output_filename = os.path.join(output_folder, f"video_{timestamp}.mp4")

                    ffmpeg_cmd = (
                        f"ffmpeg -i rtsp://{allot_ip}:555 -t {buffer_time} -r {fps} "
                        f"-vf scale={width}:{height} -c:a copy -c:v libx264 -preset ultrafast {output_filename}"
                    )

                    subprocess.run(ffmpeg_cmd, shell=True)
                    chunk_start_time = time.time()

            if input_state == GPIO.LOW:
                elapsed_time1 = time.time() - start_time
                if elapsed_time1 >= buffer_time:
                    GPIO.output(output_pin, GPIO.LOW)
                    sql = f'''update stat set pir_status = "0" where id = 1;'''
                    cursor.execute(sql)                        
                    conn.commit()

            if recording:
                elapsed_time = time.time() - start_time
                if elapsed_time >= buffer_time:
                    # sql = f'''update stat set pir_status = "0" where id = 1;'''
                    # cursor.execute(sql)                        
                    # conn.commit() 
                    print("Stopping recording...", flush=True)
                    #publish_mqtt(f'R/{topic}', json.dumps({"status": "movement stop"}))
                    recording = False
                    chunk_start_time = time.time()
        else:
            GPIO.output(output_pin, GPIO.LOW)

        current_time = time.time()
        time.sleep(2)

except KeyboardInterrupt:
    GPIO.cleanup()
    conn.close()
