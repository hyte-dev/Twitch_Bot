import json
import secrets
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta



class mqttHandler():
	def __init__(self, username, channel):
		self.live = False
		self.attributes = {
						"Bot": {"Username": username , "Channel": channel, "Subscribed": False, "Connection": "Disconnected"}, 
						"Response":{}, 
						"Stats":{}, 
						"Debug":{}
						}
		self.attr_out = {}         
		self.host = "localhost"
		self.channel = channel
		self.username = username
		self.base_topic = "twitch_bot/%s" % (username)

		self.client = mqtt.Client(client_id="Twitch_bot", clean_session=True)
		self.client.username_pw_set(secrets.MQTT_USERNAME, password=secrets.MQTT_PASSWORD)
		self.client.will_set(self.base_topic + "/lwt", payload="offline", qos=0, retain=False)

		self.client.connect(self.host, port=1883, keepalive=9999)	
		self.client.publish(self.base_topic + "/lwt", payload="online", qos=0, retain=False)

		
	def attr_updater(self, heading, *args):
		for arg in args:
			self.attributes[heading][arg[0]] = arg[1];
		self.attr_out = {}
		for key in self.attributes.keys():
			self.attr_out = {**self.attr_out, **self.attributes[key]}
		self.update()	
		
	def update(self):		
		self.client.publish(self.base_topic + "/lwt", payload="online", qos=0, retain=False)
		self.client.publish(self.base_topic + "/stat", payload=('on' if self.live else 'off'), qos=0, retain=False)
		self.client.publish(self.base_topic + "/attr", payload=json.dumps(self.attr_out), qos=0, retain=False)


def main():
	usage = "Usage - python3 mqttHandler.py"
	
	mqtt = mqttHandler("cohhcarnage")
	mqtt.status_updater("Stats", ["Activity", "Live"], ["Joined", "Now"])

if __name__ == "__main__":
	main()
