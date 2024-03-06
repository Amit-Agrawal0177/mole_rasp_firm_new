import json
import time
import paho.mqtt.client as mqtt
import subprocess
import RPi.GPIO as GPIO
import io
import re
from pydub import AudioSegment
from pydub.playback import play
import os
import sqlite3


output_pin = 18

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(output_pin, GPIO.OUT)

def play_sound(sound_file):
    sound = AudioSegment.from_file(sound_file)
    play(sound)

last_message_time = time.time()
last_demand_message_time = time.time()


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
mac = config_data['ameba_mac']

user = config_data['user']
password = config_data['password']
port = config_data['port']
broker_address = config_data['broker_address']
allot_ip = ""

def on_message(client, userdata, msg):
    global process
    global last_message_time, last_demand_message_time
    conn = sqlite3.connect('mole.db')
    cursor = conn.cursor()
    
    if msg.topic == f"Ia/{topic}":        
        temp_audio_file = "audio.mp3"
        with open(temp_audio_file, "wb") as audio_file:
            audio_file.write(msg.payload)
            
        sql = '''update stat set audio_flag = "1" where id = 1;'''
        cursor.execute(sql)                        
        conn.commit()
    else:
        
        message = msg.payload.decode("utf-8")
        print(f"message from MQTT broker: {message}", flush=True)
        try:    
            message = json.loads(message)        
            if "ins" in message:
                instruction = message["ins"]
                if instruction == "start demand mode":
                    
                    sql = '''update stat set demand_mode = "1" where id = 1;'''
                    cursor.execute(sql)                        
                    conn.commit()
                    
                    publish_mqtt(f'R/{topic}', json.dumps({"event": "demand mode started"}))
                    last_demand_message_time = time.time()                    
                            
                elif instruction == "start alert mode":
                    sql = '''update stat set alert_mode = "1" where id = 1;'''
                    cursor.execute(sql)
                    conn.commit()
                    publish_mqtt(f'R/{topic}', json.dumps({"event": "alert mode started"}))
                            
                elif instruction == "stop alert mode":
                    sql = '''update stat set alert_mode = "0" where id = 1;'''
                    cursor.execute(sql)
                    conn.commit()
                    publish_mqtt(f'R/{topic}', json.dumps({"event": "alert mode stopped"}))
                    
                elif instruction == "start reboot":
                    publish_mqtt(f'R/{topic}', json.dumps({"event": "reboot mode started"}))
                    reboot_raspberry_pi()
                    
                elif instruction == "start streaming":
                    sql = '''update stat set stream_status = "1" where id = 1;'''
                    cursor.execute(sql)
                    conn.commit()
                    publish_mqtt(f'R/{topic}', json.dumps({"event": "stream mode started"}))
                    last_message_time = time.time()
                    
                elif instruction == "start ota":
                    publish_mqtt(f'R/{topic}', json.dumps({"event": "ota started"}))
                    ota_raspberry_pi()
                           
            elif "fps" in message:
                sql = f'''update config set fps = "{message["fps"]}", height = "{message["height"]}", width = "{message["width"]}";'''
                cursor.execute(sql)
                conn.commit()

            elif "accel_thr" in message:
                sql = f'''update config set accel_thr = "{message["accel_thr"]}";'''
                cursor.execute(sql)
                conn.commit()
        except:
            pass
    conn.close()
    
def reboot_raspberry_pi():
    try:
        subprocess.run(['sudo', 'reboot'])
    except Exception as e:
        print(f"Error: {e}")

def ota_raspberry_pi():
    try:
        subprocess.run(['git', 'pull', 'origin', 'develop'])
    except Exception as e:
        print(f"Error: {e}")
                    
def publish_mqtt(topic, message):
    client.publish(topic, message)

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"Unexpected disconnection. Publishing will message. stream mqtt stop", flush=True)
        publish_mqtt(f'R/{topic}', json.dumps({"status": "device disconnected"}))
        GPIO.output(output_pin, GPIO.LOW)
        #stop_streaming()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        publish_mqtt(f'R/{topic}', json.dumps({"status": "device connected"}))
        print(f"Connected to MQTT broker: {broker_address} I/{topic}", flush=True)
        GPIO.output(output_pin, GPIO.HIGH)
        client.subscribe(f'I/{topic}')
        client.subscribe(f'Ia/{topic}')
    else:
        print(f"Failed to connect to MQTT broker with result code {rc}", flush=True)


client = mqtt.Client()
client.will_set(f'R/{topic}', payload=json.dumps({"status": "device disconnected"}), qos=0, retain=False)
client.on_disconnect = on_disconnect
client.on_connect = on_connect 
client.on_message = on_message 
client.username_pw_set(user, password)
client.connect(broker_address, port, 60)
client.loop_start()  

def update_output(data):
    conn = sqlite3.connect('mole.db')
    cursor = conn.cursor()
    sql =  f'''INSERT INTO output (  demand_mode,  nw_strength,  pir_status,  adxl_status,  stream_status,  alert_mode,  audio_flag,  lat,  long,  x_axis,  y_axis,  z_axis,  timestamp,  ver) 
    VALUES (  "{data["demand_mode"]}",  "{data["nw_strength"]}", "{data["pir_status"]}", "{data["adxl_status"]}", "{data["stream_status"]}", "{data["alert_mode"]}", "{data["audio_flag"]}",
    {data["lat"]}, {data["long"]}, {data["x_axis"]}, {data["y_axis"]}, {data["z_axis"]}, "{data["timestamp"]}", "{data["ver"]}");'''
    #print(sql, flush=True)  
    cursor.execute(sql)
    conn.commit() 
    conn.close()
    
def update_prev(data):
    conn = sqlite3.connect('mole.db')
    cursor = conn.cursor()
    sql =  f'''update stat set demand_mode = "{data["demand_mode"]}",  nw_strength = "{data["nw_strength"]}",  pir_status = "{data["pir_status"]}",  adxl_status = "{data["adxl_status"]}",  
    stream_status = "{data["stream_status"]}",  alert_mode = "{data["alert_mode"]}",  audio_flag = "{data["audio_flag"]}",  lat = {data["lat"]},  long = {data["long"]},  x_axis = {data["x_axis"]},  
    y_axis = {data["y_axis"]},  z_axis = {data["z_axis"]},  timestamp = "{data["timestamp"]}",  ver = "{data["ver"]}" where id  = 2;'''
    #print(sql, flush=True)  
    cursor.execute(sql)
    conn.commit() 
    conn.close()

push_interval = 10
data_timer = time.time() + push_interval
flag1 = 0
flag2 = 0
flag3 = 0
flag4 = 0
current_time = time.time()
save_time = time.time()

def main():
    global data_timer, push_interval, flag1, flag2, flag3, flag4, current_time, last_demand_message_time, last_message_time, save_time

    conn = sqlite3.connect('mole.db')
    cursor = conn.cursor()
    
    while True:        
        sql = '''select * from stat order by id; '''
        cursor.execute(sql)
        results = cursor.fetchall()
        
        columns = [description[0] for description in cursor.description]
        json_data = dict(zip(columns, results[0]))
        #print(json_data, flush=True)
        
        columns = [description[0] for description in cursor.description]
        prev_data = dict(zip(columns, results[1]))        
        #print(prev_data, flush=True)        
         
        
        update_prev(json_data)
        
        if json_data["adxl_status"] == "0" and prev_data["adxl_status"] == "1":
            publish_mqtt(f'R/{topic}', json.dumps({"event": "adxl movement stopped"}))
            
        if json_data["adxl_status"] == "1" and prev_data["adxl_status"] == "0":
            publish_mqtt(f'R/{topic}', json.dumps({"event": "adxl movement started"}))
            
        if json_data["pir_status"] == "0" and prev_data["pir_status"] == "1":
            publish_mqtt(f'R/{topic}', json.dumps({"event": "pir movement stopped"}))
            
        if json_data["pir_status"] == "1" and prev_data["pir_status"] == "0":
            publish_mqtt(f'R/{topic}', json.dumps({"event": "pir movement started"}))            
            
        if json_data["demand_mode"] == "1" and json_data["adxl_status"] == "1":
            if flag1 == 0:
                flag1 = 1
                flag2 = 0
                flag3 = 0
                flag4 = 0
                push_interval = 10
                data_timer = current_time + push_interval                
                 
            update_output(json_data)
            
            
        elif json_data["demand_mode"] == "1" and json_data["adxl_status"] == "0":
            if flag2 == 0:
                flag1 = 0
                flag2 = 1
                flag3 = 0
                flag4 = 0
                push_interval = 120
                data_timer = current_time + push_interval
                save_timer = save_time + 60
                
            save_time = time.time()
            if save_time >= save_timer:
                save_timer = save_time + 60                   
                update_output(json_data) 
            
        elif json_data["demand_mode"] == "0" and json_data["adxl_status"] == "1":
            if flag3 == 0:
                flag1 = 0
                flag2 = 0
                flag3 = 1
                flag4 = 0
                push_interval = 120
                data_timer = current_time + push_interval
                save_timer = save_time + 60
                
            save_time = time.time()
            if save_time >= save_timer:
                save_timer = save_time + 60                
                update_output(json_data)
            
        elif json_data["demand_mode"] == "0" and json_data["adxl_status"] == "0":
            if flag4 == 0:
                flag1 = 0
                flag2 = 0
                flag3 = 0
                flag4 = 1
                push_interval = 1800
                data_timer = current_time + push_interval
                save_timer = save_time + 600
                
            save_time = time.time()
            if save_time >= save_timer:
                save_timer = save_time + 600                
                update_output(json_data)

        else :
            update_output(json_data)

        current_time = time.time()
        
        sql = '''select * from output; '''
        cursor.execute(sql)
        results = cursor.fetchall()      
        columns = [description[0] for description in cursor.description]
        existing_data = [dict(zip(columns, row)) for row in results] 
        
        if current_time >= data_timer:
            publish_mqtt(f'R/{topic}', json.dumps(existing_data))
            sql = '''delete from output;'''
            cursor.execute(sql)
            conn.commit()
            data_timer = current_time + push_interval
        
        if time.time() - last_message_time > 30:
            if json_data["stream_status"] == "1":
                sql = '''update stat set stream_status = "0" where id = 1;'''
                cursor.execute(sql)
                conn.commit()
                publish_mqtt(f'R/{topic}', json.dumps({"event": "stream mode stopped"}))
        
        if time.time() - last_demand_message_time > 30:
            if json_data["demand_mode"] == "1":
                sql = '''update stat set demand_mode = "0" where id = 1;'''
                cursor.execute(sql)
                conn.commit()                
                publish_mqtt(f'R/{topic}', json.dumps({"event": "demand mode stopped"}))
                
        time.sleep(10)

if __name__ == "__main__":
    main()
    conn.close()
    


