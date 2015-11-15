import os, subprocess, traceback
from simplefilemon import FileMonitor

class PlayerFoobar:
	"""
	For watching and controlling the player.
	Wraps FileMonitor
	"""
	def __init__(self,playerExe,infofile,infoformat,callback=None,verbose=False,verboseFile=False):
		self._verbose = verbose
		self._callback = callback
		self._playerExe = playerExe
		self._laststate = {}
		self._prevsong = None
		self._callbacksong = None
		self._filemon = FileMonitor.start(infofile,infoformat,callback=self._callbackInt,verbose=verboseFile)

	def _call(self,cmd,desc):
		return subprocess.check_output([self._playerExe,cmd])
		if self._verbose:
			print("Player: %s" % (desc,))

	def playpause(self):
		self._call("/playpause","Play/Pause")

	def prev(self):
		self._call("/prev","Previous")

	def next(self):
		self._call("/next","Next")

	def state(self,key):
		return self._laststate[key]

	def _order(self,order):
		subprocess.call("\""+self._playerExe+"\" /runcmd=\"Playback/Order/"+order+"\"",shell=True)
		self._laststate['order'] = order
		if self._verbose:
			print("Player: Play Order: %s" % (order,))
	
	def defaultOrder(self):
		self._order("Default")

	def shuffleOrder(self):
		self._order("Shuffle (tracks)")

	def setSongChangeCallback(self,cb):
		self._callbacksong = cb

	def _callbackInt(self,data):
		try:
			for key,value in data:
				self._laststate[key] = value
			songhash = self._laststate["artist"]+self._laststate["title"]+self._laststate["album"]
			if self._prevsong != songhash:
				self._prevsong = songhash
				if self._callbacksong:
					self._callbacksong()
			if self._callback:
				self._callback(self._laststate)
		except:
			if self._verbose:
				traceback.print_exc()

	def stop(self):
		self._filemon.stop()
