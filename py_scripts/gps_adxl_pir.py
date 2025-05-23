import os
import json
import subprocess
import time
from datetime import datetime, timedelta, timezone
import serial
import sqlite3
import RPi.GPIO as GPIO
import busio
import adafruit_adxl34x
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import paho.mqtt.client as mqtt

conn = sqlite3.connect('mole.db')
cursor = conn.cursor()    

sql = '''select * from config; '''
cursor.execute(sql)
results = cursor.fetchall()

columns = [description[0] for description in cursor.description]
config_data = dict(zip(columns, results[0]))
conn.close()

topic = config_data['topic']
user = config_data['user']
password = config_data['password']
port = config_data['port']
broker_address = config_data['broker_address']

def on_message(client, userdata, msg):
    print(msg, flush=True)

def publish_mqtt(topic, message):
    client.publish(topic, message)

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"Unexpected disconnection. Publishing will message. stream mqtt stop", flush=True)
        publish_mqtt(f'R_GPS/{topic}', json.dumps({"status": "device disconnected"}))
        #stop_streaming()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        publish_mqtt(f'R_GPS/{topic}', json.dumps({"status": "device connected"}))
        print(f"Connected to MQTT broker: {broker_address} I/{topic}", flush=True)
    else:
        print(f"Failed to connect to MQTT broker with result code {rc}", flush=True)


client = mqtt.Client()
client.will_set(f'R_GPS/{topic}', payload=json.dumps({"status": "device disconnected"}), qos=0, retain=False)
client.on_disconnect = on_disconnect
client.on_connect = on_connect 
client.on_message = on_message 
client.username_pw_set(user, password)
client.connect(broker_address, port, 60)
client.loop_start() 

scl_pin = 3
sda_pin = 2

i2c = busio.I2C(scl=scl_pin, sda=sda_pin)
accelerometer = adafruit_adxl34x.ADXL345(i2c)
accelerometer.range = adafruit_adxl34x.Range.RANGE_2_G

ads = ADS.ADS1115(i2c, gain=2)

x1 = 0
y1 = 0
z1 = 0
accel_flag = 0
accel_count = 0

thr = config_data['accel_thr']
location_publish_interval = 1   #config_data['location_publish_interval']
restart_var = 0
duration = config_data['duration']

def convert_format(lat, lat_dir, lon, lon_dir):
    lat_degrees = int(lat[:2]) + float(lat[2:]) / 60
    lon_degrees = int(lon[:3]) + float(lon[3:]) / 60

    if lat_dir == 'S':
        lat_degrees = -lat_degrees
    if lon_dir == 'W':
        lon_degrees = -lon_degrees

    return lat_degrees, lon_degrees

def find_usb_port(device_path):
    try:
        result = subprocess.run(['udevadm', 'info', '--query=property', '--name=' + device_path], capture_output=True, text=True)
        
        for line in result.stdout.split('\n'):
            if 'ID_PATH=' in line:
                # Extract the USB port number
                usb_port_info = line.split('=')[1]
                return int(usb_port_info.split('.')[-1])

    except FileNotFoundError:
        print("udevadm command not found. Make sure udev is installed on your system.", flush=True)
        publish_mqtt(f'R_GPS/{topic}', json.dumps({"GPS_logs": "udevadm command not found. Make sure udev is installed on your system."}))
    except Exception as e:
        print(f"An error occurred: {str(e)}", flush=True)
        publish_mqtt(f'R_GPS/{topic}', json.dumps({"GPS_logs": str(e)}))

    return None

def find_ttyUSB0(max_ports=10):
    for i in range(max_ports):
        device_path = f'/dev/ttyUSB{i}'
        if os.path.exists(device_path):
            usb_port_index = find_usb_port(device_path)
            if usb_port_index is not None:
                print(f"/dev/ttyUSB0 is connected to USB port: {usb_port_index}", flush=True)
                publish_mqtt(f'R_GPS/{topic}', json.dumps({"GPS_logs": "/dev/ttyUSB0 is connected to USB port: {usb_port_index}"}))
                return usb_port_index

    print("/dev/ttyUSB0 not found on any USB port.", flush=True)
    publish_mqtt(f'R_GPS/{topic}', json.dumps({"GPS_logs": "/dev/ttyUSB0 not found on any USB port."}))
    return None
    
usb_port_index = find_ttyUSB0()


ser = serial.Serial(
    port= f'/dev/ttyUSB{usb_port_index}',
    baudrate=115200,
    timeout=1
)

def send_at(cmd, label):
    ser.reset_input_buffer()  # Flush serial input
    ser.write((cmd + "\r\n").encode())
    response = ser.read_until(b'OK\r\n').decode(errors='ignore')
    print(response, flush=True)
    publish_mqtt(f'R_GPS/{topic}', json.dumps({f"GPS_logs {label}": response}))
    return response

# send_at("AT+CGPSHOT", "CGPSHOT")
# time.sleep(15)

send_at("AT", "AT")
time.sleep(5)

send_at("AT+CGPS?", "Status")
time.sleep(5)

send_at("AT+CGPS=0", "OFF")
time.sleep(15)

send_at('AT+CGPSURL="supl.google.com:7276"', "CGPSURL")
time.sleep(5)

send_at("AT+CGPSSSL=0", "SSL")
time.sleep(5)

send_at("AT+CGPS=1,2", "ON")
time.sleep(5)

# send_at("AT+CGPSHOT", "hot")
# time.sleep(10)

send_at("AT+CGPSURL?", "CGPSURL")
time.sleep(10)

send_at("AT+CGPS?", "Status")
time.sleep(10)

location_timer = time.time() + location_publish_interval     

    
def on_publish_location():
    try:
        #print("on_publish_location", flush=True)
        publish_mqtt(f'R_GPS/{topic}', json.dumps({"GPS_logs": "on_publish_location"}))
        global restart_var
        
        command = "AT+CSQ"
        ser.write((command + "\r\n").encode())
        response = ser.read_until(b'OK\r\n').decode(errors='ignore')
        nw = response.split(':')[1].split(',')[0].strip()
        #print(f"response {nw} {response}", flush=True)

        send_at("AT+CGPS?", "Status")
        time.sleep(2)
        
        command = "AT+CGPSINFO"
        ser.reset_input_buffer()  # Flush serial input
        ser.write((command + "\r\n").encode())
        response = ser.read_until(b'OK\r\n').decode(errors='ignore')
        publish_mqtt(f'R_GPS/{topic}', json.dumps({"GPS_logs": str(response)}))
        
        latitude = ""
        longitude = ""
        lat_dir = ""
        lon_dir = ""
        output_lat = 0 
        output_long = 0
        
        values = response.strip().split(',')
        if len(response) > 30:
            latitude = values[0].replace("+CGPSINFO: ", "").strip()
            lat_dir = values[1].strip()
            longitude = values[2].strip()
            lon_dir = values[3].strip()
            restart_var = 0

        output_lat, output_long = convert_format(latitude, lat_dir, longitude, lon_dir)
            
        if len(longitude) == 0:
            restart_var = restart_var + 1
            publish_mqtt(f'R_GPS/{topic}', json.dumps({"GPS_logs restart_var": restart_var}))
            if restart_var > 5000:
                ser.reset_input_buffer()
                ser.write("AT+CGPS=0\r\n".encode())
                x = ser.read_until(b'OK\r\n').decode(errors='ignore')
                print(response, flush=True)
                publish_mqtt(f'R_GPS/{topic}', json.dumps({"GPS_logs": x}))
                time.sleep(5)

                ser.reset_input_buffer()
                ser.write("AT+CGPSNMEA=31\r\n".encode())
                x = ser.read_until(b'OK\r\n').decode(errors='ignore')
                print(response, flush=True)
                publish_mqtt(f'R_GPS/{topic}', json.dumps({"GPS_logs": x}))
                time.sleep(5)
                
                ser.reset_input_buffer()
                ser.write("AT+CGPS=1,3\r\n".encode())
                x = ser.read_until(b'OK\r\n').decode(errors='ignore')
                print(response, flush=True)
                publish_mqtt(f'R_GPS/{topic}', json.dumps({"GPS_logs": x}))
                time.sleep(5)

                restart_var = 0
        
        conn = sqlite3.connect('mole.db')
        cursor = conn.cursor() 
        sql = f'''update stat set lat = {output_lat}, long = {output_long}, nw_strength = "{nw}" where id = 1;'''
        cursor.execute(sql)                        
        conn.commit()
        conn.close()
        
        location_message = {"lat": latitude, "long": longitude}
        
    except Exception as e:
        print(f"An error occurred: {str(e)}", flush=True)
        publish_mqtt(f'R_GPS/{topic}', json.dumps({"GPS_logs": str(e)}))

while True:
    try:    
        conn = sqlite3.connect('mole.db')
        cursor = conn.cursor()
        
        while True:        
            x, y, z = accelerometer.acceleration
            value = AnalogIn(ads, ADS.P0)
            vol1 = value.voltage * 2
            
            value = AnalogIn(ads, ADS.P1)
            vol2 = value.voltage
            
            value = AnalogIn(ads, ADS.P2)
            vol3 = value.voltage
                
            sql = f'''update stat set x_axis = {x}, y_axis = {y}, z_axis = {z}, bat_vol = {vol1}, temp_vol = {vol2}, power_vol = {vol3} where id = 1;'''
            cursor.execute(sql)                        
            conn.commit()
            cTime = datetime.now(timezone.utc)
            publish_mqtt(f'R_GPS/{topic}', json.dumps({"GPS_logs": cTime.strftime('%Y:%m:%d %H:%M:%S')}))
            
            if (x1 - thr > x) or (x1 + thr < x) or (y1 - thr > y) or (y1 + thr < y) or (z1 - thr > z) or (z1 + thr < z):
                if accel_flag == 0:
                    print("**** intrp Occur **** ", flush=True)
                    publish_mqtt(f'R_GPS/{topic}', json.dumps({"GPS_logs": "activity"}))
                    
                    sql = f'''update stat set adxl_status = "1", timestamp = "{cTime.strftime('%Y:%m:%d %H:%M:%S')}" where id = 1;'''
                    cursor.execute(sql)                        
                    conn.commit() 

                accel_count = 0
                x1 = x
                y1 = y
                z1 = z
                accel_flag = 1
                
            if accel_flag == 1 and accel_count >= duration :
                accel_flag = 0
                accel_count = 0
                print("**** inactivity Occur **** ", flush=True)
                    
                sql = f'''update stat set adxl_status = "0", timestamp = "{cTime.strftime('%Y:%m:%d %H:%M:%S')}" where id = 1;'''
                cursor.execute(sql)                        
                conn.commit() 
                
                publish_mqtt(f'R_GPS/{topic}', json.dumps({"GPS_logs": "inactivity"}))
                
            accel_count = accel_count + 1    
            
            current_time = time.time()
            if current_time >= location_timer:
                on_publish_location()
                location_timer = current_time + location_publish_interval

            time.sleep(2)

    except Exception as e:
        publish_mqtt(f'R_GPS/{topic}', json.dumps({"GPS_logs": str(e)}))
        time.sleep(5)
        # conn.close()