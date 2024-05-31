import os
import json
import time
import subprocess
import re
import signal
import sqlite3
import RPi.GPIO as GPIO

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

output_pin = 27

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(output_pin, GPIO.OUT)
        
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

def start_streaming():
    global process
    
    if process is None or process.poll() is not None:                            
        command = 'ffmpeg -i rtsp://' + allot_ip + ' -c:v copy -c:a aac -strict experimental -f flv ' + rtmp_url
        process = subprocess.Popen(command, shell=True, preexec_fn=os.setsid)
        print(f"Starting streaming: {process.pid} {command}", flush=True)        

def stop_streaming(json_data):
    global process
    if process is not None and process.poll() is None:
        print(f"Stopping streaming.{process.pid}", flush=True)
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait()
        process = None
        if json_data["alert_mode"] == "0" or json_data["pir_status"] == "0":
            GPIO.output(output_pin, GPIO.LOW)



# ip = find_ip_with_retry(mac)
# allot_ip = ip[0]
   

process = None
last_message_time = time.time()

conn = sqlite3.connect('mole.db')
cursor = conn.cursor()

while True:
    time.sleep(2)
    sql = '''select * from stat order by id; '''
    cursor.execute(sql)
    results = cursor.fetchall()
    
    columns = [description[0] for description in cursor.description]
    json_data = dict(zip(columns, results[0]))
    #print(json_data, flush=True)
    
    if json_data["stream_status"] == "1":
        print(f"Starting streaming", flush=True)
        GPIO.output(output_pin, GPIO.HIGH)
        ip = find_ip_with_retry(mac)
        allot_ip = ip[0]
        start_streaming()
    else:
        stop_streaming(json_data)

conn.close()
