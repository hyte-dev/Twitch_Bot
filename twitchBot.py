'''
Written by John Gregg - As a hobby to live on.
All Rights Reserved 2019
'''
import sys
import irc.bot
import secrets
import requests
import threading
import scheduler as sh
import backupBroker as bb
import mqttHandler as mqtt
import chatHandler as chatH
import commandHandler as commH
import resourceHandler as rh
from random import randint
from datetime import datetime, timedelta
from time import strftime, strptime

class TwitchBot(irc.bot.SingleServerIRCBot):
	def __init__(self, username, channel, token):
		self.username = username
		self.client_id =  secrets.CHAT_CLIENT_ID
		self.channel = '#' + channel
		self.token = token
		self.subscriber = False
		
		#debug display options 
		#--SYSTEM STILL LOGS--
		self.pub_chat = False
		self.privchat = False
		self.log_event = True
		self.log_command = True
		self.debug = False

		self.live = False
		self.chatOutput = True
		self.permissions = {}
		
		self.mqtt = mqtt.mqttHandler(username, channel)

		#Data structures for each tracked variable
		#format packs them all up to be ready for the broker.
		self.backup = {}
		self.commandLog = []
		self.messageData = []
		self.eventLog = []
		self.emoteUsageData = {}
		self.formatBackup()

		
		#Setting up the DNN to come up with responces.
		self.ai = None
		#try:
		#	import chatAI as cAI
		#	self.ai = cAI.chatAI('data/%s/AI/textgenrnn_weights.hdf5'%channel)
		#	print("Ai Trained for this chat.")
		#except:
		#	print("No AI trained for %s." %self.channel)
		
		self.eventScheduler = sh.scheduler(self)
		self.loadShedule('data/%s/schedule.json'%channel)

		#Sets up the backupManager, sync's with any data currently for today
		self.backupBroker = bb.backupBroker(channel, self.backup, self.dataCallback)
		self.eventScheduler.addEvent(sh.backupEvent(self, 600, self.backupBroker.backup))
		self.loadHistoricData()

		self.loadUserPermissions('data/permissionList.json')
		self.commandHandler = commH.commandHandler(self)
		self.chatHandler = chatH.chatHandler(self)
		
		#Functions to be called on each public message sent.
		#This is where you add ALL things that process messages.
		self.processingTasks = [self.logEmotes]
		
		server = 'irc.chat.twitch.tv'
		port = 6667
		print('[%s]Connecting to %s on port %s...'%(self.channel[1:5], server, port))
		irc.bot.SingleServerIRCBot.__init__(self, [(server, port, 'oauth:' +self.token)], self.username, self.username)

	"""
	============================================================

							REACTORS
						
	============================================================
	"""
	def on_welcome(self, c, e):
		self.connection = c
		timeInfo = datetime.utcnow().strftime("%H:%M:%S on %d/%m/%y")
		print('[%s]Connected to Twitch at %s.' % (self.channel[1:5], timeInfo))
		# You must request specific capabilities before you can use them
		c.cap('REQ', ':twitch.tv/membership')
		c.cap('REQ', ':twitch.tv/tags')
		c.cap('REQ', ':twitch.tv/commands')		
		self.send_join()			

	def on_join(self, c, e):
		self.connection = c
		self.live = True
		self.mqtt.live = True
		timeInfo = datetime.utcnow().strftime("%H:%M:%S on %d/%m/%y")
		self.mqtt.attr_updater("Bot", ["Connection", "Live"], ["Timestamp", timeInfo])
		print('[%s]Connected to %s at %s.' % (self.channel[1:5], e.target, timeInfo))

	#Channel Events (Subs/Bombs/Bits Etc)
	def on_usernotice(self, c, e):
		self.connection = c
		msgData = self.structureNotice(e)
		if self.debug:
			timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
			eventlog = "[USERNOTICE][%s]:%s"%(timeInfo, msgData)
			self.mqtt.attr_updater("Debug", ["USERNOTICE", eventlog])
			print(eventlog)

	#When you join a channel it will send a userstate. (https://dev.twitch.tv/docs/irc/tags/ for full info).
	def on_userstate(self, c, e):
		self.connection = c
		msgData = self.structureNotice(e)
		self.subscriber = (msgData['subscriber'] == '1')
		now = datetime.utcnow().strftime("%H:%M:%S on %d/%m/%y")
		info = 'Not Subscribed.'
		if 'badge-info' in msgData.keys() and not msgData['badge-info'] is None:
			info = "%s %s" %(msgData['badge-info'].split('/')[1], "- Active")
		self.mqtt.attr_updater("Bot", ["Subscribed", info], ["Timestamp", now])
		if self.debug:
			timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
			eventlog = "[USERSTATE][%s]:%s"%(timeInfo, msgData)
			self.mqtt.attr_updater("Debug", ["USERSTATE", eventlog])
			print(eventlog)

	def on_pubmsg(self, c, e):
		self.connection = c
		msgData = self.structureMessage(e)
		for process in self.processingTasks:
			process(msgData)
		if self.pub_chat:
			print(self.formatMessage(msgData))

		#2 different behaviors:
		# When someone @'s the bot itll respond with a generated message.
		# It will generate ChatEvents based on flow and content of messages (see chatHandler.py)
		if self.chatOutput:
			responce = ""
			if False and self.username.lower() in msgData['message'].lower():
				if self.ai is not None:
					responce = self.ai.generateMessage(0.3)[0]
				responce = '@%s %s' % (msgData['display-name'], responce)
				self.send_pubmsg(responce)
			else:
				responce = self.chatHandler.decode(msgData)
				if responce is not None:
					timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
					eventlog = "[%s][Resp][%s]:%s - Cooldown %ss"%(self.channel[1:5], timeInfo, responce, self.chatHandler.global_cooldown)
					self.eventLog.append(eventlog)
					timeInfo = datetime.utcnow().strftime("%H:%M:%S - %y/%m/%d")
					self.mqtt.attr_updater("Response", ["Cooldown", self.chatHandler.global_cooldown], ["Timestamp", timeInfo])
					if self.log_event:
						print(eventlog)

	"""
	{'type': whisper,
	 'source': From,
	 'target': To, 
	 'arguments': Messages,
	 'tags': [0:{badges, value},
			  1:{color, value},
			  2:{display-name, value},
			  3:{emotes, value},
			  4:{message-id, value},
			  5:{thread-id, value},
			  6:{turbo, value},
			  7:{user-id, value},
			  8:{user-type, value}]
	}
	"""    
	def on_whisper(self, c, e):
		self.connection = c
		msg = self.structureMessage(e)
		timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
		if msg['message'][0] == "/":
			cmdLog = "[COMMAND][%s][%s]:%s"%(timeInfo, msg['display-name'], msg['message'])
			#Checks commands and permissions
			if msg['source'] in self.permissions.keys():
				cmdResponse = self.commandHandler.decode(msg['message'][1:], self.permissions[msg['source']])
				cmdLog = "%s - %s"%(cmdLog, cmdResponse)
				self.send_whisper(msg['source'][:msg['source'].find('!')], cmdResponse)
			else:
				cmdLog = "%s - ERROR: No command permissions."%(cmdLog)
			self.commandLog.append(cmdLog)
			if self.log_command:
				print(cmdLog)
		else:
			if self.privchat:
				print("[Whisper][%s][%s]:%s"%(timeInfo, msg['display-name'], msg['message']))



	"""
	============================================================

						SEND COMMANDS

	============================================================
	"""
	
	def send_pubmsg(self, msg):
		timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
		sendString = "PRIVMSG %s :%s"%(self.channel, msg)
		if self.debug:
			print("[%s][PUBMSG]>%s"%(timeInfo, msg))
		self.connection.send_raw(sendString)

	def send_whisper(self, target, msg):
		timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
		sendString = "PRIVMSG %s :/w %s %s"%(self.channel, target, msg)
		if self.debug:
			print("[%s][WHISPER]>%s"%(timeInfo, sendString))
		self.connection.send_raw(sendString)

	def send_disconnect(self):
		if self.debug:
			timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]		
			print("[send_disconnect][%s]:%s"%(timeInfo, self.live))
		if self.live:
			self.connection.part(self.channel)
			now = datetime.utcnow().strftime("%H:%M:%S on %d/%m/%y")
			print("Disconnected from %s's channel at %s." %(self.channel, now))
			self.live = False
			self.mqtt.live = False
			self.mqtt.attr_updater("Bot", ["Connection", "Disconnected"], ["Timestamp", now])

	def send_join(self):
		if self.debug:
			timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]	
			print("[send_join][%s]:%s"%(timeInfo, self.live))
		if not self.live:
			print('[%s]Joining %s as %s...' % (self.channel[1:5], self.channel, self.connection.ircname))
			self.connection.join(self.channel)

	"""
	============================================================

						Bot Functions

	============================================================
	EmoteStructure: [E]/[ID]:[pos][,[pos]]
	Emotes events are separated by '/', each instance is spearated by ','.
	"""
	def logEmotes(self, message):
		if message['emotes']:
			for emote in message['emotes'].split('/'):
				emote = emote.split(':')
				emoteID = emote[0]
				numEmotes = len(emote[1].split(','))
				emoteEvent = [int(datetime.utcnow().timestamp()), emoteID, numEmotes]
				try:
					(self.emoteUsageData[emoteID]).append(emoteEvent)
				except:
					self.emoteUsageData[emoteID] = [emoteEvent]
	

	"""
	Consolidates the data into an easy list for the backup broker to output.
	Resets at the end of every day.
	Known Issue: will cut off the last backup chat, depending on when it last backed up
	"""
	def dataCallback(self):
		tdelta = int(datetime.utcnow().strftime('%H')) - int(self.backupBroker.lastBackup.strftime('%H'))
		if tdelta < 0:
			del self.emoteUsageData
			del self.messageData
			self.emoteUsageData = {}
			self.messageData = []
		self.formatBackup()        
		return self.backup.copy()

	def formatBackup(self):
		del self.backup
		backupTime = datetime.utcnow().strftime("%m-%d-%y")
		self.backup = {'commandLog': [self.commandLog, 'data/commandLog.json'],
					   'eventLog': [self.eventLog, 'data/eventLog.json'],
					   'messageData': [self.messageData, 'data/%s/messageData/messageData_%s.json'%(self.channel[1:], backupTime)],
					   'emoteUsageData': [self.emoteUsageData, 'data/%s/emoteUsageData/emoteUsageData_%s.json'%(self.channel[1:], backupTime)]
					   }
		self.mqtt.attr_updater("Stats", ["Events", len(self.eventLog)], ["Emotes", len(self.emoteUsageData)], ["Messages", len(self.messageData)], ["Commands", len(self.commandLog)])
		


	"""
	============================================================

							UTILITIES
						
	============================================================
	Public/Private Message Structure:
	{'message': [String], 
	 'badges': None, 
	 'color': [Color of Name in Chat], 
	 'display-name': [String Display Name], 
	 'emotes': [Unique Emote ID Structure], 
	 'flags': None, 
	 'id': [Unique Message ID], 
	 'mod': [If Mod 0-2], 
	 'room-id': [Unique ID for the room], 
	 'subscriber': [Sub teir 0-3], [Prime, Paid, T2, T3] 
	 'tmi-sent-ts': [Time in milliseconds], 
	 'turbo': '0', 
	 'user-id': [Unique User ID], 
	 'user-type': None
	}
	"""
	def structureMessage(self, message):
		msgInfo = {}
		msgInfo["message"] = message.arguments[0]
		msgInfo["source"] = message.source
		for tag in message.tags:
			msgInfo[tag['key']] = tag['value']
		self.messageData.append(msgInfo)
		return msgInfo


	def structureNotice(self, message):
		msgInfo = {}
		for tag in message.tags:
			msgInfo[tag['key']] = tag['value']
		return msgInfo

	#formats the command line output.
	def formatMessage(self, message):
		localInfo = "[%s][%s]"%(self.channel[:5], datetime.utcfromtimestamp(int(message['tmi-sent-ts'])/1000).strftime('%H:%M:%S'))
		tags = ""
		if(message['mod']=='1'):
			tags += "[M]"
		if(message['subscriber']=='1'):
			tags += "[%sS]"%((message['badges'].split(','))[0].split('/')[1] +"-")
		
		return "%s[%s]%s:%s"%(localInfo, message['display-name'], tags, message['message'])


	"""
	Loads a schedule for the bot to connect and disconnect on.
	Times are UTC-0 and in 24hr notation
	<time> = HHMMSS
	example schedule file = {"connect":["<time>"], "disconnect":["<time>"]}
	Bug to check

	"""
	def loadShedule(self, filename):
		try:
			schedule = rh.readFile(filename)
			connectTimes = schedule['connect']
			disconnectTimes = schedule['disconnect']
			self.eventScheduler.closeAllNamedEvents('connect')
			self.eventScheduler.closeAllNamedEvents('disconnect')

			self.minDiff = -12
			self.minMinuite = 60
			self.minSecond = 60
			for conTime in connectTimes:
				ret, eventTime = self.processTime(conTime)
				if ret:
					self.live = False
					self.mqtt.live = False			
				connectionEvent = sh.functionEvent(self, 'connect_%s'%(connectTimes.index(conTime)), self.send_join, eventTime, True)
				self.eventScheduler.addEvent(connectionEvent)
			for dcTime in disconnectTimes:
				ret, eventTime = self.processTime(dcTime)
				if ret:
					self.live = True
					self.mqtt.live = True		
				dcEvent = sh.functionEvent(self, 'disconnect_%s'%(disconnectTimes.index(dcTime)), self.send_disconnect, eventTime, True)
				self.eventScheduler.addEvent(dcEvent)
		except KeyError:
			if self.debug:
				timeInfo = (datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1)
				print("[Scheduler][%s][ERROR] Corrupted Schedule. Schedule not loaded."%(timeInfo))
		except TypeError:
			if self.debug:
				timeInfo = (datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1)
				print("[Scheduler][%s][ERROR] Schedule Not Found."%(timeInfo,))


	#Processes the timeString and does a few checks on it
	def processTime(self, timeString):
		currentHour = datetime.utcnow().hour
		hour = int(timeString[:2])
		minute = int(timeString[2:4])
		second = int(timeString[4:])
		eventTime = datetime.utcnow().replace(hour=hour, minute=minute, second=second)
		ifMin = False
		#Checks to see the hour differential is the minimum (Less than 0).
		diff = hour - currentHour
		if diff >= self.minDiff and diff <= 0:
			if self.minMinuite >= minute:
				self.minDiff = diff
				self.minMinuite = minute
				self.minSecond = second
				ifMin = True
		#Checking if The start time already happened today. 
		#Eg. Bot is started at 12pm. Connect scheduled 8am will be set for Tomorrow at 8 Am 
		if (eventTime - datetime.utcnow()).days < 0:
			eventTime = eventTime + timedelta(seconds=86400)
		if self.debug:
			timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
			print("[Processes Time][%s][EVENT:%s]:%s<=%s=%s-%s - %s"%(timeInfo, eventTime.strftime('%d - %H:%M:%S'), self.minDiff, diff, hour, currentHour, ifMin))
		return ifMin, eventTime

	def loadUserPermissions(self, filename):
		self.permissions = rh.readFile(filename)

	def loadHistoricData(self):
		data = self.backupBroker.loadHistoricData()
		for key in data.keys():
			if len(data[key]) > 0:
				setattr(self, key, data[key])
				if self.debug:
					print("Historic data %s loaded. %s entries."%(key, len(data[key])))
		self.formatBackup()

	def exit(self):
		self.eventScheduler.closeAllEvents()
		timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
		print("[EXIT][%s][%s] Closing connections and threads."%(timeInfo, self.channel))
		self.die(msg="")


def main():
	#if len(sys.argv[1:]) != 3: 
	#	print("Usage - py twitchBot.py -u [username] -t [token] -c [channels]")
	#	quit()

	args = sys.argv[1:]
	state = 0
	username = ''
	token = ''
	channels = []
	maps = {'-u':1, '-t':2, '-c':3 }
	for arg in args:
		try:
			state = maps[arg]
		except:		
			if state == 1:
				username = arg
			elif state == 2:
				token = arg
			elif state == 3:
				channels.append(arg)
	threads = {}
	for channel in channels:
		bot = TwitchBot(username, channel, token)
		threads[channel] = threading.Thread(target=bot.start)
		threads[channel].start()
		

if __name__ == "__main__":
	main()
