from __future__ import absolute_import
from pycparser import c_ast
from pycparserext import ext_c_parser
from pycparserext.ext_c_generator import OpenCLCGenerator


class Generator(OpenCLCGenerator):
    def visit(self, n):
        result = super(OpenCLCGenerator, self).visit(n)

        # Simple method to remove extra newlines except where required
        # (#pragma). This has the consequence that it'll modify character
        # arrays. Fortunately, character arrays are rarely used in OpenCL in
        # practice.
        lines = [line for line in result.replace("#pragma", "\n#pragma").split("\n") if len(line) > 0]
        result = ""
        for i, line in enumerate(lines):
            if "#pragma" in line:
                # Put pragma on its own line.
                if i > 0 and "#pragma" not in lines[i - 1]:
                    result += "\n"
                result += line + "\n"
            elif len(line) > 0:
                result += line

        return result

    def visit_BinaryOp(self, n):
        # Only include brackets when order cannot be implied through operator
        # priority. Based off of C because I could not find the operator
        # precedence in the specification.
        # http://en.cppreference.com/w/c/language/operator_precedence
        operator_precedence = {
            "*": 3,
            "/": 3,
            "%": 3,
            "+": 4,
            "-": 4,
            "<<": 5,
            ">>": 5,
            "<": 6,
            "<=": 6,
            ">": 6,
            ">=": 6,
            "==": 7,
            "!=": 7,
            "&": 8,
            "^": 9,
            "|": 10,
            "&&": 11,
            "||": 12,
        }
        left = self.visit(n.left)
        right = self.visit(n.right)
        if isinstance(n.left, c_ast.BinaryOp):
            if operator_precedence[n.left.op] > operator_precedence[n.op]:
                left = "(" + left + ")"
        if isinstance(n.right, c_ast.BinaryOp):
            if operator_precedence[n.right.op] >= operator_precedence[n.op]:
                right = "(" + right + ")"
        result = "%s%s%s" % (left, n.op, right)
        return result.replace(" ", "")

    def visit_Assignment(self, n):
        result = self.visit(n.lvalue)
        result += n.op
        result += self._parenthesize_if(n.rvalue, lambda n: isinstance(n, c_ast.Assignment))
        return result

    def visit_Decl(self, n, no_type=False):
        result = n.name
        if not no_type:
            result = self._generate_decl(n)
        if n.bitsize:
            result += ":" + self.visit(n.bitsize)
        if n.init:
            result += "=" + self._visit_expr(n.init)
        return result

    def visit_DeclList(self, n):
        result = ""
        for index, decl in enumerate(n.decls):
            if index == 0:
                result = self.visit(decl)
            else:
                result += "," + self.visit_Decl(decl, no_type=True)
        return result

    def visit_Cast(self, n):
        # Work around an issue (bug?) I noticed in green's compiler that causes
        # vector literals in double brackets to be treated as a scaler using the
        # last value in the expression list.
        # ushort4 test = (ushort4)((0,1,2,3)); //test = (3,3,3,3)
        # ushort4 test = (ushort4)(0,1,2,3); //test = (0,1,2,3)
        result = "(" + self._generate_type(n.to_type) + ")"
        if self._is_simple_node(n.expr):
            result += " " + self.visit(n.expr)
        else:
            result += "(" + self.visit(n.expr) + ")"
        return result.replace(") ", ")")

    def visit_UnaryOp(self, n):
        # Avoid extra brackets around the expression unless required by the
        # operator. Just sizeof() needs the extra brackets.
        result = self.visit(n.expr)
        if n.op == "sizeof":
            result = "sizeof(" + result + ")"
        # Add postfix operators at the end.
        elif len(n.op) >= 1 and n.op[0] == "p":
            result = result + n.op[1:]
        else:
            result = n.op + result
        return result

    def visit_TernaryOp(self, n):
        result = self.visit(n.cond)
        result += "?" + self.visit(n.iftrue)
        result += ":" + self.visit(n.iffalse)
        return result

    def visit_If(self, n):
        result = "if("
        if n.cond:
            result += self.visit(n.cond)
        result += ")"
        result += self._generate_stmt(n.iftrue).strip()
        if n.iffalse:
            result += "else"
            if isinstance(n.iffalse, c_ast.If):
                result += " "
            elif not self._is_multi_stmt_compound(n.iffalse):
                result += " "
            result += self._generate_stmt(n.iffalse).strip()
        return result

    def visit_For(self, n):
        result = "for("
        if n.init:
            result += self.visit(n.init)
        result += ";"
        if n.cond:
            result += self.visit(n.cond)
        result += ";"
        if n.next:
            result += self.visit(n.next)
        result += ")"
        result += self._generate_stmt(n.stmt).strip()
        return result

    def visit_While(self, n):
        result = "while("
        if n.cond:
            result += self.visit(n.cond)
        result += ")"
        result += self._generate_stmt(n.stmt).strip()
        return result

    def visit_DoWhile(self, n):
        result = "do"
        if not self._is_multi_stmt_compound(n.stmt):
            result += " "
        result += self._generate_stmt(n.stmt).strip()
        result += "while("
        if n.cond:
            result += self.visit(n.cond)
        result += ");"
        return result

    def visit_Struct(self, n):
        result = "struct"
        if n.name:
            result += " " + n.name
        if n.decls:
            result += "{" + self._generate_grouped_stmts(n.decls) + "}"
        return result

    def visit_Switch(self, n):
        result = "switch(" + self.visit(n.cond) + ")"
        result += self._generate_stmt(n.stmt)
        return result

    def visit_Enum(self, n):
        result = "enum"
        if n.name:
            result += " " + n.name
        if n.values:
            result += "{"
            for index, enum in enumerate(n.values.enumerators):
                result += enum.name
                if enum.value:
                    result += "=" + self.visit(enum.value)
                if index != len(n.values.enumerators) - 1:
                    result += ","
            result += "}"
        return result

    def visit_Case(self, n):
        result = "case " + self.visit(n.expr) + ":"
        for stmt in n.stmts:
            result += self._generate_stmt(stmt).strip()
        return result

    def visit_Default(self, n):
        result = "default:"
        for stmt in n.stmts:
            result += self._generate_stmt(stmt).strip()
        return result

    def visit_FuncDef(self, n):
        result = self.visit(n.decl)

        # Remove double spaces created by pycparserext when the __kernel and
        # __attribute__ modifiers are both specified.
        result = result.replace("  ", " ")

        # Remove extra space after declaring an attribute modifier.
        result = result.replace(")) ", "))")

        body = self.visit(n.body)
        if self._is_multi_stmt_compound(n.body):
            result += body
        else:
            result += "{" + body + "}"
        return result

    def visit_ParamList(self, n):
        return ",".join(self.visit(param) for param in n.params)

    def visit_ExprList(self, n):
        return ",".join([self.visit(expr) for expr in n.exprs])

    def visit_InitList(self, n):
        return ",".join([self.visit(expr) for expr in n.exprs])

    def visit_Compound(self, n):
        if not n.block_items:
            return "{}"
        result = self._generate_grouped_stmts(n.block_items)
        if len(n.block_items) > 1:
            result = "{" + result + "}"
        return result

    def visit_FileAST(self, n):
        # Prevent parent implementation from inserting an unnecessary newline
        # for non-function definitions at the top level.
        result = ""
        for ext in n.ext:
            if isinstance(ext, c_ast.FuncDef) or isinstance(ext, c_ast.Pragma):
                result += self.visit(ext)
            else:
                result += self.visit(ext) + ";"
        return result

    def _generate_type(self, n, modifiers=[]):
        result = super(Generator, self)._generate_type(n, modifiers)

        # Remove space between closing bracket and name.
        if "declname" in n.attr_names and n.declname and result.endswith("} " + n.declname):
            space_index = result.rfind("} ")
            result = result[:space_index + 1] + result[space_index + 2:]

        # Remove space around pointer indicator.
        result = result.replace("* ", "*").replace(" *", "*")

        return result

    def _generate_grouped_stmts(self, stmts):
        """Generate a list of statements into a string. Sequences of
           declarations with the same type are grouped into compact form. For
           example, "float a = 0; float b; float c = 1.0f;" becomes
           "float a=0,b,c=1.0f;".
        """

        # Format a sequence of declarations in compact form.
        def group_declarations(decl_type, start_index, end_index):
            result = " ".join(decl_type)

            for x in range(start_index, end_index):
                is_ptr = isinstance(stmts[x].type, c_ast.PtrDecl)
                is_struct_decl = isinstance(stmts[x].type.type, c_ast.Struct) and stmts[x].type.type.decls
                is_enum_values = isinstance(stmts[x].type.type, c_ast.Enum) and stmts[x].type.type.values
                if x == start_index and not is_ptr and not is_struct_decl and not is_enum_values:
                    result += " "
                if x != start_index:
                    result += ","
                decl = stmts[x]
                if is_ptr:
                    result += "*" + decl.type.type.declname
                else:
                    result += decl.type.declname
                if isinstance(decl.type, ext_c_parser.TypeDeclExt):
                    result += " __attribute__((" + self.visit(decl.type.attributes) + "))"
                if decl.init:
                    result += "=" + self._generate_stmt(decl.init)[:-2]  # Strip ";\n" at end.

            result += ";"
            return result

        # Format each statement while searching for sequences of declarations.
        result = ""
        decl_chain_start_index = -1
        decl_chain_type = []
        for i, stmt in enumerate(stmts):
            # Type declaration statement.
            if isinstance(stmt, c_ast.Decl) and (isinstance(stmt.type, c_ast.TypeDecl) or isinstance(stmt.type, c_ast.PtrDecl)):
                typedecl = stmt.type.type if isinstance(stmt.type, c_ast.TypeDecl) else stmt.type.type.type
                if isinstance(typedecl, c_ast.Struct):
                    decl_type = [self.visit_Struct(typedecl), ]
                elif isinstance(typedecl, c_ast.Enum):
                    decl_type = [self.visit_Enum(typedecl), ]
                else:
                    decl_type = typedecl.names

                # New sequence and no sequence currently found.
                if decl_chain_start_index == -1:
                    decl_chain_start_index = i
                    decl_chain_type = decl_type
                # New sequence but a sequence was already found. Process it
                # first.
                elif decl_type != decl_chain_type:
                    result += group_declarations(decl_chain_type, decl_chain_start_index, i)
                    decl_chain_start_index = i
                    decl_chain_type = decl_type
            # Typical statement.
            else:
                # Format existing sequence before generating next statement.
                if decl_chain_start_index != -1:
                    result += group_declarations(decl_chain_type, decl_chain_start_index, i)
                    decl_chain_start_index = -1
                result += self._generate_stmt(stmt)

        # Format final sequence if list of statements ends in a sequence.
        if decl_chain_start_index != -1:
            result += group_declarations(decl_chain_type, decl_chain_start_index, len(stmts))

        return result

    def _is_multi_stmt_compound(self, n):
        return isinstance(n, c_ast.Compound) and ((n.block_items and len(n.block_items) != 1) or not n.block_items)
