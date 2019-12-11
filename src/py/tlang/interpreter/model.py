from typing import List,Dict,Optional,Any

class Slot:

	def __init__( self, value=None ):
		self.value:Optional[Any] = value

class Context:

	def __init__( self, parent:'Context'=None ):
		self.parent:Optional[Context] = parent
		self.slots:Dict[str,Slot] = {}

	def derive( self ) -> 'Context':
		return Context(self)

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

##   symbol#EAGER: Flag that denotes an eager evaluation
EAGER = 0
##   symbol#VALUE: Flag that denotes an evaluation of the AST
VALUE = 0
##   symbol#LAZY: Flag that denotes a lazy evaluation (opposite of `EAGER`)
LAZY  = pow(2,0)
##   symbol#DATA: Flag that denotes a data evaluation (ie. no invocation, just the data)
DATA  = pow(2,1)
##   symbol#NODE: Flag that denotes that the argument should be passed as AST
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

# EOF - vim: ts=4 sw=4 noet
