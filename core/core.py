from sublime_db.core.typecheck import (
	Any,
	Generator,
	Callable,
	List,
	Optional,
	TypeVar,
	Generic,
	Union
)

import sublime
import threading
import concurrent

from sublime_db.libs import asyncio
from .log import log_exception

T = TypeVar('T')

awaitable = Generator[Any, Any, T]
async = asyncio.coroutine
future = asyncio.Future

main_loop = asyncio.new_event_loop()
def _exception_handler(loop: Any, context: dict) -> None:
	print('An exception occured in the main_loop')
	try: 
		raise context['exception']
	except:
		log_exception()

main_loop.set_exception_handler(_exception_handler)
main_executor = concurrent.futures.ThreadPoolExecutor(max_workers = 5)

def _run_event_loop() -> None:
	print('running main event loop')
	main_loop.run_forever()

_main_thread = threading.Thread(target = _run_event_loop)
def start_event_loop() -> None:
	_main_thread.start()

def stop_event_loop() -> None:
	main_loop.stop()
	

def all_methods(decorator):
    def decorate(cls): 
        for attribute in cls.__dict__:
            if callable(getattr(cls,attribute)): 
                setattr(cls, attribute, decorator(getattr(cls, attribute)))
        return cls
    return decorate

'''decorator for requiring that a function must be run in the background'''
def require_main_thread(function):
    def wrapper(*args, **kwargs):
        assert_main_thread()
        return function(*args, **kwargs)
    return wrapper
    

def run(awaitable: awaitable[T], on_done: Optional[Callable[[T], None]] = None) -> None:
	task = main_loop.create_task(awaitable)
	def done(task) -> None:
		result = task.result()
		if on_done:
			on_done(result)
			
	task.add_done_callback(done)

def assert_main_thread() -> None:
	assert threading.current_thread() == _main_thread, 'expecting main thread'

def display(msg: 'Any') -> None:
	sublime.error_message('{}'.format(msg))

class Error:
	def __init__(self, msg: str) -> None:
		self.msg = msg
	def __str__(self) -> str:
		return self.msg
	 	