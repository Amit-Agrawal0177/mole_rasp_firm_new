import os
import json
import time
import subprocess
import re

config_file_path = 'config.json'
with open(config_file_path, 'r') as file:
    config_data = json.load(file)
    
mac = config_data['ameba_mac']
rtmp_url = f'rtmp://localhost:1935/live/'

stats = {
		"demand_mode" : "",
		"nw_strength" : "",
		"pir_status" : "",
		"adxl_status" : "",
		"stream_status" : "",
		"lat" : "",
		"long" : "",
		"x-axis" : "",
		"y-axis" : "",
		"z-axis" : "" 
}
json_file_path = 'stat.json'
with open(json_file_path, 'w') as file:
    json.dump(stats, file)

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
    
try:
    ip = find_ip_with_retry(mac)
    alot_ip = ip[0]
except Exception as e:
    print(f"An error occurred: {str(e)}", flush=True)



#command = 'ffmpeg -f video4linux2 -input_format h264 -i /dev/video0 -f alsa -i default -c:v copy -c:a aac -strict experimental -f flv  ' + rtmp_url
#command = 'ffmpeg -f video4linux2 -input_format h264 -i /dev/video0 -c:v copy -f flv ' + rtmp_url
#command = 'ffmpeg -f dshow -i video="Integrated Webcam" -f dshow -i audio="Microphone (2- High Definition Audio Device)" -c:v libx264 -c:a aac -strict -2 -f flv ' + rtmp_url


command = 'ffmpeg -i rtsp://' + alot_ip + ':555 -c:v copy -c:a aac -strict experimental -f flv ' + rtmp_url
print(command)

retry_limit = 50
retry_count = 0

while True:
    print(f"Attempt #{retry_count + 1}: {command}", flush=True)

    return_code = os.system(command)

    if return_code == 0:
        print("Command executed successfully.", flush=True)
    else:
        print(f"Command failed with return code: {return_code}", flush=True)
        retry_count += 1
        time.sleep(5)

if retry_count == retry_limit:
    print("Maximum retries reached. Exiting.", flush=True)

