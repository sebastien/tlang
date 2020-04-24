from typing import List,Dict,Optional,Any

class Singleton:
	ALL:Dict[str,'Singleton'] = {}

	@classmethod
	def Get( cls, name ):
		if name not in cls.ALL:
			cls.ALL[name] = Singleton(name)
		return cls.ALL[name]

	def __init__( self, name:str ):
		self.name = name

	def __repr__( self ):
		return f"#{self.name}"

class Slot:

	def __init__( self, value=None ):
		self.value:Optional[Any] = value

class Context:

	def __init__( self, parent:'Context'=None, reference=None ):
		self.parent:Optional[Context] = parent
		self.slots:Dict[str,Slot] = {}
		self.reference = reference

	def setReference( self, reference ):
		self.reference = reference
		return self

	def listReachableSlots( self ) -> List[str]:
		res = []
		context:Optional[Context] = self
		while context:
			for k in context.slots:
				if k not in res:
					res.append(k)
			context = context.parent
		return res

	def derive( self, reference ) -> 'Context':
		return Context(self, reference=reference)

	def has( self, name:str ) -> bool:
		return name in self.slots

	def get( self, name:str ) -> Optional[Any]:
		return self.slots.get(name)

	def define( self, name:str, value:Any ):
		# We don't allow to defined twice
		assert name not in self.slots
		self.slots[name] = value
		return value

	def resolve( self, name:str )->Optional[Slot]:
		if name in self.slots:
			return self.slots[name]
		elif self.parent:
			return self.parent.resolve(name)
		else:
			return None

	def seal( self ):
		def no_define( name:str, value:Any ):
			raise RuntimeError(f"Context is sealed, cannot define slot '{name}'")
		self.define = no_define

META_INVOCATION = "__tlang_invocation__"

# TODO: We probably want to move these
#  @symbol Flag that denotes an eager evaluation
EAGER = 0
#  @symbol Flag that denotes an evaluation of the AST
VALUE = 0
#  @symbol Flag that denotes a lazy evaluation (opposite of `EAGER`)
LAZY  = pow(2,0)
#  @symbol Flag that denotes a data evaluation (ie. no invocation, just the data)
DATA  = pow(2,1)
#  @symbol#NODE: Flag that denotes that the argument should be passed as AST
NODE  = pow(2,2)

class Argument:

	def __init__( self, name:str, index:int, flags:int=EAGER ):
		self.name = name
		self.index = index
		self.flags = flags

	def __repr__( self ):
		return f"{self.name}#{self.flags}[{self.index}]"

class Rest(Argument):
	pass

Arguments = List[Argument]

def invocation( **kwargs ):
	"""Adds a protocol annotation to a callable object, descibing how
	the arguments should be passed/evaluated."""
	def decorator( f ):
		args = []
		rest = None
		for k,v in kwargs.items():
			if k == "__":
				rest = Rest(k, -1, v)
			else:
				args.append(Argument(k,len(args),v))
		if rest:
			rest.index = len(args)
			args.append(rest)
		setattr(f, META_INVOCATION, args)
		return f
	return decorator

class Channel:

	def __init__( self ):
		self.count = 0
		self.queue = []

	def writeLazy( self, evaluator ):
		self.queue.append((0, evaluator))
		self.count += 1
		return self

	def write( self, value ):
		self.queue.append((1, value))
		self.count += 1
		return self

	def hasNext( self ):
		return self.count > 0

	def consume( self ):
		if self.count > 0:
			self.queue.pop(0)
		return self

	def peek( self ):
		if self.count > 0:
			v = self.queue[0]
			if v[0] == 0:
				# We evaluate
				v = (1, v[1]())
				self.queue[0] = v
			return v[1]
		else:
			return None

	def read( self ):
		# TODO: We should raise an exception when count == 0
		v = self.peek()
		self.consume()
		return v

# EOF - vim: ts=4 sw=4 noet
