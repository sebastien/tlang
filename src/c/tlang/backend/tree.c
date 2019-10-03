#include <stdint.h>
#include <sys/types.h>

#ifdef HEADER
#define DEF \/\*
#define END \*\/
#endif

typedef struct Node Node;
typedef uint32_t NodeID;
typedef uint32_t AttributeID;

struct Node {
	NodeID id;
	Node* parent;
	Node* firstChild;
	Node* nextSibling;
	Node* previousSibling;
	Node* lastChild;
};

typedef struct Attribute Attribute;
union AttributeValue {
	uint64_t    number;
	double      real;
	const char* text;
} AttributeValue;

struct Attribute {
	AttributeID    id;
	uint8_t        type;
	size_t         length;
	AttributeValue value;
};

// TODO: The engine should implement the VM operations, nothing more than that.

// inline void tlang_backend_tree_Engine_initState (void) {
// }
// 
// inline NodeID tlang_backend_tree_Engine_createNode (void) {
// }
// 
// inline void tlang_backend_tree_Engine_removeChild (NodeID) {
// }
// 
// inline void tlang_backend_tree_Engine_setAttribute (NodeID) {
// }
