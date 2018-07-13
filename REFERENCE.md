
Design principles
=================

`tlang`'s API is defined in an [S-Expression format](https://en.wikipedia.org/wiki/S-expression)

Type system
============

The first part of the type system is focused on defining mapping
between abstract data and its physical representation: in other words, how
data is stored in memory. The type system, at its very basic level, is a way to define
how to read and write data.

We are going to use a few specific terms, which are defined here for convenience:

- A _value_ denotes a specific value, like a given number, string, array, etc.
- A _type_ represents a set of possible values. 
- A type is _concrete_ when it has all the information to determine the type
  of values it represents.
- A type is _abstract_ (also called _higher-order_) when it need more information
  to expand into a concrete type.

Specifying data encoding
------------------------

### Encoded data size

A data value can be either of `fixed` size or of `variable` size. This is
denoted by `data-size-fixed` constraint.

```
(data-size-fixed BOOL)
(data-size-fixed? TYPE) → BOOL
```

The actual data size of the data, whether fixed or variable can be specified
as. In case of a variable data size, this will set the minimum size of the
data for all values of that type.

```
(data-size NUMBER)
(data-size? TYPE) → NUMBER
```

### Atomic data

Data can be encoded in many different ways. The most obvious one is the mapping
to corresponding low-level C types:

- `U` (prefix) for *unsigned*
- `INT` for *integers*, `FLOAT` for *floating points*
- `CHAR` for *8-bit* ASCII (or other 8-bit encoding) characters.
- `BIT` for *raw bits*
- `{8,16,32,64,128}` for the size (in bits)

```
(data-encoding :UINT64)
(data-encoding? TYPE) → ENCODING
```

Using `data-encoding` automatically implies a corresponding `data-size` for the
type.

### Fixed-size composite data

Data can then be encoded in structures, which are either fixed or dynamic.
Fixed structures have a known length, that won't change along the value's 
lifetime.

The `data-struct` construct defines a contiguous, labeled sequence of 
memory cells.

```
(data-struct SPECIFICATION…)
```

```
(data-struct
	(data-encoding FLOAT64)
	(data-encoding FLOAT64)
	(data-encoding FLOAT64)
)
```

which implies

```
;; True, because the length of a structure is the sum of length of its members.
(equals?
	(data-length? _)
	(sum
		(data-length (data-field? _ 0))
		(data-length (data-field? _ 1))
		(data-length (data-field? _ 2))
	)
)
```

Fixed arrays can be specified with the `data-repeat` construct:

```
(data-repeat COUNT SPECIFICATION…)
```

Here's how we would declare an array of 10 floats:

```
(data-repeat 10
	(data-encoding FLOAT64)
))
```

and here's how we would declare an array of 10 of the float triples
declared above:

```
(data-repeat 10
	(data-struct
		(data-encoding FLOAT64)
		(data-encoding FLOAT64)
		(data-encoding FLOAT64)
))
```

You can specify more than one element in the array, in which case
they will each be contiguous. Here is how we would create a columnar
version of the 10 float triples defined above.

```
(data-repeat 10
	(data-encoding FLOAT64)
	(data-encoding FLOAT64)
	(data-encoding FLOAT64)
)
```

It is interesting to notice that `(data-struct DATA…)` is strictly
equivalent to `(data-repeat 1 DATA…)`.

### Variable-sized composite data

We've seen how we can define data with a fixed, known size. But what about a 
variable array, or a C string of character. For a start, this set of data types
all imply `(data-size-fixed 0)`, which means their size is not fixed but variable.

The `data-repeat` form can take `*` to denote many elements that might be repeated
next to each other.

```
(data-repeat *
	(data-encoding FLOAT64)
	(data-encoding FLOAT64)
	(data-encoding FLOAT64)
)
```

Now, we call a type with a `(data-repeat * ….)` clause _incomplete_, because
it does not contain an explicit way of knowing when it ends. It is incomplete because 
it needs that extra information to know the actual size of one of the values it represents.
Let's take a C string, for instance. A C string is a sequence of characters ending with 0.

```
(data-repeat (data-repeat-end (data-value (data-encoding CHAR) 0)
	(data-encoding CHAR)
)

```

Here we introduce the `data-repeat-end` and `data-value` clauses.

```
(data-repeat-end VALUE)
```

The `data-repeat-end` expects a concrete _value_ used as a sentinel to denote the 
end of the data. This means that the size of the data is _implicit_: it can
be discovered by reading the data up until the sentinel is recognized.

```
(data-value TYPE)
(where (type-concrete? TYPE))
```

The `data-value` clause expands to a concrete series of bits that represent
the encoding of concrete value to be used as a sentinel.

```
(data-repeat (data-repeat-count (data-encoding UINT18))
	(data-encoding CHAR)
)
```

Here we use the `(data-repeat-count DATA)` declaration to denote that the number of 
sequential elements to be repeated is defined in the value encoded as 
an `UINT18`.

This format works the same with a columnar layout

```
(data-repeat (data-repeat-count (data-encoding UINT18))
	(data-encoding FLOAT64)
	(data-encoding FLOAT64)
	(data-encoding FLOAT64)
)
```

### Labelling elements

Places within the data can be assigned labels. For instance, if your float
tripe is actually a vector in 3D space Euclidean, you'd consider the triple
to be `(x,y,z)` instead of three anonymous floats.

To do so, you can use the `(data-label DECL)` to wrap a declaration in a label:

```
(data-struct
	(data-label "x" (data-encoding FLOAT64))
	(data-label "y" (data-encoding FLOAT64))
	(data-label "z" (data-encoding FLOAT64))
)
```

### Data conversion and re-encoding

Now we have the basic building blocks to define low level-types: the encoding
primitives of atomic elements (like numbers), and ways to combine then in 
structures of fixed and dynamic size.

The next step is to express how these encodings of data can relate to each
other.  For numbers, we can define the relation of _inclusion_, which says that
*A includes B* if all elements of *B* can be found in *A*. From a data encoding
perspective, this translates into saying "can I re-encode a value of B into a
value of A", which is expressed by the `(data-encodable? B A)` relation:

```
;; True, as all INT8 values sare part of INT32 values
(data-encodable? INT8  INT32) 

;; False, as for instance 256 cannot be represented as an INT8
(data-encodable? INT32 INT8) 

;; False, as you can't convert a negative to an unsigned number 
(data-encodable? UINT32 INT32)
```

Now, let's see if we have two fixed arrays, A and B. We introduce the
`(data-def NAME SPECIFICATION…)` declaration and the `(data-ref NAME)` to
respectively define and reference a specific data specification.

```
(data-def "A"
	(data-repeat 10 (data-encoding UINT8))
)
(data-def "B"
	(data-repeat 10 (data-encoding UINT16))
)
```

we will have

```
;; True, A's content can be re-encoded in B's content, and A and B
;; have the same size.
(data-encodable? (data-ref "A") (data-ref "B"))

;; False, B's content cannot be re-encoded in B's content
(data-encodable? (data-ref "B") (data-ref "A")) ;; False
```

likewise,

```
(data-def "A"
	(data-repeat 5 (data-encoding UINT8))
)
(data-def "B"
	(data-repeat 10 (data-encoding UINT8))
)
```

will yield

```
;; True, A is smaller than B
(data-encodable? (data-ref "A") (data-ref "B"))

 ;; False, B is larger than A
(data-encodable? (data-ref "B") (data-ref "A"))
```

Specifying types
----------------

We've seen how we can define data encodings, from atoms to composite elements,
from fixed sized to variable size, and how we can identify is one can be
converted to the other.

While some values may have strictly the same value encoding, they might not
have the same meaning. Maybe we're using a `FLOAT64` to store the temperature,
but one is in Celcius, the other one in Fahrenheit.  Technically, these values
have compatible encodings, but they don't represent the same thing. A `0` celcius
is *not* the same as a `0` Fahrenheit.

To express this, we define types and define relations between then. We
introduce the `(type-def NAME TYPESPEC…)` directive to define a type,
in a similar way to `(data-def …)`:

```
;; We define an encoding called TEMPARATURE, which is a FLOAT64 atom
(data-def TEMPERATURE (data-encoding FLOAT64))

;; We define two types with that encoding
(type-def Celcius    (type-encoding TEMPERATURE))
(type-def Fahrenheit (type-encoding TEMPERATURE))
```

Now, we've seen that Celcius and Fahrenheit are not the same thing, but
we could at least say that they're numbers -- their interpretation is different,
but they still are essentially numbers.

```
;; We define a Number type that is encoded as a FLOAT64 value.
(type-def Number
	(type-encoding (data-encoding FLOAT64)))
```

We can explicitly create relations between `Celcius`, `Fahrenheit` and `Number`.
For this, we introduce the `(type-sub CHILD PARENT)` that defines the `CHILD`
type as sub-type of the `PARENT` type.

```
;; We say that Celcius is a subtype of number. This works because both 
;; encodings are compatible:
(type-sub Celcius Number)
(type-sub Fahrenheit Number)
```

This is possible because the following expressions are all true:

```
;; All these are True, because all these type values are encoded
;; as FLOAT64.
(data-encodable? (type-encoding? Celcius)    (type-encoding? Number))
(data-encodable? (type-encoding? Fahrenheit) (type-encoding? Number))
(data-encodable? (type-encoding? Fahrenheit) (type-encoding? Celcius))
(data-encodable? (type-encoding? Celcius)    (type-encoding? Fahrenheit))
```
