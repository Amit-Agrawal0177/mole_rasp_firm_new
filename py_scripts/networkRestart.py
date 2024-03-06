import subprocess
import time

counter = 0

def check_network():
    try:
        subprocess.check_output(["ping", "-c", "1", "google.com"])
        return True
    except subprocess.CalledProcessError:
        return False

def restart_network():
    if counter > 20 :
        print("Restarting networking...")
        subprocess.run(["sudo", "reboot"])
    #subprocess.run(["sudo", "ifconfig", "usb0", "down"])
    #time.sleep(10)
    #subprocess.run(["sudo", "ifconfig", "usb0", "up"])
    #subprocess.run(["sudo", "systemctl", "restart", "hostapd"])

if __name__ == "__main__":
    check_interval = 30  

    while True:
        if not check_network():
            print("Network is down. Restarting networking...")
            counter = counter + 1
            restart_network()
        else:
            print("Network is up.")
            counter = 0

        time.sleep(check_interval)
