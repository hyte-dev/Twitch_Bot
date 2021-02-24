import sys
import json
import time
import secrets
import requests
import threading
import webbrowser
import debugger as db
import scheduler as sh
import twitchBot as tb
import resourceHandler as rh
#from datetime import datetime, timedelta
from requests_oauthlib import OAuth2Session

class onna():
	def __init__(self, username, user_chat_token, debug_level = 9):
		self.debugger = db.debugger(prefix="ONNA", level=debug_level)
		self.debug = False;
		
		self.options = {"FIRST_X_CHANNELS": 1, 
						"EVENT_FREQUENCY": 60, 
						"CHANNEL_LANGUAGE" :"en", 
						"VIEWER_COUNT_MAX": 24000,
						"VIEWER_COUNT_MIN": 10000 }
		self.eventScheduler = sh.scheduler(self)
		
		self.client_id =  secrets.CLIENT_ID
		self.client_secret = secrets.CLIENT_SECRET
		self.client_scope = "user:edit user:edit:follows analytics:read:games analytics:read:extensions"
		self.client_token = self.getOAuth()

		self.header = {'Authorization': 'Bearer ' + self.client_token['access_token'], 'Client-Id': self.client_id}
		self.verify = True

		

		self.base_url = "https://api.twitch.tv/helix"

		self.user_info = (self.get("users?login=%s"% (username.lower()))["data"])[0]
		self.username = username
		self.user_id = self.user_info["id"]
		self.user_chat_token = user_chat_token
		self.user_auth_stat = []
		self.user_client_token = self.requestAuth()
		
		self.bots = {}
		self.channels_top = {}

		dataStream = sh.functionEvent(self, 'dataStream', self.recurrentRequests, self.options["EVENT_FREQUENCY"], True)
		self.eventScheduler.addEvent(dataStream)

		self.recurrentRequests()

		self.debugger.log("Initialized.")

	def recurrentRequests(self):
		self.getTopChannels()
		self.attachBots()
		self.telemetry()
		if self.debug:
			self.debugger.log("Data Tick. - Scheduled: %s" %(list(self.eventScheduler.events.keys())), 1)

	def attachBots(self):
		#Closes old Bots
		removed = []
		added = []
		for channel in self.bots.keys():
			if channel not in self.channels_top.keys():
				self.debugger("Shut Down %s bot."%(channel))
				removed.append(channel)
				self.bots[channel].exit()				
		for channel in removed:
			del self.bots[channel]
				

		#Spins up new bots
		for channel in self.channels_top.keys():
			if channel not in self.bots.keys():
				self.debugger.log("Bot Spun Up. %s has %s viewers."%(channel, (self.channels_top[channel])["viewer_count"]))
				self.followChannel(channel)
				self.joinChannel(channel)
				added.append(channel)
				time.sleep(5)
		
		self.debugger.log("Channels: %s - Added: %s - Removed: %s" %(list(self.channels_top.keys()), added, removed), 2)


	def getTopChannels(self):
		self.channels_top = {}
		r = self.get('streams?first=%s&language=%s'%(30, self.options['CHANNEL_LANGUAGE']))
		for channel in r['data']:
			if (self.options['VIEWER_COUNT_MIN'] <= channel["viewer_count"] and channel["viewer_count"] <= self.options['VIEWER_COUNT_MAX']) and len(self.channels_top) < self.options['FIRST_X_CHANNELS']:
				username = channel['user_name']
				self.channels_top[username] = channel
				self.debugger.log(channel, 4)


	def followChannel(self, channel):
		(self.channels_top[channel])["user_id"]
		header = {'Authorization': 'Bearer ' + self.user_client_token["access_token"], 'Client-Id': self.client_id}
		data = {"from_id": self.user_id, "to_id": (self.channels_top[channel])["id"]}
		r = requests.post("%s/%s"%(self.base_url, "users/follows"), headers=header,  data=data, verify=self.verify)
		self.debugger.log("Follow @ %s - %s - %s" %(channel, r, data), 4)


	def joinChannel(self, channel):
		self.bots[channel] =  tb.TwitchBot(self.username, channel, self.user_chat_token)
		self.bots[channel].debug = self.debug
		thread = threading.Thread(target=self.bots[channel].start)
		thread.start()


	def getOAuth(self):
		grant_type = "client_credentials"
		oAuth_url = "https://id.twitch.tv/oauth2/token?client_id=%s&client_secret=%s&grant_type=%s&scope=%s"%(self.client_id, self.client_secret, grant_type, self.client_scope)
		r = requests.post(oAuth_url).json()
		clientTokenRefresh = sh.functionEvent(self, 'clientTokenRefresh', self.getOAuth, r["expires_in"] - 20, False)
		self.eventScheduler.addEvent(clientTokenRefresh)
		self.debugger.log(r, 8)
		self.debugger.log("Client Authenticated to Twitch.", 0)
		return r

	def requestAuth(self):
		self.debugger.log("[ONNA]Authenticating as %s to Twitch." %(self.username), 0)

		authURL = "https://id.twitch.tv/oauth2/authorize"
		tokenURL = "https://id.twitch.tv/oauth2/token"
		redirect_uri = "https://localhost"
		
		saved_token = rh.readFile("data/metastate")

		if saved_token == []:
			twitch = OAuth2Session(self.client_id, redirect_uri = redirect_uri, scope = self.client_scope)
			authorization_url, self.user_auth_state = twitch.authorization_url(authURL)
			print("Visit this page in your browser:\n{}".format(authorization_url))		
			code = input("Paste CODE you get back here: ")		
			r = requests.post("%s?client_id=%s&client_secret=%s&code=%s&grant_type=authorization_code&redirect_uri=%s"%(tokenURL, self.client_id, self.client_secret, code, redirect_uri), verify=self.verify)
			self.debugger.log(r.json(), 0)

		else:
			refreshURL = "%s?grant_type=refresh_token&refresh_token=%s&client_id=%s&client_secret=%s"%(tokenURL, saved_token["refresh_token"], self.client_id, self.client_secret)
			r = requests.post(refreshURL)

		token =  r.json()
		rh.writeJSON("data/metastate", token)
		userClientTokenRefresh = sh.functionEvent(self, 'appTokenRefresh', self.requestAuth, token["expires_in"] - 20 , False)
		self.eventScheduler.addEvent(userClientTokenRefresh)
		self.debugger.log("Succuessfully Authenticated to twitch as %s." %(self.username), 0)
		return token

	def telemetry(self):
		br = "Telemetry Report"
		for channel in self.bots.keys():
			br = br + "\n\t%s\tVC:%s\tLive:%s\t:Last Message:%s"%(channel, (self.channels_top[channel])["viewer_count"], self.bots[channel].live, self.bots[channel].last_message)
		self.debugger.log(br)

	def get(self, service):
		r = requests.get("%s/%s"%(self.base_url, service), headers=self.header, verify=self.verify)
		try:
		  r.raise_for_status()
		except requests.exceptions.HTTPError as e:
		  self.debugger.log(e, 5)
		  return {'data': e}
		return r.json()


	def post(self, service, data = {}):
		r = requests.post("%s/%s"%(self.base_url, service), headers=self.header, data=data, verify=self.verify)
		return r

def addSecs(tm, secs):
    fulldate = datetime(100, 1, 1, tm.hour, tm.minute, tm.second)
    fulldate = fulldate + timedelta(seconds=secs)
    return fulldate.time()

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
