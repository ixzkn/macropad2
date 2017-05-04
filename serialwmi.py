import threading, traceback

class WMIMonitor:
	"""
	Watches for serial device addition and removal.
	"""

	def __init__(self,deviceid,callback=None,timeout=2000,verbose=False,singleThread=False):
		"""
		Create a new monitor.  Monitor will spawn a seperate thread for an event loop.
		Callbacks are called from the event loop thread.

		Args:
			deviceid: prefix substring of DeviceID, usually of the form "USB\VID_..."
			callback: function to call on device add/loss (see: setCallback)
			timeout: max time to wait inside WMI event
			verbose: print debugging information
		"""
		self._deviceid = deviceid
		self._stop = False
		self.connected = False
		self._verbose = verbose
		self._callback = callback
		self._timeout = timeout
		self._device = None
		if singleThread:
			self._loop()
		else:
			threading.Thread(target=self._loop).start()

	def setCallback(self,callback):
		"""
		Set the callback function for when device is added or lost.

		Args:
			callback: function of the form callback(connected, comPort)
			          connected is true on connect, false on disconnect
			          comPort is the com port of the connected device
		"""
		self._callback = callback

	def getData(self,portName):
		"""
		Gets a WMI Serial port object given a port name (e.g: "COM6")

		Args:
			portName: the port name to search for
		"""
		for port in self._wm.Win32_SerialPort():
			if port.DeviceID == portName:
				return port
		return None

	def stop(self):
		"""
		Stops the event loop.
		"""
		self._stop = True

	def comPort(self):
		"""
		Returns the COM port name of the currently connected device.
		"""
		if self._device:
			return self._device

	def assumeConnected(self):
		"""
		Assume we are already connected to the device and watch for
		disconnect event first instead of connect event.
		"""
		self.connected = True

	def _loop(self):
		import wmi
		self._wm = wmi.WMI()

		# check to see if we are already connected
		for port in self._wm.Win32_SerialPort():
			print(port.PNPDeviceID)
			if port.PNPDeviceID.startswith(self._deviceid):
				self._device = port.DeviceID
				self.connected = True
				if self._callback is not None:
					self._callback(self.connected,self._device)
				if self._verbose:
					print("WMI: Processed events connected=%s" % (str(self.connected),))
				break

		# create WMI events
		self._watchCreate = self._wm.Win32_SerialPort.watch_for("creation")
		self._watchDelete = self._wm.Win32_SerialPort.watch_for("deletion")
		while not self._stop:
			try:
				event = None
				if self.connected:
					event = self._watchDelete(timeout_ms=self._timeout)
					if event.DeviceID == self._device:
						self.connected = False
						if self._callback is not None:
							self._callback(self.connected,self._device)
						if self._verbose:
							print("WMI: Processed events connected=%s" % (str(self.connected),))
				else:
					event = self._watchCreate(timeout_ms=self._timeout)
					data = self.getData(event.DeviceID)
					if data.PNPDeviceID.startswith(self._deviceid):
						self.connected = True
						self._device = data.DeviceID
						if self._callback is not None:
							self._callback(self.connected,self._device)
						if self._verbose:
							print("WMI: Processed events connected=%s" % (str(self.connected),))
				if self._verbose:
					print("WMI: Got Event: %s" % (str(event),))
			except wmi.x_wmi_timed_out:
				pass
		if self._verbose:
			print("WMI: Close WMI")

if __name__ == "__main__":
	WMIMonitor("",verbose=True,singleThread=True)
