from enum import Enum
from typing import Optional,List,Dict
import os,sys

__doc__ = """
A test module to experiment with ways to minimize the number of traversals.
"""

class Axis(Enum):
	CURENT = 0
	PARENT = 1
	ANCESTORS = 2
	CHILDREN = 3
	DESCENDANTS = 4
	AFTER = 5
	BEFORE = 6

class Transform:

	@classmethod
	def ParseString( cls, text ):
		"""Format is like `SRC/@ATTR  → DST/@ATTR : AXIS DEPTH?`"""
		for line in text.split("\n"):
			if line.strip():
				yield cls.ParseLine(line)

	@classmethod
	def ParseLine( cls, line ):
		nodes,axis = line.rsplit(":",1)
		src,dst    = [_.split("/",1) for _ in nodes.split("->",1)]
		axis       = [_ for _ in axis.strip().split() if _.strip()]
		depth      = int(axis[1]) if len(axis) >= 2 else 0
		axis       = axis[0].strip()
		src_node   = src[0].strip()
		src_attr   = src[1].strip() if len(src) > 1 else None
		dst_node   = dst[0].strip()
		dst_attr   = dst[1].strip() if len(dst) > 1 else None
		return Transform(src_node, src_attr, dst_node, dst_attr, axis, depth)

	def __init__( self, srcNode:str, srcAttr:Optional[str], dstNode:str, dstAttr:Optional[str], axis:str, depth=0 ):
		self.srcNode = srcNode
		self.srcAttr = srcAttr
		self.srcKey  = srcNode + ("/" + str(srcAttr) if srcAttr else "")
		self.dstNode = dstNode
		self.dstAttr = dstAttr
		self.dstKey  = dstNode + ("/" + str(dstAttr) if dstAttr else "")
		self.axis    = axis
		self.depth   = depth

	def __str__( self ):
		sa = "/" + self.srcAttr if self.srcAttr else ""
		da = "/" + self.dstAttr if self.dstAttr else ""
		d  = " " + str(self.depth) if self.depth else ""
		return "{0}{1} → {2}{3} : {4}{5}".format(self.srcNode, sa, self.dstNode, da, self.axis, d)

	def __repr__( self ):
		return "<Transform {0}>".format(str(self))

class Optimizer:

	def __init__( self ):
		self.transforms:List[Transform]   = []
		self.sources:Dict[str,Transform] = {}

	def add( self, transform:Transform ) -> 'Optimizer':
		self.transforms.append(transform)
		self.sources[transform.srcKey] = transform
		return self

	def query( self, query:str ):
		query_list:List[str] = [_.strip() for _ in query.strip().split()]
		for q in query_list:
			node_attr = [_.strip() for _ in q.split("/")]
			node = node_attr[0]
			attr = node_attr[1] if len(node_attr) > 1 else None
			yield self.getTraversalFor(node, attr)

	def getTraversalFor( self, node:str, attr:Optional[str] ):
		key = node + ("/" + attr if attr else "")
		assert key in self.sources, "No transform registered for `{0}` : use one of ({1})".format(key, ", ".join(self.sources.keys()))
		trn = self.sources.get(key)

if __name__ == "__main__":
	opt = Optimizer()
	query = sys.argv[1]
	for path in sys.argv[2:]:
		if os.path.exists(path):
			with open(path, 'rt') as f:
				text = f.read()
		else:
			text = path
		for t in Transform.ParseString(text):
			opt.add(t)
	for q in opt.query(query):
		print (q)

# EOF - vim: ts=4 sw=4 noet
