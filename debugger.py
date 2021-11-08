from datetime import datetime, timedelta

class debugger():
	
	__instance = None

	"""
	Levels:
	[0, 1) - General Output
	[1, 4] - Debugging Levels
	[5, 9] - Debugging Levels with Sensitive Information
	"""
	def __init__(self, prefix = "UNKO", template="[{}][{:.2f}]{}", level = 0):
		if debugger.__instance is None:
			self.prefix = prefix
			self.template = template
			self.level = level
			self.start_time = datetime.utcnow()
		debugger.__instance = self

	def getInstance(prefix = "UNKO", level = 0):
		if debugger.__instance is None:
			debugger(prefix, level)
		return debugger.__instance
		

	def log(self, message, level = 0):
		if self.level >= level:
			timeInfo = float((datetime.utcnow() - self.start_time) / timedelta(seconds=1))%86400
			print(self.template.format(self.prefix, timeInfo, message))