import os
import json
import subprocess
import time
from datetime import datetime, timedelta
import serial
import sqlite3
import RPi.GPIO as GPIO
import busio
import adafruit_adxl34x

scl_pin = 3
sda_pin = 2

i2c = busio.I2C(scl=scl_pin, sda=sda_pin)
accelerometer = adafruit_adxl34x.ADXL345(i2c)
accelerometer.range = adafruit_adxl34x.Range.RANGE_2_G

x1 = 0
y1 = 0
z1 = 0
accel_flag = 0
accel_count = 0

conn = sqlite3.connect('mole.db')
cursor = conn.cursor()    

sql = '''select * from config; '''
cursor.execute(sql)
results = cursor.fetchall()

columns = [description[0] for description in cursor.description]
config_data = dict(zip(columns, results[0]))
conn.close()

thr = config_data['accel_thr']
location_publish_interval = config_data['location_publish_interval']
restart_var = 0
duration = config_data['duration']

def convert_format(lat, long):
    lat_degrees = int(lat[:2]) + float(lat[2:]) / 60
    long_degrees = int(long[:3]) + float(long[3:]) / 60
    return lat_degrees, long_degrees
    
def on_publish_location():
    try:
        #print("on_publish_location", flush=True)
        global restart_var
        
        command = "AT+CSQ"
        ser.write((command + "\r\n").encode())
        response = ser.read_until(b'OK\r\n').decode(errors='ignore')
        nw = response.split(':')[1].split(',')[0].strip()
        #print(f"response {nw} {response}", flush=True)
        
        command = "AT+CGPSINFO"
        ser.write((command + "\r\n").encode())
        response = ser.read_until(b'OK\r\n').decode(errors='ignore')
        
        latitude = ""
        longitude = ""
        
        values = response.strip().split(',')
        if len(response) > 15:
            latitude = values[0]
            longitude = values[2]
            latitude = latitude.replace("+CGPSINFO: ", "")
            restart_var = 0
            output_lat, output_long = convert_format(latitude, longitude)
            
        if len(longitude) == 0:
            restart_var = restart_var + 1
            if restart_var > 5:
                ser.write("AT+CGPS=0\r\n".encode())
                x = ser.read_until(b'OK\r\n').decode(errors='ignore')
                print(f"r {x}", flush=True)
                
                
                ser.write("AT+CGPS=1\r\n".encode())
                x = ser.read_until(b'OK\r\n').decode(errors='ignore')
                print(f"r {x}", flush=True)
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
    except Exception as e:
        print(f"An error occurred: {str(e)}", flush=True)

    return None

def find_ttyUSB0(max_ports=10):
    for i in range(max_ports):
        device_path = f'/dev/ttyUSB{i}'
        if os.path.exists(device_path):
            usb_port_index = find_usb_port(device_path)
            if usb_port_index is not None:
                print(f"/dev/ttyUSB0 is connected to USB port: {usb_port_index}", flush=True)
                return usb_port_index

    print("/dev/ttyUSB0 not found on any USB port.", flush=True)
    return None
    
usb_port_index = find_ttyUSB0()


ser = serial.Serial(
    port= f'/dev/ttyUSB{usb_port_index}',
    baudrate=115200,
    timeout=1
)

ser.write("AT\r\n".encode())
response = ser.read_until(b'OK\r\n').decode(errors='ignore')
print(response, flush=True)

ser.write("AT+CGPS=1\r\n".encode())
response = ser.read_until(b'OK\r\n').decode(errors='ignore')
print(response, flush=True)


location_timer = time.time() + location_publish_interval     

try:    
    conn = sqlite3.connect('mole.db')
    cursor = conn.cursor()
    
    while True:        
        x, y, z = accelerometer.acceleration
            
        sql = f'''update stat set x_axis = {x}, y_axis = {y}, z_axis = {z} where id = 1;'''
        cursor.execute(sql)                        
        conn.commit()
        cTime = datetime.now()
        
        if (x1 - thr > x) or (x1 + thr < x) or (y1 - thr > y) or (y1 + thr < y) or (z1 - thr > z) or (z1 + thr < z):
            if accel_flag == 0:
                print("**** intrp Occur **** ", flush=True)
                #publish_mqtt(f'R/{topic}', json.dumps({"event": "activity"}))
                
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
            
            #publish_mqtt(f'R/{topic}', json.dumps({"event": "inactivity"}))
            
        accel_count = accel_count + 1    
        
        current_time = time.time()
        if current_time >= location_timer:
            on_publish_location()
            location_timer = current_time + location_publish_interval

        time.sleep(1)

except KeyboardInterrupt:
	conn.close()
