Type system
===========


Definining a string type
------------------------

```
```

Definining an array type
------------------------


Fixed size (size = `N`), with value of type `T`

```
(type-template (T N)
	(where
		((type-data-length-fixed? T) true)
	)
	(data-array (N T))
)
```

This given `T=Int64` and `N=10` this will yield:

```
	(data-length 80)
	(data-repeat "<Int64 hash>")
```
