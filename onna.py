import sys
import json
import secrets
import requests
import threading
import webbrowser
import scheduler as sh
import twitchBot as tb
import resourceHandler as rh
from datetime import datetime, timedelta
from requests_oauthlib import OAuth2Session

class onna():
	def __init__(self, username, user_chat_token):
		self.debug = False;
		self.options = {"FIRST_X_CHANNELS": 3, "EVENT_FREQUENCY": 120, "CHANNEL_LANGUAGE" :"en"}
		
		self.client_id =  secrets.CLIENT_ID
		self.client_secret = secrets.CLIENT_SECRET
		self.client_scope = "user:edit user:edit:follows analytics:read:games analytics:read:extensions"
		self.client_token = ''
		self.getOAuth()

		self.header = {'Authorization': 'Bearer ' + self.client_token, 'Client-Id': self.client_id}
		self.verify = True
		

		self.base_url = "https://api.twitch.tv/helix"

		self.user_info = (self.get("users?login=%s"% (username.lower()))["data"])[0]
		self.username = username
		self.user_id = self.user_info["id"]
		self.user_chat_token = user_chat_token
		self.user_client_token = self.requestAuth()	
		
		self.bots = {}
		self.channels_top = {}

		self.eventScheduler = sh.scheduler(self)
		dataStream = sh.functionEvent(self, 'top_channel', self.recurrentRequests, self.options["EVENT_FREQUENCY"], True)
		self.eventScheduler.addEvent(dataStream)

		self.recurrentRequests()

		timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
		print("[ONNA][%s]Initialized." %(timeInfo))

	def recurrentRequests(self):
		self.getTopChannels()
		self.attachBots()
		if self.debug:
			timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
			print("[ONNA][%s]Data Tick." %(timeInfo))

	def attachBots(self):
		channels = list(set(self.bots.keys()) - set(self.channels_top.keys()))
		#Closes old Bots
		removed = []
		added = []
		for channel in self.bots.keys():
			if channel not in self.channels_top.keys():
				print("[ONNA][%s] Bot Shut Down."%(channel))
				self.leaveChannel(channel)
				removed.append(channel)

		#Spins up new bots
		for channel in self.channels_top.keys():
			if channel not in self.bots.keys():
				print("[ONNA][%s] Bot Spun Up"%(channel))
				self.followChannel(channel)
				self.joinChannel(channel)
				added.append(channel)

		if self.debug:
			timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
			print("[ONNA][%s][BOTS]Channels: %s - Added: %s - Removed: %s" %(timeInfo, list(self.channels_top.keys()), added, removed))


	def getTopChannels(self):
		r = self.get('streams?first=%s&language=%s'%(self.options['FIRST_X_CHANNELS'], self.options['CHANNEL_LANGUAGE']))
		for channel in r['data']:
			username = channel['user_name']
			self.channels_top[username] = channel
			if self.debug:
				timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
				print("[ONNA][%s] %s" %(timeInfo, channel))

	def followChannel(self, channel):
		(self.channels_top[channel])["user_id"]
		header = {'Authorization': 'Bearer ' + self.user_client_token["access_token"], 'Client-Id': self.client_id}
		data = {"from_id": self.user_id, "to_id": (self.channels_top[channel])["id"]}
		r = requests.post("%s/%s"%(self.base_url, "users/follows"), headers=header,  data=data, verify=self.verify)
		if self.debug:
			timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
			print("[ONNA][%s] Follow @ %s - %s - %s" %(timeInfo, channel, r, data))

	def joinChannel(self, channel):
		self.bots[channel] =  tb.TwitchBot(self.username, channel, self.user_chat_token)
		self.bots[channel].debug = self.debug
		thread = threading.Thread(target=self.bots[channel].start)
		thread.start()

	def leaveChannel(self, channel):
		channel = '#' + channel
		self.bots[channel].exit()



	def getOAuth(self):
		grant_type = "client_credentials"
		oAuth_url = "https://id.twitch.tv/oauth2/token?client_id=%s&client_secret=%s&grant_type=%s&scope=%s"%(self.client_id, self.client_secret, grant_type, self.client_scope)
		r = requests.post(oAuth_url).json()
		if self.debug:
				timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
				print("[ONNA][%s] %s" %(timeInfo, r))
		self.client_token = r['access_token']
		print("[ONNA]Client Authenticated to Twitch.")

	def requestAuth(self):
		print("[ONNA]Authenticating as %s to Twitch." %(self.username))
		
		authUrl = "https://id.twitch.tv/oauth2/authorize"
		tokenURL = "https://id.twitch.tv/oauth2/token"
		redirect_uri = "https://localhost"

		r = requests.get("%s?client_id=%s&redirect_uri=%s&response_type=token&scope=%s"%(authUrl, self.client_id, redirect_uri, self.client_scope), verify=self.verify)
		twitch = OAuth2Session(self.client_id, redirect_uri = redirect_uri, scope = self.client_scope)
		authorization_url, state = twitch.authorization_url(authUrl)
		print("Visit this page in your browser:\n{}".format(authorization_url))		
		code = input("Paste CODE you get back here: ")		
		r = requests.post("%s?client_id=%s&client_secret=%s&code=%s&grant_type=authorization_code&redirect_uri=%s"%(tokenURL, self.client_id, self.client_secret, code, redirect_uri), verify=self.verify)
		print("[ONNA]Succuessfully Authenticated to twitch as %s." %(self.username))
		if self.debug:
				timeInfo = str((datetime.utcnow() - datetime(1970, 1, 1)) / timedelta(seconds=1))[4:10]
				print("[ONNA][%s] %s" %(timeInfo, r.json()))
		return r.json()

	def get(self, service):
		r = requests.get("%s/%s"%(self.base_url, service), headers=self.header, verify=self.verify)
		try:
		  r.raise_for_status()
		except requests.exceptions.HTTPError as e:
		  print(e)
		  return {'data': e}
		return r.json()


	def post(self, service, data = {}):
		r = requests.post("%s/%s"%(self.base_url, service), headers=self.header, data=data, verify=self.verify)
		return r


def main():
	#if len(sys.argv[1:]) != 3: 
	#	print("Usage - py twitchTenticles.py -u [username] -t [token] -c [channels] - t[0-100]")
	#	quit()

	args = sys.argv[1:]
	state = 0
	username = ''
	token = ''
	channels = []
	maps = {'-u':1, '-t':2}
	for arg in args:
		try:
			state = maps[arg]
		except:		
			if state == 1:
				username = arg
			elif state == 2:
				token = arg
	onna(username, token)
		

if __name__ == "__main__":
	main()