from tlang.tree.model import Node, TreeProcessor, TreeBuilder
from typing import Optional,TypeVar,Generic,Union,Any,Tuple
from enum import Enum

T = TypeVar("T")
Control = Enum("Control", "STEP WAIT")

class Channel(Generic[T]):

	def __init__( self ):
		self.values:List[T] = []
		self.queue:List = []

	def put( self, value:T ):
		self.values.append(value)
		if self.queue:
			for i in range(min(len(self.values), len(self.queue))):
				# NOTE: We don't consume values at that stage
				self.queue.pop(0)()
		return self

	def get( self ) -> Tuple[Control, Optional[T]]:
		if not self.values:
			return (Control.WAIT, None)
		else:
			return (Control.WAIT, self.values.pop(0))

	def join( self, callback ):
		"""Attaches a callback that will be called when there is
		a value available."""
		self.queue.append(callback)
		return self

class Process:

	def __init__( self, *nodes:Node ):
		self.operations:List[Node] = [_ for _ in nodes if _]

class ProcessState:

	def __init__( self, process:Process ):
		self.process:Process = process
		self.counter:int = 0
		self.bindings:Dict[str,Any] = {}
		self.channels:Dict[str,Channel] = {}


class Scheduler:

	def __init__( self ):
		self.scheduled:List[ProcessState] = []

	@property
	def isEmpty( self ):
		return not bool(self.scheduled)

	def schedule( self, state:ProcessState ):
		self.scheduled.append(state)
		return self

	def next( self ) -> ProcessState:
		# NOTE: This is where we could have a different scheduling
		# strategy.
		return self.scheduled.pop(0)

class Interpreter(TreeProcessor):

	def __init__( self, scheduler:Scheduler ):
		super().__init__()
		self.scheduler = scheduler
		self.state:Optional[ProcessState] = None

	def setState( self, state:ProcessState ):
		self.state = state
		return self

	def on_open( self, node ):
		self.state.channels[node["channel"]] = Channel()
		return Control.STEP

	def on_declare( self, node ):
		self.state.bindings.setdefault(node["slot"], None)
		return Control.STEP

	def on_receive( self, node ):
		channel = self.state.channels[node["channel"]]
		status, value = channel.get()
		self.state.bindings[node["slot"]] = value
		# If the channel is waiting, we'll reschedule that process
		# as soon as we have a value
		if status is Control.WAIT:
			channel.join(lambda: self.scheduler.schedule(self))
		return status

class Executor:

	def __init__( self ):
		self.scheduler = Scheduler()

	def run( self, process:Process ):
		state = ProcessState(process)
		inter = Interpreter(self.scheduler)
		self.scheduler.schedule(state)
		while not self.scheduler.isEmpty:
			state = self.scheduler.next()
			inter.setState(state)
			for i,op in enumerate(state.process.operations):
				res = inter.process(op)
				if res is Control.STEP:
					state.counter = i
				else:
					print (f"Process break at step {i}/{len(state.process.operations)-1}: {op}")
					break
			print (f"Process complete: {state.bindings}")
		print ("Stopped")

if __name__ == "__main__":
	node = TreeBuilder.MakeNode
	add = Process(
		node("open",      {"channel":"in"}),
		node("declare",   {"slot":"A"}),
		node("declare",   {"slot":"B"}),
		node("declare",   {"slot":"R"}),
		node("receive",   {"channel":"in", "slot":"A"}),
		node("receive",   {"channel":"in", "slot":"B"}),
		node("intrinsic", {"compute":lambda A,B:A + B, "slot":"R"}),
		node("open",      {"channel":"out"}),
		node("emit",      {"channel":"out", "slot":"R"}),
	)
	Executor().run(add)


# EOF - vim: ts=4 sw=4 noet
