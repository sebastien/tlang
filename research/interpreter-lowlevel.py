
## This aims to be a C-style implementation of a low level interpreter.

State   = namedtuple("State_t", ("counter", int))
SlotID  = int

# -----------------------------------------------------------------------------
#
# TREE API
#
# -----------------------------------------------------------------------------

def tlang_tree_node_create():
	pass

def tlang_tree_node_append( node:Node, child:Node ):
	pass

def tlang_tree_node_remove_at( node:Node, index:int ):
	pass

def tlang_tree_node_index( node:Node, node: Node) -> int:
	pass

def tlang_tree_node_index( node:Node, node: Node) -> int:
	pass

def tlang_tree_attr_get( node:Node, name:str ) -> Any
	pass

def tlang_tree_attr_set( node:Node, name:str ) -> Any
	pass

# NOTE: Not sure about that
# def tlang_tree_attr_add( node:Node, name:str ) -> Any
# 	pass
# 
# def tlang_tree_attr_remove( node:Node, name:str ) -> Any
# 	pass

# -----------------------------------------------------------------------------
#
# RUNTIME DATA
#
# -----------------------------------------------------------------------------

def runtime_list_create( size:int ) -> List:
	pass

def runtime_list_set( l:List, index:int, element:Any ) -> None:
	pass

def runtime_list_append( l:List, element:Any ) -> None:
	pass

def runtime_list_expand( l:List, l:List ) -> None:
	pass

def runtime_list_remove_at( l:List, index:int) -> None:
	pass

def runtime_scope_push( scope:Scope ) -> Scope:
	pass

def runtime_scope_pop( scope:Scope ) -> Scope:
	pass

def runtime_scope_resolve( scope:Scope, slot:SlotID ) -> Any:
	pass

def runtime_scope_set( scope:Scope, slot:SlotID, value:Any ) -> None:
	pass

def runtime_scope_get( scope:Scope, slot:SlotID, value:Any ) -> None:
	pass

def runtime_slot_id( name:str ):
	pass

def runtime_invoke_direct_0( function ):
	pass

def runtime_invoke_direct_1( function, a0 ):
	pass

def runtime_invoke_direct_2( function, a1 ):
	pass

def runtime_invoke_direct_3( function, a2):
	pass

def runtime_invoke_direct_4( function, a3 ):
	pass

# -----------------------------------------------------------------------------
#
# PRIMITIVES
#
# -----------------------------------------------------------------------------

def primitive_lambda( ):
	pass

# EOF - vim: ts=4 sw=4 noet
