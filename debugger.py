from datetime import datetime, timedelta

class debugger():
	def __init__(self, prefix = "UNKO", template="[{}][{:.2f}]{}", level = 0):
		self.prefix = prefix
		self.template = template
		self.level = level

		"""
		Levels:
		[0, 1) - General Output
		[1, 4] - Debugging Levels
		[5, 9] - Debugging Levels with Sensitive Information

		"""

		
		self.start_time = datetime.utcnow()

	def log(self, message, level = 0):
		if self.level >= level:
			timeInfo = float((datetime.utcnow() - self.start_time) / timedelta(seconds=1))
			print(self.template.format(self.prefix, timeInfo, message))