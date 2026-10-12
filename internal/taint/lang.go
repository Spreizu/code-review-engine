package taint

// syntax describes the node kinds of one grammar family that the analysis needs.
type syntax struct {
	funcs     set // function-like nodes analysed on their own
	calls     set // call nodes
	news      set // constructor calls (callee normalised to "new T")
	assigns   set // assignment / declaration nodes
	ifs       set
	ternaries set
	loops     set
	switches  set
	returns   set
	strings   set // string literals without interpolation are constants
	idents    set // variable references
	members   set // member access / subscript nodes (source candidates)
	compare   set // nodes whose value is a boolean (never tainted)
	casts     set
	pseudo    map[string]string // statement kind -> pseudo callee (echo, include, backticks)
	numbers   set
	trues     set
	falses    set
}

type set map[string]bool

func mk(xs ...string) set {
	s := set{}
	for _, x := range xs {
		s[x] = true
	}
	return s
}

var langs = map[string]*syntax{
	"java": {
		funcs:     mk("method_declaration", "constructor_declaration", "lambda_expression", "compact_constructor_declaration"),
		calls:     mk("method_invocation"),
		news:      mk("object_creation_expression"),
		assigns:   mk("variable_declarator", "assignment_expression"),
		ifs:       mk("if_statement"),
		ternaries: mk("ternary_expression"),
		loops:     mk("for_statement", "enhanced_for_statement", "while_statement", "do_statement"),
		switches:  mk("switch_expression", "switch_statement"),
		returns:   mk("return_statement"),
		strings:   mk("string_literal", "character_literal"),
		idents:    mk("identifier"),
		members:   mk("field_access", "array_access"),
		compare:   mk("instanceof_expression"),
		casts:     mk("cast_expression"),
		numbers:   mk("decimal_integer_literal", "hex_integer_literal", "octal_integer_literal", "binary_integer_literal"),
		trues:     mk("true"), falses: mk("false"),
	},
	"kotlin": {
		funcs:    mk("function_declaration", "lambda_literal", "anonymous_function", "secondary_constructor", "getter", "setter"),
		calls:    mk("call_expression"),
		assigns:  mk("property_declaration", "assignment"),
		ifs:      mk("if_expression"),
		loops:    mk("for_statement", "while_statement", "do_while_statement"),
		switches: mk("when_expression"),
		returns:  mk("jump_expression"),
		strings:  mk("string_literal", "character_literal"),
		idents:   mk("identifier", "simple_identifier"),
		members:  mk("navigation_expression", "index_expression"),
		compare:  mk("check_expression", "is_expression", "in_expression"),
		casts:    mk("as_expression"),
		numbers:  mk("number_literal", "integer_literal"),
		trues:    mk("true"), falses: mk("false"),
	},
	"python": {
		funcs:     mk("function_definition", "lambda"),
		calls:     mk("call"),
		assigns:   mk("assignment", "augmented_assignment", "named_expression"),
		ifs:       mk("if_statement"),
		ternaries: mk("conditional_expression"),
		loops:     mk("for_statement", "while_statement"),
		switches:  mk("match_statement"),
		returns:   mk("return_statement"),
		strings:   mk("string"),
		idents:    mk("identifier"),
		members:   mk("attribute", "subscript"),
		compare:   mk("comparison_operator", "not_operator"),
		numbers:   mk("integer"),
		trues:     mk("true"), falses: mk("false"),
	},
	"javascript": {
		funcs:     mk("function_declaration", "function_expression", "function", "arrow_function", "method_definition", "generator_function_declaration", "generator_function"),
		calls:     mk("call_expression"),
		news:      mk("new_expression"),
		assigns:   mk("variable_declarator", "assignment_expression", "augmented_assignment_expression"),
		ifs:       mk("if_statement"),
		ternaries: mk("ternary_expression"),
		loops:     mk("for_statement", "for_in_statement", "while_statement", "do_statement"),
		switches:  mk("switch_statement"),
		returns:   mk("return_statement"),
		strings:   mk("string"),
		idents:    mk("identifier", "shorthand_property_identifier_pattern"),
		members:   mk("member_expression", "subscript_expression"),
		compare:   mk("unary_expression_not"),
		casts:     mk("as_expression", "satisfies_expression", "non_null_expression", "type_assertion"),
		numbers:   mk("number"),
		trues:     mk("true"), falses: mk("false"),
	},
	"php": {
		funcs:     mk("function_definition", "method_declaration", "anonymous_function", "anonymous_function_creation_expression", "arrow_function"),
		calls:     mk("function_call_expression", "member_call_expression", "scoped_call_expression", "nullsafe_member_call_expression"),
		news:      mk("object_creation_expression"),
		assigns:   mk("assignment_expression", "augmented_assignment_expression", "reference_assignment_expression"),
		ifs:       mk("if_statement"),
		ternaries: mk("conditional_expression"),
		loops:     mk("for_statement", "foreach_statement", "while_statement", "do_statement"),
		switches:  mk("switch_statement"),
		returns:   mk("return_statement"),
		strings:   mk("string", "string_value"),
		idents:    mk("variable_name"),
		members:   mk("member_access_expression", "subscript_expression", "nullsafe_member_access_expression", "scoped_property_access_expression"),
		casts:     mk("cast_expression"),
		pseudo:    map[string]string{"echo_statement": "echo", "print_intrinsic": "print", "include_expression": "include", "include_once_expression": "include", "require_expression": "include", "require_once_expression": "include", "shell_command_expression": "shell_exec", "exit_statement": "exit"},
		numbers:   mk("integer"),
		trues:     mk("boolean"),
	},
	"go": {
		funcs:    mk("function_declaration", "method_declaration", "func_literal"),
		calls:    mk("call_expression"),
		assigns:  mk("short_var_declaration", "assignment_statement", "var_spec"),
		ifs:      mk("if_statement"),
		loops:    mk("for_statement"),
		switches: mk("expression_switch_statement"),
		returns:  mk("return_statement"),
		strings:  mk("interpreted_string_literal", "raw_string_literal"),
		idents:   mk("identifier"),
		members:  mk("selector_expression", "index_expression"),
		numbers:  mk("int_literal"),
		trues:    mk("true"), falses: mk("false"),
	},
}

// Family maps a crev grammar id to its syntax family ("" = unsupported).
func Family(grammar string) string {
	switch grammar {
	case "java", "kotlin", "python", "php", "go":
		return grammar
	case "javascript", "typescript", "tsx":
		return "javascript"
	}
	return ""
}
