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
from datetime import datetime, timedelta
# use prefix to determine the chat emote prefix


class chatHandler():
	def __init__(self, bot, cooldown = [20,100]):
		self.bot = bot

		self.debug_threshhold = False
		self.debug_loadResponces = False

		self.cooldownRange = cooldown
		self.global_cooldown = random.randint(*self.cooldownRange)
		self.lastTriggered = datetime.utcnow()

		self.keywords = {}
		self.responces = {}

		self.loadDefaultResponces()
		self.loadChannelResponces()

	def loadDefaultResponces(self):
		self.loadResponces('data/defaultResponces.json')

	def loadChannelResponces(self):
		try:
			self.loadResponces('data/%s/channelResponces.json'%(self.bot.channel[1:]))
		except TypeError:
			data = {"messageResponce": [], "threshholdResponce": []}
			rh.writeJSON('data/%s/channelResponces.json'%(self.bot.channel[1:]), data)
			timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
			print("[%s][%s]Writing Default responces JSON."%(self.bot.channel[1:5], timeInfo))


	def loadResponces(self, filePointer):
		responceData = rh.readFile(filePointer)
		channelResponces = []
		for threshhold in responceData['threshholdResponce']:
			threshhold["bot"] = self.bot
			channelResponces.append(threshholdResponce(**threshhold))
		for message in responceData['messageResponce']:
			message["bot"] = self.bot
			channelResponces.append(messageResponce(**message))
		self.addResponce(channelResponces)
		if self.debug_loadResponces:
			timeInfo = datetime.utcnow().strftime('%H:%M:%S')
			debug = '[Load Resp.][%s][%s]:' % (timeInfo, self.bot.channel[1:])
			print('%sLoaded responces, %s messageResponces, %s threshholdResponces.' % (debug, len(responceData['messageResponce']), len(responceData['threshholdResponce'])))

	"""
	Checks if any of the keywords are in the message.
	Has a global cooldown on accepting messages.
	Keeps the bot from spamming different emotes.
	"""
	def decode(self, message):
		if (datetime.utcnow()-self.lastTriggered).seconds > self.global_cooldown:
			for trigger in list(self.keywords.keys()):
				if all(words in message['message'].split() for words in trigger.split(' ')):
					cmd_reactor = self.keywords[trigger]
					message["keyword"] = trigger
					responce =  cmd_reactor(message)
					if responce is not None:
						self.lastTriggered = datetime.utcnow()
						self.global_cooldown = random.randint(*self.cooldownRange)
					return responce
			

	def addResponce(self, chatResponces):
		if not isinstance(chatResponces, (list,)):
			chatResponces = [chatResponces]
		for chatResponce in chatResponces:
			if self.responces.get(chatResponce.name) is None:
				self.responces[chatResponce.name] = chatResponce
			else:
				self.removeResponce(chatResponce.name)
				self.responces[chatResponce.name] = chatResponce
		self.mapReactors()

	def removeResponce(self, name):
		resp = self.responces.get(name)
		if resp is not None:
			del self.responces[name]
		self.mapReactors()

	def mapReactors(self):
		self.keywords = {}
		for command in self.responces.keys():
			for keyword in self.responces[command].keywords:
				self.keywords[keyword] = self.responces[command].reactor	

"""
Command Flow: chatHandler.decode -> chatResponce.reactor -> <commandType>.execute -[DOES COMMAND]> Return command outcome ['string'].
responceOpt:
[ 't': 0-2, #TYPE: 0 - One to One, 1 - Spam Responce, 2 - Chain Response
  'p': 0-1, #Pass Chance
  'ms': 10, #Max Spam - Max Character Length
]
"""
class chatResponce():
	def __init__(self, bot, name, keywords, responce, subResponce, min_delay, max_delay, responceOpt):
		self.bot = bot
		self.name = name
		self.keywords = keywords
		self.responce = responce
		if subResponce == []:
			self.subResponce = self.responce
		else:
			self.subResponce = subResponce
		self.min_delay = min_delay
		self.max_delay = max_delay
		self.responceOpt = responceOpt

	def reactor(self, message):		
		return processMessage(message)

	def processMessage(self, message):
		msg_pass = self.responceOpt['p']
		if random.randint(0,100)/100 < msg_pass:
			msg_type = self.responceOpt['t']
			if msg_type == 0:
				msg_spam = 1
			else: 
				msg_spam = random.randint(0, self.responceOpt['ms'])
			mod_message = message
			for i in range(msg_spam-1):
				if random.randint(0,10) < 5:#Place for special spice maybe a crowd voracity?
					mod_message = mod_message + message				
			return mod_message
		else:
			return ""


	def execute(self, responceList, flavor="", aftertaste=""):
		randomResponse = random.randint(0, len(responceList))-1
		delay = random.randint(self.min_delay*1000, self.max_delay*1000)/1000
		responceList[randomResponse] = flavor + responceList[randomResponse] + aftertaste
		message = self.processMessage(responceList[randomResponse])
		bcEvent = sh.broadcastEvent(bot = self.bot, name=self.name, message=message, freq=delay)
		self.bot.eventScheduler.addEvent(bcEvent)
		#return 'Responce scheduled %s. Sent: "%s"' %(self.name, responceList[randomResponse])
		timeInfo = datetime.utcnow().strftime("%H:%M:%S - %y/%m/%d")
		self.bot.mqtt.attr_updater("Response", ["Name", self.name], ["Delay", delay], ["Message", message], ["Timestamp", timeInfo])
		return '[%s][%s] %s' %(self.name, delay, message)




"""
message Responce:
Sets an exact responce for a set of keywords(strings) for it to respond to, every time.

"""
class messageResponce(chatResponce):
	def __init__(self, bot, name, keywords = [], responce = [''], subResponce = [], userList = [], min_delay = 0, max_delay = 2, responceOpt = {'t':0, 'p': 1}):
		self.userList = userList
		self.responce = responce
		super().__init__(bot, name, keywords, responce, subResponce, min_delay, max_delay, responceOpt)

	def reactor(self, message):
		if message['display-name'].lower() in self.userList:
			if self.bot.subscriber:
				responceList = self.subResponce
			else:
				responceList = self.responce
			return chatResponce.execute(self, responceList)
			


"""
threshhold Responce:
This is for when the bot will be listening for #<threshhold> messages containing <keywords> per <period> seconds.
It will wait for <cooldown> seconds until it reacts again.
"""
class threshholdResponce(chatResponce):
	def __init__(self, bot, name, keywords = [], responce = [''], subResponce = [],  threshhold = 4, period = 2, cooldown = 60, min_delay=0, max_delay=3, responceOpt = {'t':0, 'p': 0.5}, flavor = [], aftertaste = []):
		self.count = 0
		self.period = period
		self.cooldown = cooldown
		self.threshhold = threshhold
		
		self.flavor = flavor
		self.aftertaste = aftertaste

		self.lastMessage = ""		
		self.lastCounted = datetime.utcnow()
		self.lastTriggered = datetime.now() + timedelta(seconds=cooldown)
		super().__init__(bot, name, keywords, responce, subResponce, min_delay, max_delay, responceOpt) 
		
	def reactor(self, message):
		if (datetime.utcnow()-self.lastTriggered).seconds < self.cooldown or (datetime.utcnow()-self.lastCounted).seconds > self.period:
			self.count = 0
			self.lastMessage = ""
		self.count += 1
		self.lastCounted = datetime.utcnow()
		self.lastMessage = message["message"]

		if self.bot.chatHandler.debug_threshhold:
			timeInfo = datetime.utcnow().strftime('%H:%M:%S')
			debug = '[Thresh. Resp.][%s][%s]:Count %d/%d - Streak-time %s/%s' % (timeInfo, self.name, self.count, self.threshhold, (datetime.utcnow()-self.lastCounted).seconds, self.period)
			if (datetime.utcnow()-self.lastTriggered).seconds <  self.cooldown:
				debug = debug + " - Cooldown"
			print(debug)

		if self.count >= self.threshhold:
			self.lastTriggered = datetime.utcnow()
			if self.bot.subscriber:
				responceList = self.subResponce
			else:
				responceList = self.responce
			return chatResponce.execute(self, responceList)
