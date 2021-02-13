'''
Written by John Gregg - As a hobby to live on.
All Rights Reserved 2019
'''
from datetime import datetime
from threading import Timer, Thread

class scheduler():
	def __init__(self, bot):
		self.events = {}
		self.bot = bot

	def addEvent(self, incEvent):
		if isinstance(incEvent, event):
			self.events[incEvent.name] = incEvent
			incEvent.start()
			return 'Event added. %s'%(incEvent.name)
		else:
			return 'Invalid Event.'

	def removeEvent(self, eventName):
		ev = self.events.get(eventName)
		if ev is not None:
			ev.killEvent()
			del self.events[eventName]

	def closeAllEvents(self):
		for key in list(self.events.keys()):
			self.removeEvent(key)

	def closeAllNamedEvents(self, name):
		for key in list(self.events.keys()):
			if name in key:
				self.removeEvent(key)
			
def doNothing(self):
	pass

"""
Event
The event class handles starting and dispatching of events depending on the time or activation condintions.
Flow: Event.start() -> Event.dispatch() -> <event>.callback()
"""
class event(Thread):
	def __init__(self, name, frequency, callback=doNothing, repeat=False):
		Thread.__init__(self)
		self.name = name
		self.freq = frequency
		self.callback = callback
		self.repeat = repeat
		self.thread = None

	def start(self):
		self.thread = Timer(self.freq, self.dispatch) 
		self.thread.start()

	def dispatch(self):
		self.callback()
		if self.repeat:
			self.start()
#		else:
#			self.bot.eventScheduler.removeEvent(self.name)
	
	def killEvent(self):
		self.thread.cancel()
		


"""
============================================================

					Events Section

	Note: All events start counting down from 
		  the moment of instanciation.

============================================================
"""

#Calls <callback> in <frequency> seconds. And repeatidly calls it every <freq> secondds.
#This function is specialized to call the callback function before closing the thread.
class backupEvent(event):
	def __init__(self, bot, frequency, callback):
		self.bot = bot
		super().__init__(name='regular_Backup', frequency=frequency, callback=callback, repeat=True)
	
	def killEvent(self):
		self.callback()
		self.thread.cancel()


#Sends a <message> in <freq> seconds. 
class broadcastEvent(event):
	def __init__(self, bot, name, message, freq, repeat=False):
		self.bot = bot
		self.message = message
		super().__init__(name=name, frequency=freq, callback=self.sendReminder, repeat=repeat)

	def sendReminder(self):
		self.bot.send_pubmsg( self.message)

#Calls <callback> at <time>. If set to repeat, it will repeat at <time> Daily.
class functionEvent(event):
	def __init__(self, bot, name, callback, time, repeat=False):
		self.bot = bot

		if time is datetime:
			seconds = (time - datetime.utcnow()).seconds
			if bot.debug:
				timeInfo = datetime.utcnow().strftime('%H:%M:%S')
				print("[functionEvent][%s][EVENT:%s]:%s seconds."%(timeInfo, time.strftime('%d - %H:%M:%S'), seconds))
			self.tcCB = callback
			super().__init__(name=name, frequency=seconds, callback=self.timeCorrection, repeat=repeat)
		else:
			seconds = time
			super().__init__(name=name, frequency=seconds, callback=callback, repeat=repeat)

	def timeCorrection(self):
		self.callback = self.tcCB
		self.callback()
		self.freq = 86400
		if self.bot.debug:
			timeInfo = datetime.utcnow().strftime('%H:%M:%S')			
			print("[functionEvent][%s][%s]: Freq:%s"%(timeInfo, self.callback, self.freq))