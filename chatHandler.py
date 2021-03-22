'''
Written by John Gregg - As a hobby to live on.
All Rights Reserved 2019
'''
import os
import sys
import json
import random
import scheduler as sh
import resourceHandler as rh
import debugger as db
from datetime import datetime, timedelta
# use prefix to determine the chat emote prefix


class chatHandler():
	def __init__(self, cooldown = [80,120]):
		self.debugger = db.debugger()

		self.cooldownRange = cooldown
		self.global_cooldown = random.randint(*self.cooldownRange)
		self.lastTriggered = {"time": datetime.utcnow(), "keyword": ""}

		self.keywords = {}
		self.responses = {}

		#self.loadDefaultResponses()
		#self.loadChannelResponses()

	def loadDefaultResponses(self):
		self.loadResponses('data/defaultResponses.json')

	def loadChannelResponses(self):
		try:
			self.loadResponses('data/%s/channelResponses.json'%(self.bot.channel[1:]))
		except TypeError:
			data = {"messageResponse": [], "threshholdResponse": []}
			rh.writeJSON('data/%s/channelResponses.json'%(self.bot.channel[1:]), data)
			self.debugger.log("Writing Default responses JSON.")


	def loadResponses(self, filePointer):
		responseData = rh.readFile(filePointer)
		channelResponses = []
		for threshhold in responseData['threshholdResponse']:
			threshhold["bot"] = self.bot
			channelResponses.append(threshholdResponse(**threshhold))
		for message in responseData['messageResponse']:
			message["bot"] = self.bot
			channelResponses.append(messageResponse(**message))
		self.addResponse(channelResponses)
		self.debugger.log("[cH]Loaded responses, %s messageResponses, %s threshholdResponses."%(len(responseData['messageResponse']), len(responseData['threshholdResponse'])), 3)


			 

	"""
	Checks if any of the keywords are in the message.
	Has a global cooldown on accepting messages.
	Keeps the bot from spamming different emotes.
	"""
	def decode(self, message):
		if (datetime.utcnow()-self.lastTriggered['time']).seconds > self.global_cooldown:
			pulled = []
			for trigger in message['message'].split():
				if trigger not in pulled and trigger in list(self.keywords.keys()):
					self.debugger.log("[chDec]:%s - %s"%(trigger, message), 4)
					pulled.append(trigger)					
					message["keyword"] = trigger
					cmd_reactor = (self.keywords[trigger]).reactor
					response =  cmd_reactor(message)
					if response is not None:						
						self.global_cooldown = random.randint(*self.cooldownRange)
						if self.lastTriggered['keyword'] == trigger:
							response["message"] =  ""
						self.lastTriggered['time'] = datetime.utcnow()
						self.lastTriggered['keyword'] = trigger
						self.debugger.log("[chDec]:%s - %s"%(trigger, message), 1)
						return response
					else:
						pass
			self.debugger.log("[chDec]:%s"%(pulled), 1)
		return None
			

	def addResponse(self, chatResponses):
		if not isinstance(chatResponses, (list,)):
			chatResponses = [chatResponses]
		for chatResponse in chatResponses:
			if self.responses.get(chatResponse.name) is None:
				self.responses[chatResponse.name] = chatResponse
			else:
				self.removeResponse(chatResponse.name)
				self.responses[chatResponse.name] = chatResponse
		self.mapReactors()
		self.debugger.log("[cHaR]%s - %s"%(len(self.keywords), len(self.responses)), 1)

	def removeResponse(self, name):
		resp = self.responses.get(name)
		if resp is not None:
			del self.responses[name]
		self.mapReactors()

	def mapReactors(self):
		self.keywords = {}
		for command in self.responses.keys():
			for keyword in self.responses[command].keywords:
				self.keywords[keyword] = self.responses[command]	

"""
Command Flow: chatHandler.decode -> chatResponse.reactor -> <commandType>.execute -[DOES COMMAND]> Return command outcome ['string'].
responseOpt:
[ 't': 0-2, #TYPE: 0 - One to One, 1 - Spam response, 2 - Chain Response
  'p': 0-1, #Pass Chance
  'ms': 10, #Max Spam - Max Character Length
]
"""
class chatResponse():
	def __init__(self, name, keywords, response, subResponse, min_delay, max_delay, responseOpt):
		self.name = name
		self.keywords = keywords
		self.response = response
		if subResponse == []:
			self.subResponse = self.response
		else:
			self.subResponse = subResponse
		self.min_delay = min_delay
		self.max_delay = max_delay
		self.responseOpt = responseOpt

	def reactor(self, message):		
		return processMessage(message)

	#Specifically for generating a random response based on the responseOpt
	def processMessage(self, message):
		msg_pass = self.responseOpt['p']
		if random.randint(0,100)/100 < msg_pass:
			msg_type = self.responseOpt['t']
			if msg_type == 0:
				msg_spam = 1
			else: 
				msg_spam = random.randint(0, self.responseOpt['ms'])
			mod_message = message
			for i in range(msg_spam-1):
				if random.randint(0,10) < 5:#Place for special spice maybe a crowd voracity?
					mod_message = mod_message + message				
			return mod_message
		else:
			return ""

	#Collects all of the necessary things needed to send a message
	def execute(self):
		randomResponse = random.randint(0, len(self.subResponse))-1
		delay = random.randint(self.min_delay*1000, self.max_delay*1000)/1000
		subMessage = self.processMessage(self.subResponse[randomResponse])

		randomResponse = random.randint(0, len(self.response))-1
		delay = random.randint(self.min_delay*1000, self.max_delay*1000)/1000
		message = self.processMessage(self.response[randomResponse])
		response = {"name": self.name, "delay": delay, "message": message, "subMessage": subMessage}		
		return response




"""
message response:
Sets an exact response for a set of keywords(strings) for it to respond to, every time.

"""
class messageResponse(chatResponse):
	def __init__(self, name, keywords = [], response = [''], subResponse = [], userList = [], min_delay = 0, max_delay = 2, responseOpt = {'t':0, 'p': 1}):
		self.userList = userList
		self.response = response
		super().__init__(name, keywords, response, subResponse, min_delay, max_delay, responseOpt)

	def reactor(self, message):
		if message['display-name'].lower() in self.userList:
			return chatResponse.execute(self)

			
"""
threshhold response:
This is for when the bot will be listening for #<threshhold> messages containing <keywords> per <period> seconds.
It will wait for <cooldown> seconds until it reacts again.
"""
class threshholdResponse(chatResponse):
	def __init__(self, name, keywords = [], response = [''], subResponse = [],  threshhold = 4, period = 2, cooldown = 60, min_delay=0, max_delay=3, responseOpt = {'t':0, 'p': 0.5}):
		self.debugger = db.debugger()

		self.count = 0
		self.period = period
		self.cooldown = cooldown
		self.threshhold = threshhold

		self.lastMessage = ""		
		self.lastCounted = datetime.utcnow()
		self.lastTriggered = datetime.now() + timedelta(seconds=cooldown)
		
		self.taste = []
		super().__init__(name, keywords, response, subResponse, min_delay, max_delay, responseOpt)

		
	def reactor(self, message):
		cooldown = (datetime.utcnow()-self.lastTriggered).seconds < self.cooldown
		if cooldown or (datetime.utcnow()-self.lastCounted).seconds > self.period:
			self.count = 0
			self.lastMessage = ""
		self.count += 1
		self.lastCounted = datetime.utcnow()
		self.lastMessage = message["message"]

		debug = 'Ct %d/%d - St %s/%s' % (self.count, self.threshhold, (datetime.utcnow()-self.lastCounted).seconds, self.period)
		if cooldown:
			debug = debug + " - Cooldown"
		self.debugger.log("[cHthR][%s]:%s" % (self.name[:6], debug), 1)
		if self.count >= self.threshhold:
			self.lastTriggered = datetime.utcnow()			
			return chatResponse.execute(self)
