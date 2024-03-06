import RPi.GPIO as GPIO
import time
import os
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import subprocess
import serial
import busio
import adafruit_adxl34x

import os
import subprocess 

scl_pin = 3
sda_pin = 2

i2c = busio.I2C(scl=scl_pin, sda=sda_pin)
accelerometer = adafruit_adxl34x.ADXL345(i2c)

thr = config_data['accel_thr']
x1 = 0
y1 = 0
z1 = 0
accel_flag = 0
accel_count = 0

config_file_path = 'config.json'
with open(config_file_path, 'r') as file:
    config_data = json.load(file)

url = config_data['url']
topic = config_data['topic']

user = config_data['user']
password = config_data['password']
port = config_data['port']
broker_address = config_data['broker_address']


def publish_mqtt(topic, message):
    client.publish(topic, message)

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"Unexpected disconnection. Publishing will message.")
        publish_mqtt(f'R/{topic}', json.dumps({"status": "Adxl disconnection"}))

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected to MQTT broker: {broker_address}")
        publish_mqtt(f'R/{topic}', json.dumps({"status": "Adxl connection"}))
        local_ip_address = subprocess.check_output(['hostname', '-I']).decode('utf-8').strip()
        local_ip_address = local_ip_address.split()[0]
        print(f"local_ip_address: {local_ip_address}")
        publish_mqtt(f'R/{topic}', json.dumps({"local_ip_address": local_ip_address}))
    else:
        print(f"Failed to connect to MQTT broker with result code {rc}")

try:
    client = mqtt.Client()
    client.will_set(f'R/{topic}', payload=json.dumps({"status": "Adxl disconnection"}), qos=0, retain=False)
    client.on_disconnect = on_disconnect
    client.on_connect = on_connect 
    client.username_pw_set(user, password)
    client.connect(broker_address, port, 60)
    client.loop_start()  
except:
    print("mqtt connection fail", flush="True")

    
try:
    while True:
        x, y, z = accelerometer.acceleration
        json_file_path = 'stat.json'
        #with open(json_file_path, 'r') as file:
         #   stats = json.load(file)
            
        #stats['x-axis'] = x
        #stats['y-axis'] = y
        #stats['z-axis'] = z
        #current_time = datetime.now()
        #stats['timestamp'] = current_time.strftime('%Y:%m:%d %H:%M:%S')
        
        #with open(json_file_path, 'w') as file:
         #   json.dump(stats, file)
        #print("%f %f %f" % (x, y, z), flush=True)
        
        if (x1 - thr > x) or (x1 + thr < x) or (y1 - thr > y) or (y1 + thr < y) or (z1 - thr > z) or (z1 + thr < z):
            if accel_flag == 0:
                print("**** intrp Occur **** ", flush=True)
                publish_mqtt(f'R/{topic}', json.dumps({"event": "activity"}))
                json_file_path = 'stat.json'
                with open(json_file_path, 'r') as file:
                    stats = json.load(file)
                    
                stats['adxl_status'] = "1"
                
                with open(json_file_path, 'w') as file:
                    json.dump(stats, file)
            accel_count = 0
            x1 = x
            y1 = y
            z1 = z
            accel_flag = 1
            
        if accel_flag == 1 and accel_count >= 60 :
            accel_flag = 0
            accel_count = 0
            print("**** inactivity Occur **** ", flush=True)
            #with open(json_file_path, 'r') as file:
            #    stats = json.load(file)
                
            #stats['adxl_status'] = "0"
            
            #with open(json_file_path, 'w') as file:
             #   json.dump(stats, file)
            publish_mqtt(f'R/{topic}', json.dumps({"event": "inactivity"}))
            
        accel_count = accel_count + 1
        time.sleep(1)

except KeyboardInterrupt:
    client.disconnect()
    client.loop_stop()
