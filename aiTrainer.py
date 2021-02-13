'''
Written by John Gregg - As a hobby to live on.
All Rights Reserved 2019
'''
import sys
import random
import resourceHandler as rh
from datetime import datetime

"""
Message Structure:
{'message': [String], 
 'badges': None, 
 'color': [Color of Name in Chat], 
 'display-name': [String Display Name], 
 'emotes': [Unique Emote ID Structure], 
 'flags': None, 
 'id': [Unique Message ID], 
 'mod': [If Mod 0-2], 
 'room-id': [Unique ID for the room], 
 'subscriber': [Sub teir 0-3], [None, T1, T2, T3] 
 'tmi-sent-ts': [Time in milliseconds], 
 'turbo': '0', 
 'user-id': [Unique User ID], 
 'user-type': None
}
Current Filters:
No Mod
No All Caps
No msg longer that N char
No msg less than N words.
No commands '![command]'
Banned words.
-no Links, no Questions, no @'s
"""
class aiTrainer():
	def __init__(self):
		self.userList = {}
		self.wordBlackList = rh.readCSV("data/bannedWordsList.txt")
		self.processedMessages = {'passed': [], 'failed': [], 'badWord': [], 'modReply': [], '@messages': [], 'notMessages': []}

	def sortBadWords(self, message):
		self.processedMessages['badWord'].append(message)

	def sortReply(self, message):
		self.processedMessages['@messages'].append(message['message'])

	def sortModMessage(self, message):
		self.processedMessages['modReply'].append(message)

	def processMessages(self, channel):
		folderPath = "data/%s/messageData"%(channel.lower())
		fileList = rh.allOfType(folderPath,".json")
		startTime = datetime.utcnow()
		fileNumber = 1
		for file in fileList:
			messageData = rh.readFile(file)
			print('(%s/%s) Processing messages from %s.' % (fileNumber, len(fileList), file[41:-5]))
			passedMsgs = []
			failedMsgs = []
			messageNumber = 0
			for message in messageData:
				try:
					if self.messageFilter(message): #and self.isReply(message):
						passedMsgs.append(message['message'])
					else:
						failedMsgs.append(message)
				except KeyError:
					self.processedMessages['notMessages'].append(message)
				messageNumber+=1
				print('\t⮡Progress %d%%\tPassed:%s\tFailed:%s' % (100*(messageNumber/len(messageData)), len(passedMsgs), len(failedMsgs)), end = '\r')
			print('')
			self.processedMessages['passed'] += passedMsgs
			self.processedMessages['failed'] += failedMsgs
			fileNumber+=1
			del messageData
			del passedMsgs
			del failedMsgs

		responce = "Processing complete. %d messages Filtered." % (len(self.processedMessages['passed'])+len(self.processedMessages['failed']))
		print(responce)
		output = {'passed':  'data/%s/AI/trainingSet.txt'%(channel), 
				  #'failed': None, 
				  'badWord': 'data/%s/AI/badMessages.json'%(channel), 
				  'modReply':'data/%s/AI/modMessages.json'%(channel), 
				  '@messages':'data/%s/AI/replies.txt'%(channel),
				  'notMessages':'data/%s/AI/events.json'%(channel)
				  }
		print('Writing %d Output Files...' %( len(output)))
		for key in output.keys():
				print('Key: %s\tEntries: %s\n\tLocation: %s' % (key, len(self.processedMessages[key]), output[key]))
				if(output[key].endswith('.txt')):
					rh.writeRAW(output[key], '\n'.join(self.processedMessages[key]))
				else:
					rh.writeJSON(output[key], self.processedMessages[key])
		print("Processing took %s sec."%((datetime.utcnow()-startTime).seconds))

	class filter():
		def __init__(self, binCallback = None, inverted = False):
			self.inverted = inverted
			self.binCallback = binCallback
			if binCallback is None:
				self.binCallback = self.doNothing

		def match(self, message):
			matched = self.condintion(message)
			if matched != self.inverted:
				self.binCallback(message)
			return matched

		def condintion(self, message):
			print("TODO:condintion")
			return False

		def doNothing(self, message):
			pass

	class isSub(filter):
		def condintion(self, message):
			return (int(message['subscriber']) == 0)

	class isNotMod(filter):
		def __init__(self, callback):
			self.inverted = True
			self.binCallback = callback

		def condintion(self, message):
			return (int(message['mod']) == 0)

	class wordCount(filter):
		def __init__(self, numberWords):
			super().__init__()
			self.nWord = numberWords

		def condintion(self, message):
			return (len(message['message'].split()) in range(*self.nWord))

	class inCharacterRange(filter):
		def __init__(self, numberCharacters):
			super().__init__()
			self.nCharacters = numberCharacters

		def condintion(self, message):
			return (len(message['message']) in range(*self.nCharacters))

	class isReply(filter):
		def __init__(self, callback):
			self.inverted = False
			self.binCallback = callback

		def condintion(self, message):
			return (message['message'].count('@') > 0) 

	class doesNotContainBannedWord(filter):
		def __init__(self, callback, wordList):
			self.inverted = True
			self.binCallback = callback
			self.bannedWordsList = wordList

		def condintion(self, message):
			for bannedWord in self.bannedWordsList:
				if bannedWord in message['message'].lower().split():
					return False
			return True

	class isSpam(filter):
		def condintion(self, message):
			split = message["message"].split()
			return (split[0] in split[1:])

	class isNotCommand(filter):
		def condintion(self, message):
			return (message["message"][0] != '!')


	def messageFilter(self, message):
		#no mod messages
		results = []
		filters = [ #self.isSub(),
					self.isReply(callback = self.sortReply),
					self.isNotMod(callback = self.sortModMessage),
					self.isSpam(),
					self.isNotCommand(),
					self.wordCount(numberWords = [4, 20]),
					self.inCharacterRange(numberCharacters = [30, 60]),
					self.doesNotContainBannedWord(callback = self.sortBadWords, wordList = self.wordBlackList)]
		key = [False, True, False, True, True, True, True]
		for barrier in filters:
			results.append(barrier.match(message))
		#if (False in set(results)):
		#print("Message:%s\nScore:%s\nTests:%s"%(message["message"], (results == key), results))
		return (results == key)


def trainAI(path, epochs=3):
		import chatAI as cAI
		print('Training ChatAI with data in %s.' % path)
		try:
			ai = cAI.chatAI("%s/textgenrnn_weights.hdf5"%(path))
			print('Training existing model.')
		except:
			print("No model found. Training from scratch.")
			ai = cAI.chatAI()

		ai.trainData(("%s/trainingSet.txt"% path), epochs)
		print("Your Ai's first words are: %s\nTraining Complete." % ai.generateMessage(0.8))


def main():
	usage = "Usage - python3 chatAI.py [process|train|generate] [args]"
	args = sys.argv[1:]
	try:
		if len(args) < 1: 
			print(usage)
			quit()

		#Process messages and exports the processed messages
		#
		if args[0].lower() == 'process':
			print("Processing %s's message data."%(args[1]))
			trainer = aiTrainer()
			trainer.processMessages(args[1])

		#Generates a a few messages at different temperatures to get a feel for the AI's responces.
		#[channel]
		elif args[0].lower() == 'generate':
			path = 'data/AI/%s/textgenrnn_weights.hdf5' % (args[1].lower())
			import chatAI as cAI  
			ai = cAI.chatAI(path)
			temps = range(0, 8)
			for  temp in temps:
				temp = temp *.2
				print("Temp:%s\n%s"%(temp , ai.generateMessage(temp)))

		#Trains a new model for the AI based on collected data in args[2] folder
		#train [channel] [epochs]
		elif args[0].lower() == 'train':
			import chatAI as cAI
			path = 'data/%s/AI' % (args[1].lower())
			print('cAI Training.\nLocation:%s\tEpochs:%s' %(path, args[2]))
			trainAI(path, epochs=int(args[2]))

	except IndexError:
		print(usage)

if __name__ == "__main__":
	main()
