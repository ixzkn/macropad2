import os, traceback
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileMonitor(FileSystemEventHandler):
	"""
	Monitors a given filename, and on change
	parses it using the format (a list of what each line means)
	"""

	@staticmethod
	def start(filename,format,callback=None,verbose=False):
		observer = Observer()
		fm = FileMonitor(observer,filename,format,callback,verbose)
		fm._handle()
		observer.schedule(fm, path=os.path.dirname(filename), recursive=False)
		observer.start()
		return fm

	def __init__(self,observer,filename,format,callback,verbose):
		self._observer = observer
		self._format = format
		self._callback = callback
		self._filename = filename
		self._verbose = verbose

	def stop(self):
		self._observer.stop()

	def setCallback(self,callback):
		self._callback = callback

	def _handle(self):
		try:
			data = open(self._filename).read().splitlines()
			self._callback(zip(self._format,data))
			if self._verbose:
				print("FM: Got modify: %s" % (self._filename,))
		except:
			if self._verbose:
				traceback.print_exc()
			pass

	def on_modified(self,event):
		if event.src_path == self._filename:
			self._handle()
