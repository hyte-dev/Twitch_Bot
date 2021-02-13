'''
Written by John Gregg - As a hobby to live on.
All Rights Reserved 2019
'''
import os
import sys
import json

class commandHandler():
	def __init__(self, bot):
		self.bot = bot
		self.keywords = {}
		self.commandList = [displayChatCommand(self.bot),
							disconnectCommand(self.bot),
							broadcastCommand(self.bot),
							schedulerCommand(self.bot),
							autoSaveCommand(self.bot),
							respondCommand(self.bot),
							reloadCommand(self.bot),
							exitCommand(self.bot)
							]

		if self.bot.ai is not None:
			self.commandList.append(generateTextCommand(self.bot))

		for command in self.commandList:
			for keyword in command.keywords:
				self.keywords[keyword] = command.permissionCheck	

	def decode(self, cmd, permission):
		cmd = cmd.split(' ')
		if cmd[0].lower() in ['list', 'help']:
			commands = ""
			for command in self.commandList:
					commands += "| %s " % (command.usage)
			return 'For additional Help Contact Admin:[%s]' %(commands[1:])

		elif cmd[0].lower() in self.keywords.keys():
			cmd_permissionCheck = self.keywords[cmd[0].lower()]
			return cmd_permissionCheck(cmd, permission)
		else:
			return "Invalid Command."

"""
Command Flow: commandHandler.decode -> command.permissionCheck -> <commandType>.execute -> Return command outcome ['string'].
"""
class command():
	def __init__(self, bot, keywords, usage, minPerm):
		self.bot = bot
		self.keywords = keywords
		self.minPerm = minPerm
		self.usage = usage
		self.connection = None

	def permissionCheck(self, cmd, permission):
		if permission <= self.minPerm:
			try:
				return self.executor(cmd, permission)
			except IndexError as error:
				return "Invalid syntax. %s" % self.usage
		else:
			return "Insufficent Permissions."

	def executor(self, c, cmd, permission):
		return "TODO Command"

"""
Disconnect Command:
Closed the bot entirely. The bot from the server, saves data, and ends process.
"""
class exitCommand(command):
	def __init__(self, bot):
		keywords = ['exit', 'quit']
		usage = "Usage: /[exit|quit]"
		minPerm = 0
		super().__init__(bot, keywords, usage, minPerm)

	def executor(self, cmd, permission):
		self.bot.exit()
		return "Disconnecting Bot..."

"""
Disconnect Command:
Disconnects the bot from the server, saves data, and ends process.
"""
class disconnectCommand(command):
	def __init__(self, bot):
		keywords = ['dc', 'disconnect']
		usage = "Usage: /[disconnect]"
		minPerm = 0
		super().__init__(bot, keywords, usage, minPerm)

	def executor(self, cmd, permission):
		self.bot.send_disconnect()
		return "Disconnected from %s." % (self.bot.channel)



"""
Save Command:
Exports data when called. Doesn't affect autosave freq
"""
class autoSaveCommand(command):
	def __init__(self, bot):
		keywords = ['autosave', 'save']
		usage = "Usage: /autoSave [now|freq] [args]"
		minPerm = 1
		super().__init__(bot, keywords, usage, minPerm)

	def executor(self, cmd, permission):	
		if permission == 0:
			if cmd[1].lower() in ['freq']:
				return self.bot.backupBroker.changeFrequency(cmd[2])
		
		if cmd[1].lower() in ['now', 'instant']:
			self.bot.backupBroker.backup()
			return "Save Succuessful."

"""
Reload Command:
Reloads data members of the bot. Eg permission list, emoji data.
"""
class reloadCommand(command):
	def __init__(self, bot):
		keywords = ['reload']
		usage = "Usage: /reload [backup Item Name]"
		minPerm = 0
		super().__init__(bot, keywords, usage, minPerm)

	def executor(self, cmd, permission):	
		if cmd[1] in ['permissionList', 'PL', 'permL']:
			self.bot.loadUserPermissions()
			return "Reloaded User Permission List."
		elif cmd[1] in ['responceLists', 'respList', 'RL']:
			self.bot.chatHandler.loadDefaultResponces()
			self.bot.chatHandler.loadChannelResponces()
			return "Reloaded entire Responce lists from file."
		else:
			return "ERROR: Cannot Reload that Property."

"""
Generate Command:
Generated text from the trained DNN
"""
class generateTextCommand(command):
	def __init__(self, bot):
		keywords = ['generate', 'g']
		usage = "Usage: /generate [temperature] [c|t]"
		minPerm = 99
		self.confirm = ""
		super().__init__(bot, keywords, usage, minPerm)

	def executor(self, cmd, permission):
		if cmd[1].lower() in ['c', 'conf', 'confirm']:
			selection = int(cmd[2])
			if selection in range(0, len(self.confirm)):
				self.bot.send_pubmsg(self.confirm[selection])
				return 'Message %d confirmed.' %(selection)
			else:
				return "Invalid selection. Select one between [1-%d]"%(len(self.confirm))
		try:
			temperature = float(cmd[1])
			if cmd[2].lower() in ['t', 'true']:
				generatedText = self.bot.ai.generateMessage(temp=temperature)[0]
				self.bot.send_pubmsg(generatedText)
			elif cmd[2].lower() in ['c', 'conf', 'confirm']:
				generatedText = self.bot.ai.generateMessage(temp=temperature, n=3)
				self.confirm = generatedText
				temp = []
				for indx, text in enumerate(generatedText):
					temp.append('%s: %s'%(indx, text))
				generatedText = 'Select One: %s'%(' - '.join(temp))
			return generatedText
		except ValueError:
			return "Invalid Temperature, expected [0.1 - 1.2]."

"""
Respond Command:
Sets flag if the bot will respond with a generated message or not.
"""
class respondCommand(command):
	def __init__(self, bot):
		keywords = ['respond']
		usage = "Usage: /respond [t|f]"
		minPerm = 0
		super().__init__(bot, keywords, usage, minPerm)

	def executor(self, cmd, permission):
		if cmd[1].lower() in ['t', 'true']:
			self.bot.respondToUsers = True
			return "Chat bot will respond to users."
		else:
			self.bot.respondToUsers = False
			return 'Chat bot will NOT respond to users.'
		return msg


"""
Display Chat Command:
Sets flag if the bot will/wont display each flag.
"""
class displayChatCommand(command):
	def __init__(self, bot):
		keywords = ['d' ,'disp', 'display']
		self.validLevels = ['pub_chat', 'log_event', 'debug_privmsg', 'debug_pubmsg', 'log_command', 'backupBroker.debug_backup', 'backupBroker.debug_loadHist', 'chatHandler.debug_threshhold', 'chatHandler.debug_loadChannelResponces']
		minPerm = 0
		usage = "Usage: /display [log level] [t|f] Log Levels:[%s]" % (', '.join(self.validLevels))
		super().__init__(bot, keywords, usage, minPerm)

	def executor(self, cmd, permission):
		if cmd[1] in self.validLevels:
			if cmd[2].lower() in ['t', 'true']:
				dictDiveSet(self.bot, cmd[1], True)
				return "Bot will display: %s" % (cmd[1])
			else:
				dictDiveSet(self.bot, cmd[1], False)
				return "Bot will NOT display: %s" % (cmd[1])
		else:
			if cmd[1].lower() in ['s', 'status']:
				status = ""
				for level in self.validLevels:
					status += "| %s:%s " % (level, dictDiveGet(self.bot, level))
				return 'Status:[%s]' %(status[2:])
			else:
				return "Invalid Level. %s" %(self.usage)

"""
broadcase Command:
Makes the bot say what you'd like!
"""
class broadcastCommand(command):
	def __init__(self, bot):
		keywords = ['broadcast', 'b']
		usage = "Usage: /broadcast [message]"
		minPerm = 0
		super().__init__(bot, keywords, usage, minPerm)
		
	def executor(self, cmd, permission):
		msg =' '.join(cmd[1:])
		self.bot.send_pubmsg(msg)
		return "Broadcasting message."

"""
schedular Command:
Currently just to see status of the schedular queue

"""
class schedulerCommand(command):
	def __init__(self, bot):
		keywords = ['sch', 'sched', 'schedular']
		usage = "Usage: /scheduler [add|remove] [name] [seconds] [message] [r]"
		minPerm = 0
		super().__init__(bot, keywords, usage, minPerm)
		
	def executor(self, cmd, permission):
		if cmd[1].lower() in ['s', 'status']:
			currentEvents = ', '.join(list(self.bot.eventScheduler.events.keys()))
			return 'Status:[%s]' %(currentEvents)
		else:
			return "Invalid Level. %s" %(self.usage)



"""
permission Command:
Changes Permissions for bot internals interraction.
Useful For QOL if others need to be able to interact with the bot on my behalf
"""
class permissionCommand(command):
	def __init__(self, bot):
		keywords = ['permission']
		usage = "Usage: /permission [give|take|request] [args]"
		minPerm = 99
		super().__init__(bot, keywords, usage, minPerm)


"""
============================================================

					Helpers

============================================================
"""

#Decodes a string into an objectFilePath, and sets that objets value
def dictDiveSet(rootObj, structure, value):
	obj = rootObj
	dives = structure.split('.')
	for dive in dives:
		if dives.index(dive) != len(dives)-1:
			obj = getattr(obj, dive)
		else:
			setattr(obj, dive, value)
	return obj

#Gets value from a string FilePath
def dictDiveGet(rootObj, structure):
	obj = rootObj
	dives = structure.split('.')
	for dive in dives:
		obj = getattr(obj, dive)
	return obj