'''
Written by John Gregg - As a hobby to live on.
All Rights Reserved 2019
'''
import os
import sys
import traceback
import resourceHandler as rh
from datetime import datetime
from time import localtime, strftime, strptime

class backupBroker():
	def __init__(self, channel, data, dataCallback):
		self.channel = channel
		self.dataCallback = dataCallback
		self.data = data

		self.debug_backup = False
		self.debug_loadHist = False
		
		self.lastBackup = datetime.utcnow()
		self.dataAgeLimit = 10 #in days
		
		self.dataFolderCheck()

	"""
	backup
	This is a threaded backup function. May undergo reorg soon.
	This will call a callback to get a dict of data. It processes
	the dict. It will generate where the file location is and it will save.
	Bugs: 
	"""
	def backup(self):
		del self.data
		self.data = self.dataCallback()
		for key in self.data.keys():
			responce = self.saveData(self.data[key][1], self.data[key][0])
			del self.data[key][0]
			if self.debug_backup:
				print(responce)
		if self.debug_backup:
			print("[%s] Historic Data older than %d days trimmed."%(datetime.utcnow().strftime('%H:%M:%S'), self.dataAgeLimit))
		rh.removeAgedFiles('data/%s/messageData'%(self.channel), self.dataAgeLimit)
		rh.removeAgedFiles('data/%s/emoteUsageData'%(self.channel), self.dataAgeLimit)
		self.lastBackup = datetime.utcnow()

	def saveData(self, filename, data):
		try:
			rh.writeJSON(filename, data)
			return('[%s] Output %d entries to: "%s".'%(datetime.utcnow(), len(data), filename))
		except Exception as error:
			print("[%s]-- ERROR: BACKUP FAILED DURING WRITE. --\nDUMP:\n%s"%(datetime.utcnow(),traceback.format_exc()))


	def loadHistoricData(self):
		backupTime = datetime.utcnow().strftime("%m-%d-%y")
		historicData = {}
		for key in self.data.keys():
			data = rh.readFile(self.data[key][1])
			if self.debug_loadHist:
				print("[%s]File %s loaded. %d entries."%(datetime.utcnow(), self.data[key][1], len(data)))
			historicData[key] = data
		return historicData

	def dataFolderCheck(self):
		channelPath = 'data/%s'%(self.channel)
		folderCheck = ['data',
				 	   'data/%s'%(self.channel),
				 	   'data/%s/AI'%(self.channel),
				 	   'data/%s/messageData'%(self.channel),
				 	   'data/%s/emoteUsageData'%(self.channel),
					  ]
		for folder in folderCheck:
			if not os.path.exists(folder):
				os.mkdir(folder)
				print("Directory " , folder ,  " Created ")
