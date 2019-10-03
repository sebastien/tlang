#include <stdint.h>
#include <stdbool.h>

// The core idea behind a VM is that it becomes possible to write programs
// that perform optimizied traversals and optimized updates of tree data,
// independently of the API.
//
// A backend can then be synthesized based on a schema and a set of queries,
// so that its data structure and operation implementation is optimal regarding
// the use case.
//
// Using a VM makes it possible to compile tree creation and manipulation
// programs, exchange them and replay them with different backends.

#ifdef HEADER
#define DEF \/\*
#define END \*\/
#endif

// TODO: We might want a set of compact OPCODEs, so that programs can
// be written by hand and can be easily readable/debuggable.
//
// === Nodes
#define OP_NODE_ID              = (uint8_t)0x10
#define OP_NODE_TYPE_GET            = (uint8_t)0x11
#define OP_NODE_TYPE_SET        = (uint8_t)0x12

OP_NODE_CHILD_REMOVE
OP_NODE_CHILD_INSERT
OP_NODE_CHILD_COUNT
OP_NODE_SIBLING_GET_NEXT
OP_NODE_SIBLING_GET_PREVIOUS

#define OP_NODE_REMOVE_CHILD    = (uint8_t)0x13
#define OP_NODE_INSERT_CHILD    = (uint8_t)0x14
#define OP_NODE_COUNT_CHILDREN  = (uint8_t)0x15
#define OP_NODE_NEXT_SIBLING    = (uint8_t)0x16
#define OP_NODE_PREV_SIBLING    = (uint8_t)0x17
#define OP_NODE_PARENT          = (uint8_t)0x18
#define OP_NODE_FIRST_CHILD     = (uint8_t)0x19
#define OP_NODE_COUNT_ATTR      = (uint8_t)0x1A
#define OP_NODE_GET_ATTR        = (uint8_t)0x1B
#define OP_NODE_PREV_ATTR       = (uint8_t)0x1C
#define OP_NODE_NEXT_ATTR       = (uint8_t)0x1D



// === Attributes
#define OP_ATTR_CLEAR        = 0x22
#define OP_ATTR_ID           = 0x22
#define OP_ATTR_TYPE         = 0x22
#define OP_ATTR_SET_BOOL     = 0x20
#define OP_ATTR_SET_INT      = 0x20
#define OP_ATTR_SET_NUM      = 0x20
#define OP_ATTR_SET_STR      = 0x20
#define OP_ATTR_GET_BOOL     = 0x21
#define OP_ATTR_GET_INT      = 0x21
#define OP_ATTR_GET_NUM      = 0x21
#define OP_ATTR_GET_STR      = 0x21


#define OP_NODE_COUNT_ATTRIBUTES = 0x30


#define IMPLEMENT_PREFIX = tlang_backend_tree_Engine

typedef uint32_t NodeID;
typedef uint32_t AttributeID;
typedef uint64_t StreamID;
typedef uint64_t TransactionID;

typedef uint8_t (*OnNodeCallback)      (StreamID stream, NodeID node);
typedef uint8_t (*OnAttributeCallback) (StreamID stream, AttributeID attr);
typedef uint8_t (*OnStringCallback)    (StreamID stream, const char* string);
//typedef uint8_t (*OnNumber)            (StreamID stream, float64_t   number);
typedef uint8_t (*OnIntegerCallback)   (StreamID stream, int64_t     number);
typedef uint8_t (*OnBoolCallback)      (StreamID stream, bool        value);

// typedef uint8_t *(OnTransactionStart)  (StreamID stream, TransactionID transaction);
// typedef uint8_t *(OnTransactionCommit) (StreamID stream, TransactionID transaction);
// typedef uint8_t *(OnTransactionEnd)    (StreamID stream, TransactionID transaction);

typedef struct tlang_vm_State {
	AttributeID attribute;
	NodeID      node;
} tlang_vm_State;

struct tlang_vm_Stream {
	StreamID stream;
	OnNodeCallback*      onNode;
	OnAttributeCallback* onAttribute;
	OnStringCallback*    onString;
	OnIntegerCallback*   onInteger;
	OnBoolCallback*      onBool;
	// onNumber;
	onBool;
	// onFail;
	// onTransactionStart;
	// onTransactionCommit;
	// onTransactionCancel;
}


void tlang_vm_Engine_step( tlang_vm_State* state, uint8_t opcode ) {
}

// EOF
