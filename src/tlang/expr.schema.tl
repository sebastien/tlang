;; T-Lang Expression Language Schema
;; 2019-02-14 -> 2019-02-15

(schema

	(expr-comment      {(@value type-string):VALUE_STRING})

	(expr-value-number (@value type-number))

	(expr-value-string VALUE_STRING)

	(expr-value-ref    VALUE_STRING)

	(expr-value-symbol VALUE_STRING)

	;; Composites

	(expr-value-list {(many-of //expr-value* expr-comment):CONTENT})

	(expr-value-invocation //expr-value* CONTENT)

	(expr CONTENT)

)

;; EOF
