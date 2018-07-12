== TLang
-- A Tree Processing Language

The core idea of the T language is to create a language that lends itself well to
creating, manipulating and transforming trees.

Its core features are:

- **Incremental**: T offers core primitives to write incremental algorithm
  that can transform *deltas* into *data transformations*.

- **Typed**:

- **Capabilities**:

- **Meta-programming**

Concepts
========

References
----------

References are a `(value, type, capabilities)`, where:

- `value` is the actual value wrapped by the reference
- `type` is the most specific type known about the given `value`
- `capabilities` is a map of `capability→value` indicating what can
  be done with the reference.

```
(VALUE TYPE CAPABILITY)
```

Primitives:

```
(ref-make VALUE)
```

Type
----

A type is a series of constraints and properties associated with a value.
Some of these properties refer to the way the value is laid out in memory,
or the operations that can be done with it.


Here is an example encoding of an `uint8`

```
(type-data-size 8)           # This is a 8bit value
(type-data-encoding :UINT8)  # It is a numeric type encoded as an unsigned integer numeric
```

Here is an example encoding of a `string` (or an array, for that matter).

```
(type-struct
	(type-struct-member     length
		(type-data-size     64)
		(type-data-encoding :UINT64)
	)
	(type-struct-member data
		(type-data-size .length)  # This tells that the size is defined in the `length` structure
	)
)
``` 

Primitives:

```
:UINT64
:UINT32
```

```
(type-data-size ...)
(type-data-encoding ...)
(type-struct ...)
(type-struct-member ...)
```

Capabilities
------------

Capabilities define what can be done with a reference, and constrains the
following operations:

- *Aliasing*: can a reference be assigned to another name?
- *Shared*: can a reference be shared with another block, function, construct, thread, process?
- *Access*: can a reference be accessed?
- *Mutated*: can a reference be mutated?
- *Deleted*: can a reference be deleted?

