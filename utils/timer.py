import time

class Timer:
	def __init__(self):
		self._start = None
		self._end = None
	
	def start(self):
		self._start = time.perf_counter()

	def stop(self):
		self._end = time.perf_counter()

	def __str__(self):
		time = (self._end - self._start) * 1000
		self.end = round(time, 3)
		return f"{self.end} ms"
	
	def __enter__(self, *args, **kwargs):
		self.start()
		return self
     
	def __exit__(self, *args, **kwargs):
		self.stop()
		
