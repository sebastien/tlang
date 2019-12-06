from tlang.tree.model import Node, TreeProcessor, TreeBuilder
from typing import Optional,TypeVar,Generic,Union,Any,Tuple,Dict
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
			return (Control.STEP, self.values.pop(0))

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
		self.step:int = 0
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

	def __init__( self, scheduler:Scheduler, primitives:Dict, processes:Dict[str,Process] ):
		super().__init__()
		self.scheduler = scheduler
		self.primitives = primitives
		self.processes   = processes
		self.state:Optional[ProcessState] = None

	def setState( self, state:ProcessState ):
		self.state = state
		return self

	def on_declare( self, node ):
		self.state.bindings.setdefault(node["slot"], None)
		return Control.STEP

	def on_primitive( self, node ):
		prim = self.primitives[node["name"]]
		args = [self.state.bindings[_["slot"]] for _ in node.children if _.name == "arg"]
		self.state.bindings[node["slot"]] = prim(*args)
		return Control.STEP

	def on_open( self, node ):
		self.state.channels[node["channel"]] = Channel()
		return Control.STEP

	def on_receive( self, node ):
		channel = self.state.channels[node["channel"]]
		status, value = channel.get()
		self.state.bindings[node["slot"]] = value
		# If the channel is waiting, we'll reschedule that process
		# as soon as we have a value
		if status is Control.WAIT:
			channel.join(lambda state=self.state: self.scheduler.schedule(state))
		else:
			print (f"<<< {node['channel']} ← {value}")
		return status

	def on_log( self, node ):
		print (f"━━━ {node['message']}")
		return Control.STEP

	def on_emit( self, node ):
		channel = self.state.channels[node["channel"]]
		if node.hasAttribute("slot"):
			value = self.state.bindings[node["slot"]]
		else:
			value = node["value"]
		channel.put(value)
		return Control.STEP

	def on_start( self, node ):
		process     = self.processes[node["process"]]
		# We create the input/output channels
		in_channel  = Channel()
		out_channel = Channel()
		# We create the subprocess state
		state       = ProcessState(process)
		# Binding th echannels
		state.channels["in"]  = in_channel
		state.channels["out"] = out_channel
		# We bind the channels to the current process
		self.state.channels[node["input"]] = in_channel
		self.state.channels[node["output"]] = out_channel
		# And we schedule the execution
		self.scheduler.schedule(state)
		# Here we step because we don't consume anything at that stage, meaning
		# that the process is only going to be started once we reach a synchronization
		# point (through a receive). However, the procsess could very well be
		# scheduled to start already.
		return Control.STEP

class Executor:

	def __init__( self, primitives, processes:Dict[str,Process] ):
		self.scheduler = Scheduler()
		self.primitives = primitives
		self.processes = processes

	def run( self, process:Process ):
		for i,step in enumerate(self.iter(process)):
			print (f"Step {i}:{step}")

	def iter( self, process:Process ):
		state = ProcessState(process)
		inter = Interpreter(self.scheduler, self.primitives, self.processes)
		self.scheduler.schedule(state)
		while not self.scheduler.isEmpty:
			state = self.scheduler.next()
			inter.setState(state)
			print (f" →  [{state.step}→{len(state.process.operations)-1}]")
			for i in range(state.step, len(state.process.operations)):
				op  = state.process.operations[i]
				res = inter.process(op)
				state.step = i
				if res is Control.STEP:
					print (f"    [{i}/{len(state.process.operations)-1}] {op}")
				else:
					print (f" …  [{i}/{len(state.process.operations)-1}] {op}")
					yield state
					break
			if state.step == len(state.process.operations) - 1:
				print (f"[=] {state.bindings}")
		print (f"Stopped: scheduler is empty: {self.scheduler.scheduled}")

if __name__ == "__main__":
	node = TreeBuilder.MakeNode

	# NOTE: We don't declare in/out channels they're already there
	add = Process(
		node("log", message="Starting add"),
		node("declare",   {"slot":"A"}),
		node("declare",   {"slot":"B"}),
		node("declare",   {"slot":"R"}),
		node("receive",   {"channel":"in", "slot":"A"}),
		node("receive",   {"channel":"in", "slot":"B"}),
		node("primitive", {"name":"add","slot":"R"},
			node("arg", slot="A"),
			node("arg", slot="B")),
		node("emit",      {"channel":"out", "slot":"R"}),
	)

	mul = Process(
		node("log", message="Starting mul"),
		node("declare",   {"slot":"A"}),
		node("declare",   {"slot":"B"}),
		node("declare",   {"slot":"R"}),
		node("receive",   {"channel":"in", "slot":"A"}),
		node("receive",   {"channel":"in", "slot":"B"}),
		node("primitive", {"name":"mul", "slot":"R"},
			node("arg", slot="A"),
			node("arg", slot="B")),
		node("emit",      {"channel":"out", "slot":"R"}),
	)
	main = Process(
		node("open", channel="out"),
		node("start", process="mul", input="m_in", output="m_out"),
		node("declare", slot="A"),
		node("declare", slot="R"),
		node("emit", channel="m_in", value=10),
		node("start", process="add", input="a_in", output="a_out"),
		node("emit", channel="a_in", value=1),
		node("emit", channel="a_in", value=2),
		node("receive", channel="a_out", slot="A"),
		node("emit", channel="m_in", slot="A"),
		node("receive", channel="m_out", slot="R"),
		node("emit", channel="out", slot="R"),
	)
	PRIMITIVES = {
		"add":lambda a,b: a + b,
		"mul":lambda a,b: a * b,
	}
	PROCESSES  = {
		"add": add,
		"mul": add,
	}

	thread = Executor(PRIMITIVES, PROCESSES).run(main)
	# state = next(thread)
	# state.channels["in"].put(1)
	# state = next(thread)
	# state.channels["in"].put(10)
	# state = next(thread)
	# print (state.step)


# EOF - vim: ts=4 sw=4 noet
