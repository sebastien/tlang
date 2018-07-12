== TLang Implementation


Implementation Language
=======================

`tlang` should be implemented in a **compiled language** (for speed), that
can compile to *native* code as well as *web assembly*. `tlang` is by no means
meant to be a general, full-featured programming language, but rather be used
as a DSL (or an engine) to process and apply *incremental transformations*
to hierarchical data.

Java is an interesting contender given its portability and its recent capacity
to compile to WebAssembly (TeaVM) and native code. Its syntax is not ideal, though,
and Kotlin might be better suited. Kotlin has the advantage of also offering
an LLVM-based backend.

An instrumented C implementation would be possible, but the lack of safety 
features makes it likely that a lot of time will be spent fixing or preventing
errors.

Rust would be a good choice, except that its learning curve is steep and most
of the code written while learning Rust would need to be rewritten in the long run.

Go would be a balanced choice between portability and performance, at the cost
of having a language that might be a little bit too simple.

Scheme is an appealing option, given that it is well-suited for
meta-programming and can be compiled to C (using Chicken Scheme) or native
executables (using Chez Scheme), but it's quite fragmented and does not have
first-class WebAssembly support. Also, the memory footprint of functional
languages tend to be quite large.

Constraints solver
==================

Both *types* and *capabilities* can be represented as constraints, which can
be combined together.

Let's imagine that we have N unique, disjoint capability pairs `(capability,value)`, and
we have the set `R` of relations like `{share,alias,read,write}` (we might even
add `access,resolve,invoke` to that). We then have a "truth matrix" that tells
which operations are valid (`1`) for a given capability.

```
    N0 N1 N2 … NN
R0  0  1  0  …  1
R1  1  0  1  …  0
R2  0  1  1  …  0
…   …  …  …  …  …
RN  1  0  0  …  1
```

We can then define a capability as a **bitmap vector** of `N` bits, capable
of representing all the combinations between all the capabilities. Given two
capability vectors `V0`, `V1`, we can define a matrix (probably a sparse matrix)
that outputs the corresponding vector in `R`, which *in fine* tells which
relations are valid given the specific combination of capabilities.

The same principle can be applied for a type system, except the original "truth matrix"
might is going to be square. Let's imagine that `T` is the set of 
all *type pairs* `(type-constraint,value)`, we can define a matrix like so:

```
    T0 T1 T2 … TN
T0  1  2 -2  …  1
T1  -2 1  1  …  0
T2  2  1  1  …  0
…   …  …  …  …  …
TN  1  0  0  …  1
```

where a value of `0` means the types are incompatible, `1` means the types
are *identical*, `-2` means the row type is a **superset** (more general, less constrained)
and `2` means the row type is a **subset** (more specific, more constrained). We might even
be able to give greater/smaller numeric ids by combining results based on a criteria
to be determined.

Note that this matrix is going to be sparse (most types are going to be disjoint),
and symetrical-ish (the symetric value with respect to the diagonal is going to be
the negation of the cell value).

Like with the capabilities, a specific type could then be encoded as a bitmap vector
of `T` bits.

The main issue in both cases is that the disjoint pairs are probably going to be
a large number, probably in the thousands or tens of thousands. Taking the worst
case scenario, that would mean a little bit more than 1Kb of data per type.

These large numbers could be hashed using a one-way hash function that is built
to reduce the size of numbers with frequent occurrences. This could be as simple
as sorting the values in an array by decreasing order of frequency and using a variable
size encoding to store the index of the key within that array.

The goal being that operations of retrieval given a couple `(N,R)` or `(T,T)`
are as fast as possible for values that have a lot of occurences.

These large matrices should be statically created based on a pre-established
dictionary of available constraints.




