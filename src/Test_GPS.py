#!/usr/bin/python
# -*- coding:utf-8 -*-            								
import time               								# Import time module to add delays
import paho.mqtt.client as mqtt  						# Import paho.mqtt for MQTT communication
import json  
import sys
import platform
import logging
if platform.system() != "Linux" or platform.machine() != "armv7l":
    sys.path.insert(0, "/home/v005101/GPS_web_app")
    from lib_mock.GPIO import GPIO as GPIO
    import lib_mock.mock_serial as serial
else:
    import RPi.GPIO as GPIO
    import serial


#============================ Initialize serial communication with the SIM7600X module at 115200 baud rate =======
ser = serial.Serial('/dev/ttyS0', 115200)
ser.flushInput()  										# Clear the input buffer to start fresh

#============================ MQTT Configuration for ThingBoard ================================
THINGSBOARD_HOST = "demo.thingsboard.io"  # e.g., "demo.thingsboard.io"
ACCESS_TOKEN = "tGZ5ZOcgP64j10xGLaVB"  # Replace with your actual device access token

# MQTT Setup
client = mqtt.Client()
client.username_pw_set(ACCESS_TOKEN)  # Set the access token for authentication
client.connect(THINGSBOARD_HOST, 1883, 60)  # Connect to ThingBoard MQTT broker

# =========================
# Logging setup
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

#============================ GPIO pin number for controlling power to the SIM7600X module =======================
power_key = 6
rec_buff = ''  											# Buffer to store the response from the serial port
rec_buff2 = ''  										# Another buffer (not used in this code)

#============================ Function to send AT commands and wait for a specific response ======================
def send_at(command, back, timeout):
    rec_buff = ''  										     # Initialize the response buffer as empty
    ser.write((command + '\r\n').encode())  			     # Send the AT command followed by a carriage return
    time.sleep(timeout)  								     # Wait for the specified timeout to receive a response

    # Check if there is any data in the input buffer
    if ser.inWaiting():
        time.sleep(0.01) 								     # Short delay to ensure all data is received
        rec_buff = ser.read(ser.inWaiting())  			     # Read all available data in the buffer

    # If a response was received
    if rec_buff != '':
        # Check if the expected response ('back') is in the received data
        if back not in rec_buff.decode():
            logger.warning(f"Command'{command}' ERROR\n")  						 # Print error if response doesn't match
            logger.warning(f"Command'{command}' back:\t{rec_buff.decode()}")
            return 0,"Null"  										             # Return 0 to indicate error
        else:
            logger.info(f"AT Response: {rec_buff.decode()}")  					 # Print the received response
            return 1,rec_buff.decode()  										 # Return 1 to indicate success
    else:
        logger.warning("GPS is not ready")  							         # Print error if no response was received
        return 0,"Null"  											             # Return 0 to indicate error

# Function to get the GPS position
def get_gps_position():
    rec_null = True  										 # Initialize the flag indicating whether GPS data is ready
    answer = 0 												 # Initialize the answer flag
    logger.info('Start GPS session...') 					 # Print starting message
    rec_buff = '' 											 # Clear the response buffer

    # Send command to enable GPS
    send_at('AT+CGPS=1,1', 'OK', 1)
    if not send_at('AT+CGPS=1,1', 'OK', 1):
        logger.error("Failed to enable GPS")
        return False
    time.sleep(2) 											 # Wait for 2 seconds to allow GPS module to initialize

    # Continuously get GPS information until valid data is received
    while rec_null:
        answer, data = send_at('AT+CGPSINFO', '+CGPSINFO: ', 1) 	 # Request GPS info
        if 1 == answer:
            answer = 0
            # If the GPS info contains only commas, it means GPS data is not ready
            if ',,,,,,' in rec_buff:
                logger.warning('GPS is not ready')
                rec_null = False 							 # Stop waiting if GPS data is not available
                time.sleep(1) 								 # Wait for a second before retrying
            if ":" in data:
                data = data.split(":", 1)[1].strip()
            position = data.split(',')
            if len(position) >= 4:
                latitude      = position[0]
                lat_direction = position[1]
                longitude     = position[2]
                lon_direction = position[3]
                
                if latitude and longitude:
                    # Convert latitude and longitude to decimal degrees
                    latitude_degrees_decimal = float(latitude[:2]) + float(latitude[2:]) / 60.0
                    if lat_direction == 'S':
                        latitude_degrees_decimal = -latitude_degrees_decimal
                    
                    longtitude_degrees_decimal = float(longitude[:3]) + float(longitude[3:]) / 60.0
                    if lon_direction == 'W':
                        longtitude_degrees_decimal = -longtitude_degrees_decimal
                    
                    logger.info(f"Latitude:{latitude_degrees_decimal}, Longitude:{longtitude_degrees_decimal}")
                    
                    # push data to thingsboard
                    publish_to_thingboard(latitude_degrees_decimal, longtitude_degrees_decimal)
                else:
                    logger.info('GPS data is incomplete')
        else:
            logger.error('error %d' % answer) 				 # Print error message if AT command fails
            rec_buff = '' 									 # Clear the response buffer
            send_at('AT+CGPS=0', 'OK', 1) 					 # Disable GPS session
            return False 									 # Return False if there is an error
        time.sleep(1) 									     # Wait before trying again


#========================= Function to power on the SIM7600X module ====================================
def power_on(power_key):
    logger.info('SIM7600X is starting:') 					 # Print the power-on message

    GPIO.setmode(GPIO.BCM) 									 # Set the GPIO pin numbering mode to BCM
    GPIO.setwarnings(False) 								 # Disable GPIO warnings (optional)
    GPIO.setup(power_key, GPIO.OUT) 						 # Set the power_key GPIO pin as an output
    
    time.sleep(0.1) 										 # Wait for 100ms
    GPIO.output(power_key, GPIO.HIGH) 						 # Set the GPIO pin HIGH (turn on power)
    time.sleep(2) 											 # Wait for 2 seconds to let the SIM7600X power up
    GPIO.output(power_key, GPIO.LOW) 						 # Set the GPIO pin LOW (turn off power)
    time.sleep(5) 											 # Wait for 5 seconds to allow the SIM7600X to initialize
    ser.flushInput() 										 # Clear the serial input buffer
    logger.info('SIM7600X is ready') 						 # Print the ready message

#========================= Function to power down the SIM7600X module ====================================
def power_down(power_key):
    logger.info('SIM7600X is logging off:') 				 # Print the power-down message
    GPIO.output(power_key, GPIO.HIGH) 						 # Set the power_key GPIO pin HIGH (turn on power)
    time.sleep(3) 											 # Wait for 3 seconds
    GPIO.output(power_key, GPIO.LOW) 						 # Set the power_key GPIO pin LOW (turn off power)
    time.sleep(18) 											 # Wait for 18 seconds before completely powering down
    logger.info('Good bye!') 								 # Print the shutdown message

#========================= Function to publish data to ThingBoard ===============================
def publish_to_thingboard(latitude, longitude):
    # Construct the JSON payload with GPS data
    payload = {
        "gps_latitude": latitude,
        "gps_longitude": longitude
    }
    
    # Publish the data to ThingBoard
    client.publish("v1/devices/me/telemetry", json.dumps(payload), qos=1)
    logger.info("Data sent to ThingBoard successfull!")

#========================= Main program execution ====================================

def main():
    try:
        power_on(power_key) 									 # Power on the SIM7600X
        get_gps_position()
        power_down(power_key) 									 # Power down the SIM7600X
    except Exception as e: 										 # If there is an exception (error) during execution
        logger.error(f"Error: {e}") 							 # Print the error message
        if ser != None: 										 # If serial is initialized, close it
            ser.close()
        power_down(power_key) 									 # Ensure the SIM7600X is powered down
        GPIO.cleanup() 											 # Clean up the GPIO pins
    if ser != None:
        ser.close() 											 # Close the serial connection
        GPIO.cleanup() 											 # Clean up GPIO settings

if __name__ == '__main__':
    main() 													     # Run the main function