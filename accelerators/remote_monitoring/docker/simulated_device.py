#!/usr/bin/python

# Simulates device data
# Make sure your regions and cert files are in the cert directory

import sys
import ssl
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import json
import random
import time

#Get the region
fileptr = open("./certs/region.txt", "r")

region = fileptr.read()

endpoint = "data.iot."+region

print "Endpoint :" + endpoint

#Setup our MQTT client and security certificates

mqttc = AWSIoTMQTTClient("1234")

#Make sure you use the correct region!
mqttc.configureEndpoint(endpoint,8883)
mqttc.configureCredentials("./certs/rootCA.pem","./certs/privateKey.pem","./certs/certificate.pem")

#Function to encode a payload into JSON
def json_encode(string):
        return json.dumps(string)

mqttc.json_encode=json_encode

#This sends our test message to the iot topic
def send():
#Declaring our variables
    message ={
        "deviceType": "RM_Accelerator",
        "deviceID": "AWS98765",
        'deviceData': random.randint(1, 4098)
    }    
    #Encoding into JSON
    message = mqttc.json_encode(message)
    mqttc.publish("remote_monitoring", message, 0)
    print "Message Published " + message

#Connect to the gatewaydevice
mqttc.connect()
print "Connected"

#Loop until terminatedcertifi
while True:
    send()
    time.sleep(5)

mqttc.disconnect()
