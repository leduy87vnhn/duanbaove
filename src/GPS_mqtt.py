#!/usr/bin/python
# -*- coding:utf-8 -*-
import RPi.GPIO as GPIO  								# Import RPi.GPIO to control GPIO pins on Raspberry Pi
import serial             								# Import pySerial for serial communication with SIM7600X
import time               								# Import time module to add delays
import paho.mqtt.client as mqtt  						# Import paho.mqtt for MQTT communication
import json               								# Import json for creating JSON payloads

#============================ Initialize serial communication with the SIM7600X module at 115200 baud rate =======
ser = serial.Serial('/dev/ttyS0', 115200)
ser.flushInput()  										# Clear the input buffer to start fresh

#============================ MQTT Configuration for ThingBoard ================================
THINGSBOARD_HOST = "your_thingboard_host"  # e.g., "demo.thingsboard.io"
ACCESS_TOKEN = "your_device_token"  # Replace with your actual device access token

# MQTT Setup
client = mqtt.Client()
client.username_pw_set(ACCESS_TOKEN)  # Set the access token for authentication
client.connect(THINGSBOARD_HOST, 1883, 60)  # Connect to ThingBoard MQTT broker

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
            print(command + ' ERROR')  						 # Print error if response doesn't match
            print(command + ' back:\t' + rec_buff.decode())  # Print the actual response
            return 0  										 # Return 0 to indicate error
        else:
            print(rec_buff.decode())  						 # Print the received response
            return 1  										 # Return 1 to indicate success
    else:
        print('GPS is not ready')  							 # Print error if no response was received
        return 0  											 # Return 0 to indicate error

# Function to get the GPS position
def get_gps_position():
    rec_null = True  										 # Initialize the flag indicating whether GPS data is ready
    answer = 0 												 # Initialize the answer flag
    print('Start GPS session...') 							 # Print starting message
    rec_buff = '' 											 # Clear the response buffer

    # Send command to enable GPS
    send_at('AT+CGPS=1,1', 'OK', 1)
    time.sleep(2) 											 # Wait for 2 seconds to allow GPS module to initialize

    # Continuously get GPS information until valid data is received
    while rec_null:
        answer = send_at('AT+CGPSINFO', '+CGPSINFO: ', 1) 	 # Request GPS info
        if 1 == answer:
            answer = 0
            # If the GPS info contains only commas, it means GPS data is not ready
            if ',,,,,,' in rec_buff:
                print('GPS is not ready')
                rec_null = False 							 # Stop waiting if GPS data is not available
                time.sleep(1) 								 # Wait for a second before retrying
        else:
            print('error %d' % answer) 						 # Print error message if AT command fails
            rec_buff = '' 									 # Clear the response buffer
            send_at('AT+CGPS=0', 'OK', 1) 					 # Disable GPS session
            return False 									 # Return False if there is an error
        time.sleep(1) 									 # Wait before trying again

#========================= Function to power on the SIM7600X module ====================================
def power_on(power_key):
    print('SIM7600X is starting:') 							 # Print the power-on message

    GPIO.setmode(GPIO.BCM) 									 # Set the GPIO pin numbering mode to BCM
    GPIO.setwarnings(False) 								 # Disable GPIO warnings (optional)
    GPIO.setup(power_key, GPIO.OUT) 						 # Set the power_key GPIO pin as an output
    
    time.sleep(0.1) 										 # Wait for 100ms
    GPIO.output(power_key, GPIO.HIGH) 						 # Set the GPIO pin HIGH (turn on power)
    time.sleep(2) 											 # Wait for 2 seconds to let the SIM7600X power up
    GPIO.output(power_key, GPIO.LOW) 						 # Set the GPIO pin LOW (turn off power)
    time.sleep(5) 											 # Wait for 5 seconds to allow the SIM7600X to initialize
    ser.flushInput() 										 # Clear the serial input buffer
    print('SIM7600X is ready') 								 # Print the ready message

#========================= Function to power down the SIM7600X module ====================================
def power_down(power_key):
    print('SIM7600X is logging off:') 						 # Print the power-down message
    GPIO.output(power_key, GPIO.HIGH) 						 # Set the power_key GPIO pin HIGH (turn on power)
    time.sleep(3) 											 # Wait for 3 seconds
    GPIO.output(power_key, GPIO.LOW) 						 # Set the power_key GPIO pin LOW (turn off power)
    time.sleep(18) 											 # Wait for 18 seconds before completely powering down
    print('Good bye') 										 # Print the shutdown message

#========================= Function to publish data to ThingBoard ===============================
def publish_to_thingboard(latitude, longitude):
    # Construct the JSON payload with GPS data
    payload = {
        "gps_latitude": latitude,
        "gps_longitude": longitude
    }
    
    # Publish the data to ThingBoard
    client.publish("v1/devices/me/telemetry", json.dumps(payload), qos=1)
    print("Data sent to ThingBoard")

#========================= Main program execution ====================================

def main():
    try:
        power_on(power_key) 									 # Power on the SIM7600X
        gps_data = get_gps_position() 							 # Get the GPS position
        if gps_data:
            latitude, longitude = gps_data 					     # Extract latitude and longitude
            publish_to_thingboard(latitude, longitude)			 # Send the data to ThingBoard
        power_down(power_key) 									 # Power down the SIM7600X
    except Exception as e: 										 # If there is an exception (error) during execution
        print(f"Error: {e}") 									 # Print the error message
        if ser != None: 										 # If serial is initialized, close it
            ser.close()
        power_down(power_key) 									 # Ensure the SIM7600X is powered down
        GPIO.cleanup() 											 # Clean up the GPIO pins
    if ser != None:
        ser.close() 											 # Close the serial connection
        GPIO.cleanup() 											 # Clean up GPIO settings

if __name__ == '__main__':
    main() 													     # Run the main function