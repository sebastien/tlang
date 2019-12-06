from tlang.tree.model import Node,TreeProcessor,TreeBuilder,NodeError
from typing import Optional,TypeVar,Generic,Union,Any
from enum import Enum

## @tdoc:indent spaces=2
## title: Process-based research interpreter
## texto|texto
##   The core idea of this interpreter is to try and see what happens when
##   we use communication between channels as a core mechanism of the language.
##
##   For instance, we consider an invocation as opening a channel and feeding
##   the channel arguments. One or more results can then be read to and from
##   the channel.
##
##   Each _channel_ has a corresponding _process_ that receives or emits
##   data. A process is stepped using the `Process.next` method, which will
##   tell wether it was sucessful in stepping or not. For instance, if the
##   receiving channel is not emitting, it will not be able to continue.
## :

match = TreeProcessor.Match
T     = TypeVar("T")
Status = Enum("Status", "WAIT STEP")

# -----------------------------------------------------------------------------
#
# CHANNEL
#
# -----------------------------------------------------------------------------

## section title=Channel

# TODO: Should be parametric
class Channel(Generic[T]):
	"""Channels are like pipes where you put values, peek for available
	values and consume available values."""

	def __init__( self  ):
		# TODO: High water mark
		self.queue:List[T] = []
		self.consumeWait:List['Process'] = []

	@property
	def isReady( self) -> bool :
		return bool(self.stack)

	@property
	def expects( self) -> bool :
		return len(self.consumeWait)

	def put( self, value:T ) -> T:
		is_consumed = False
		for state in self.consumeWait:
			state.onReceive(self, value)
			is_consumed = True
			break
		if not is_consumed:
			self.queue.append(value)
		return value

	# FIXME: We should have a wait queue
	# def peek( self, process:Process ) -> Optional[T]:
	# 	if self.queue:
	# 		self.process.onPeek(self, self.queue[0])
	# 	else:
	# 		return Wait

	# TODO: Should be Union[Wait,T]
	def consume( self, state:'ProcessState' ) -> Status:
		if self.queue:
			state.onReceive(self, self.queue.pop(0))
			return Status.STEP
		else:
			self.consumeWait.append(state)
			return Status.WAIT

# -----------------------------------------------------------------------------
#
# PROCESS
#
# -----------------------------------------------------------------------------

## section: Process
##   text|texto
##      The process has 

class Process:

	def __init__( self ):
		# These are static, and should not change once the process has been
		# designed.
		self.slots      = {}
		self.primitives = {}
		self.operations = []

	def start( self, input:Channel, output:Channel ):
		"""Creates a new process state, bound to the given input and output
		channels."""
		state = ProcessState()
		assert state.step == -1, "Process state is already engaged."""
		state.channels["in"]  = input
		state.channels["out"] = output
		state.step            = 0
		state.bindings        = [None] * len(process.slots)
		state.process         = self
		return state

	def step( self, state:'ProcessState' ):
		"""Tries to move the given `state` to the next step."""
		op = self.operations[state.step]
		if op.name == "receive":
			channel = op.attr("channel")
			slot    = op.attr("slot")

			if not channel in state.channels:
				raise NodeError(op, RuntimeError(f"Operation references unknown channel '{channel}', should be one of: {', '.join(repr(_) for _ in state.channels)}"))
			if not slot in self.slots:
				raise NodeError(op, RuntimeError(f"Slot '{slot}' is undefined, should be one of: {', '.join(repr(_) for _ in state.channels)}"))
			return self.do_receive(state, state.channels[channel], self.slots[slot])
		else:
			return NodeError(op,RuntimeError(f"Unspported operation: {op.name}"))

	def do_receive( self, state:'ProcessState', channel:Channel, slot:int ):
		return channel.consume( state)

class ProcessState:

	def __init__( self ):
		self.channels:Dict[str,Channel] = {}
		self.step       = -1
		self.bindings:Optional[List[Any]]  = None
		self.process:Optional[Process] = None

	def onReceive( self, channel:Channel, value:Any ):
		print ("RECEIVED", value)
		step = self.process.step(self) is not Status.WAIT

# -----------------------------------------------------------------------------
#
# PROCESS BUILDER
#
# -----------------------------------------------------------------------------
## text|texto
##   The process builder translates program trees into a `Process` object
##   and corresponding operations.
class ProcessBuilder(TreeProcessor):
	"""Takes an instruction tree and creates a corresponding process object."""

	def __init__( self, process:Optional[Process]=None ):
		super().__init__()
		self.process = None

	def build( self, node:Node ):
		self.process = Process()
		super().build(node)
		return self.process

	def on_primitive( self, node:Node ):
		self.process.primitives[node.attr("id")] = True

	def on_slot( self, node:Node ):
		self.process.slots[node.attr("id")] = len(self.process.slots)

	def on_receive( self, node:Node ):
		channel  = node.attr("channel")
		slot     = node.attr("slot")
		if not channel:
			raise NodeError(op, RuntimeError(f"Operation missing @channel"))
		if not slot:
			raise NodeError(op, RuntimeError(f"Operation missing @slot"))
		assert slot in self.process.slots, f"Missing slot '{slot}', should be one of: {', '.join(_ for _ in self.process.slots)}"
		self.process.operations.append(node)

# -----------------------------------------------------------------------------
#
# MAIN
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
	node = TreeBuilder.MakeNode
	tree = node("process"
		# + is a primitive
		,node("primitive", id="+")
		# A, B and R are slots
		,(node("slot", id=_) for _ in "A B R".split())
		# We receive from 'in' and put in in A
		,node("receive", channel="in",slot="A")
		# We receive from 'in' and put in in B
		,node("receive", channel="in",slot="B")
		# We open the + stream
		,node("open",   process="+",channel="+")
		,node("emit",   channel="+",slot="A")
		,node("emit",   channel="+",slot="B")
		,node("receive", channel="+",slot="R")
	)

	# We print the tree (for reference) and build the process from
	# the AST
	print (tree)
	builder = ProcessBuilder()
	process:Process = builder.build(tree.children)

	# We create an input and output channel, and start the process
	# with these two channels
	in_chan = Channel() ; out_chan = Channel()
	state:ProcessState = process.start(in_chan, out_chan)

	assert in_chan.expects == 0, "The input channel should expect 0 value now"

	# We step the state
	assert process.step(state) is Status.WAIT, "The process should be in waiting state"
	assert state.step == 0, "The state should still be at step 0"
	assert in_chan.expects == 1, "The input channel should expect 1 value now"

	# We put 10 in the channel
	in_chan.put(10)
	assert process.step(state) is not Status.WAIT, "The process should not be in the WAIT step."
	assert state.step == 1, "The state should still be at step 1"

# IDEA: we define a machine for the executor: it manages a stack of processes.
# When a process waits for a h

# EOF - vim: ts=4 sw=4 noet
