from __future__ import print_function
# Macropad 1 - Media / game macro pad controller
# depends on the following libs:
# pyserial, watchdog, python wmi, pywin32, demjson

######################################################################
# Config

# Verbosity for each component, warning: some are very chatty
verbosity = {
	'FM': False,
	'DEV': True,
	'WMI': True,
	'Player': False,
	'Manager': True
}

# Must sync the following with Arduino code ##########

# Based on Arduino keyboard library:
KEY_CTRL  = 128
KEY_SHIFT = 129
KEY_ALT   = 131
# chosen arbritrarly:
MACRO_END = 132

# Keep in sync with microcontroller code
KEYCOUNT = 5
MAX_MACRO_SIZE = 4
FULL_MACRO_SIZE = MAX_MACRO_SIZE*2
PROG_SIZE = FULL_MACRO_SIZE*KEYCOUNT

######################################################################
import serial, threading, os, subprocess, time, re, traceback, binascii, demjson
from serialwmi import WMIMonitor
from foocontrol import PlayerFoobar

def printProfile(keys):
	for key in keys:
		print("   ",)
		if 'down' in key:
			print("d: ",)
			for macro in key['down']:
				print(macro,",",)
		if 'up' in key:
			print("u: ",)
			for macro in key['up']:
				print(macro,",",)
		print("")

def ordinateProfile(keys):
	nameMap = {
		"CTRL": KEY_CTRL,
		"SHIFT": KEY_SHIFT,
		"ALT": KEY_ALT
	}
	def ordinateOne(value):
		if value in nameMap: return nameMap[value]
		return ord(value)
	for k in xrange(0,len(keys)):
		if 'down' in keys[k]:
			for m in xrange(0,len(keys[k]['down'])):
				keys[k]['down'][m] = ordinateOne(keys[k]['down'][m])
		if 'up' in keys[k]:
			for m in xrange(0,len(keys[k]['up'])):
				keys[k]['up'][m] = ordinateOne(keys[k]['up'][m])
	return keys

def verifyProfile(keys):
	if len(keys) < KEYCOUNT:
		print("Profile: Warning: not all keys bound")
	if len(keys) > KEYCOUNT:
		print("Profile: ERROR: too many keys bound:")
		printProfile(keys)
	for key in keys:
		if 'down' not in key:
			print("Profile: Warning: did not find down keyset")
		elif len(key['down']) > MAX_MACRO_SIZE:
			print("Profile: ERROR: macro is too long:")
			printProfile(keys)
		if 'up' not in key:
			print("Profile: Warning: did not find up keyset")
		elif len(key['up']) > MAX_MACRO_SIZE:
			print("Profile: ERROR: macro is too long:")
			printProfile(keys)
	return keys

def symetricProfile(keys):
	"""
	Takes an array of an array of key definitions and
	makes a symetric profile (up/down are the inverse).
	"""
	data = []
	for key in keys:
		data.append({
			'down': key,
			'up': list(reversed(key))
		})
	return verifyProfile(data)

def simpleProfile(keys):
	"""
	Accepts just a list of keys.
	Generates a symetric profile where a macropad key
	maps to just one key in the list.
	"""
	data = []
	for key in keys:
		data.append([key])
	return symetricProfile(data)

def scanProfiles(folder):
	result = {}
	for f in os.listdir(folder):
		fl = os.path.join(folder,f)
		if os.path.isfile(fl): 
			result[f] = loadProfile(fl)
	return result

def loadProfile(file):
	try:
		profile = demjson.decode(open(file).read())
		types = {
			'simple': simpleProfile,
			'symetric': symetricProfile,
			'complete': verifyProfile
		}
		# validate it:
		if "type" not in profile:
			print("Invalid profile, missing type")
			return None
		elif profile["type"] not in types.keys():
			print("Invalid profile, unknown type",type)
			return None
		if "profile" not in profile:
			print("Invalid profile, missing profile")
			return None
		return ordinateProfile(types[profile['type']](profile['profile']))
	except:
		traceback.print_exc()
		print("Failed to load profile",os.path.basename(file))
		return None

######################################################################

class Device:
	"""
	Represents communication with the device once
	we are connected.  Connect with port, and baud.
	"""
	def __init__(self,port,baud,retries=0,callback=None,retrysleep=200):
		self._verbose = verbosity['DEV']
		for x in xrange(0,retries):
			try:
				self._ser = serial.Serial(port,baud,timeout=2)
				break
			except:
				if self._verbose:
					print("Retrying %d" % (x,))
				time.sleep(retrysleep)
				continue
		self._stop = False
		self.connected = True
		if self._verbose:
			print("DEV: Connected")
		self.buttonState = [False, False, False, False, False]
		self._callbacks = [callback,callback,callback,callback,callback]
		self._chord = []
		self.lightState = {}
		self._keyboardMode = False
		self._swget = threading.Event()
		self._swgetValue = None
		threading.Thread(target=lambda: self._loop()).start()

	def stop(self):
		self._stop = True

	def setCallback(self,buttonno,callback):
		self._callbacks[buttonno] = callback

	def setLight(self,lightid,color):
		self.lightState[lightid] = color
		if not self._keyboardMode:
			self._ser.write(str(lightid))
			self._ser.write(chr(color[0]))
			self._ser.write(chr(color[1]))
			self._ser.write(chr(color[2]))
		elif self._verbose:
			print("DEV: set light in kbd mode not allowed")

	def _restoreLights(self):
		"""
		Called on keyboard mode exit to put lights back into
		the state they were before entering keyboard mode (device forgets)
		"""
		for lightid,color in self.lightState.iteritems():
			self.setLight(lightid,color)

	def setKeymode(self,on):
		if on:
			self._ser.write('k')
		else:
			self._ser.write('x')

	def progKeymode(self,keymap):
		# MUST write PROG_SIZE values
		data = bytearray([ord('p')])
		# values are always in reverse order
		for x in range(KEYCOUNT-1,-1,-1):
			for u in range(MAX_MACRO_SIZE-1,-1,-1):
				if (x < len(keymap)) and ('up' in keymap[x]) and (u < len(keymap[x]['up'])):
					data.append(keymap[x]['up'][u])
				else:
					data.append(MACRO_END)
			for d in range(MAX_MACRO_SIZE-1,-1,-1):
				if (x < len(keymap)) and ('down' in keymap[x]) and (d < len(keymap[x]['down'])):
					data.append(keymap[x]['down'][d])
				else:
					data.append(MACRO_END)
		print(binascii.hexlify(data))
		self._ser.write(data)

	def _loop(self):
		while not self._stop:
			try:
				line = self._ser.readline()
				if "-" in line:
					data = line.split("-")
					try:
						button = int(data[0].strip())
						state = int(data[1].strip())
						self.buttonState[button] = (state == 1)
						if state == 1:
							self._chord.append(button)
						if state == 0:
							if self._verbose:
								print("DEV: Got button: %s %s" % (line,str(self._chord)))
							self._callbacks[button](button,state,self._chord)
							self._chord.remove(button)
					except:
						# this can fail all the time
						if self._verbose:
							print(data)
							traceback.print_exc()
				elif "kbd" in line:
					print("DEV: In keyboard mode")
					self._keyboardMode = True
				elif "nkb" in line:
					print("DEV: Exit keyboard mode")
					self._restoreLights()
					self._keyboardMode = False
				else:
					# signal swget and set a value for everything else
					self._swgetValue = line
					self._swget.set()
			except:
				self.connected = False
				if self._verbose:
					traceback.print_exc()
				break
		self._ser.close()
		if self._verbose:
			print("DEV: Close Device")

class Manager:
	def __init__(self):
		self._dev = None
		self._foobar = None
		self._verbose = verbosity['Manager']
		scriptdir = os.path.dirname(os.path.realpath(__file__))
		self._config = demjson.decode(open(os.path.join(scriptdir,"config.js")).read())
		self._profiles = scanProfiles(os.path.join(scriptdir,"profiles"))
		self._wm = WMIMonitor(self._config['deviceId'],callback=self._connect,verbose=verbosity['WMI'])
		self.profile = None

	def _button(self,button,state,chord):
		if chord == [1]:
			self._foobar.playpause()
		elif chord == [1,2]:
			self._foobar.pauseonend()
		elif chord == [2]:
			self._foobar.voldown()
		elif chord == [3]:
			self._foobar.volup()
		elif chord == [0]:
			self._foobar.next()
		elif chord == [4]:
			self._foobar.prev()
		elif chord == [1,0]:
			self._foobar.rateup()
		elif chord == [1,4]:
			self._foobar.ratedown()
		elif chord == [2,1]:
			if self._foobar.state("order") == "Shuffle (tracks)":
				self._foobar.defaultOrder()
			else:
				self._foobar.shuffleOrder()

	def printButtonState(self):
		for v in self._dev.buttonState:
			print(" %d" % v)

	def printLightState(self):
		for k,v in self._dev.lightState.iteritems():
			print("    %d: (%d,%d,%d)" % (k,v[0],v[1],v[2]))

	def keymode(self,value):
		if self._dev is not None:
			self._dev.setKeymode(value)

	def _internalstop(self):
		if self._dev is not None:
			self._dev.stop()
			self._dev = None
		if self._foobar is not None:
			self._foobar.stop()
			self._foobar = None

	def _player(self,state):
		try:
			baseRed = 0
			if state["stopAfter"]:
				self._dev.setLight(0,(0,0,15))
			elif state["playing"] == "playing":
				percent = 0
				try:
					percent = int(self._foobar.state("percent"))
				except:
					pass
				self._dev.setLight(0,(3,3,int(percent / 5.0)))
			else:
				self._dev.setLight(0,(15,0,0))
		except:
			if self._verbose:
				traceback.print_exc()

	def _songchange(self):
		rating = 0
		if self._verbose:
			print("Song change")
		try:
			rating = 5+int(self._foobar.state("rating"))*2
			self._dev.setLight(1,(rating-2,5,5))
		except:
			self._dev.setLight(1,(0,0,0))

	def stop(self):
		self._wm.stop()
		self._internalstop()

	def loadProfile(self,profile):
		if profile not in self._profiles:
			print("Not a profile")
			return
		prof = self._profiles[profile]
		if self._dev is not None:
			self._dev.progKeymode(prof)
		self._profile = profile

	def connect(self):
		self._connect(True,self._config['defaultPort'])
		self._wm.assumeConnected()

	def _connect(self,state,data):
		if state:
			# we connected
			self._dev = Device(data,self._config['baudRate'],retries=4,callback=self._button)
			self._foobar = PlayerFoobar(self._config['playerExe'],
										self._config['playingFile'],
										self._config['fileFormat'],
										callback=self._player,
										verbose=verbosity['Player'],verboseFile=verbosity['FM'])
			self._foobar.setSongChangeCallback(self._songchange)
		else:
			# we lost connection
			self._internalstop()
			if self._verbose:
				print("Manager: Lost connection")

def help():
	print("""Commands:
quit    - quit
help    - help
button  - show button state
light   - show light state
connect - try to connect right now
key     - go into keyboard mode
ekey    - exit keyboard mode
prof    - load profile
listpro - list current profile
""")

if __name__ == "__main__":
	manager = Manager()
	while True:
		try:
			v = raw_input("> ")
			if v.startswith("q"): break
			if v.startswith("h"): help()
			if v.startswith("c"): 
				try:
					manager.connect()
				except:
					print("Failed to connnect")
			if v.startswith("b"):
				manager.printButtonState()
			if v.startswith("l"):
				manager.printLightState()
			if v.startswith("k"):
				manager.keymode(True)
			if v.startswith("e"):
				manager.keymode(False)
			if v.startswith("p"):
				manager.loadProfile(v.split(" ")[1])
			if v.startswith("l"):
				print(manager.profile)
		except:
			traceback.print_exc()
			break
	manager.stop()
