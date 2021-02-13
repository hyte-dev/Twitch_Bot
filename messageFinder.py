import traceback
import resourceHandler as rh
from datetime import datetime, timedelta

def matches(message):
	match = False
	startTime = 1560773000
	endTime   = 1560775000
	keywords = ['queue', 'hello']

	window = range(startTime*1000, endTime*1000)
	if(int(message['tmi-sent-ts']) in window):		
		for word in keywords:
			if(word.lower() in message['message'].lower()):
				match = True
				break
	return match

filepath ='data/cohhcarnage/messageData/messageData_06-17-19.json'
data = rh.readFile(filepath)
for message in data:
	try:
		if matches(message):
			formattedMessage = "[%s]%s:%s"%(datetime.utcfromtimestamp(int(message['tmi-sent-ts'])/1000).strftime('%H:%M:%S'), message['display-name'], message['message'])
			print(formattedMessage)
	except KeyError:
			pass
	except:
		print(traceback.format_exc())
		break
