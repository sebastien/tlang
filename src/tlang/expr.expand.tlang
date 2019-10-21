;; @title Expression Expansion
;; @updated 2019-02-15

;; @texto
;; The expression language can contain template
;; expressions denoted by the `expr-value-template`
;; nodes. We want to introduce a `@meta-level`
;; attribute that indicates how many expansions
;; need to be applied until the expression has
;; no more templates.

;; @attribute expr*/meta-level
;; @texto
;; The meta level attribute of an expression is the
;; maximum meta-level of any sub-expression plus
;; 1 if the expression contains 
(attr
	({expr-*:NODE}  @meta-level)
	(add
		(max     ./expr-*/@meta-level)
		(int (has? ./expr-value-template))))

