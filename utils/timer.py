import time

class Timer:
	def __init__(self):
		self.time = None
		self.start = None
		self.end = None
		
	def __str__(self):
		return f"{self.end} ms"
	
	def __enter__(self, *args, **kwargs):
		self.start = time.perf_counter()
		return self
     
 	def __exit__(self, *args, **kwargs):
		self.end = round((time.perf_counter - self.start) * 1000, 3)
