'''
Written by John Gregg - As a hobby to live on.
All Rights Reserved 2019
'''
import os
import sys
import resourceHandler as rh
from textgenrnn import textgenrnn
"""
For More information on the textgenrnn see:
https://github.com/minimaxir/textgenrnn

Neural net, trained by chat to be in chat!
"""
class chatAI():
	def __init__(self, weights=None):
		from textgenrnn import textgenrnn
		if weights != None:
			self.cai = textgenrnn(weights)
		else:
			self.cai = textgenrnn()

	def generateMessage(self, temp=0.8, n=1):
		return self.cai.generate(temperature=temp, return_as_list=True, n=n)

	def trainData(self, fileName, epochs=3):
		self.cai.train_from_file(fileName, num_epochs = epochs)