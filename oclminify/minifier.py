from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import copy
import itertools
import sys
from pycparser import c_ast
from oclminify.parser import Parser


class Minifier(c_ast.NodeVisitor):
    IGNORE_TYPE_SYMBOLS = Parser.initial_type_symbols | set(["char", "int", "short", "long", "float", "double"])
    CONSTANT_SYMBOLS = [
        "true",
        "false",
        "CLK_LOCAL_MEM_FENCE",
        "CLK_GLOBAL_MEM_FENCE",
        "CLK_NORMALIZED_COORDS_TRUE",
        "CLK_NORMALIZED_COORDS_FALSE",
        "CLK_ADDRESS_MIRRORED_REPEAT",
        "CLK_ADDRESS_REPEAT",
        "CLK_ADDRESS_CLAMP_TO_EDGE",
        "CLK_ADDRESS_CLAMP",
        "CLK_ADdRESS_NONE",
        "CLK_FILTER_NEAREST",
        "CLK_FILTER_LINEAR",
        "CLK_SNORM_INT8",
        "CLK_SNORM_INT16",
        "CLK_UNORM_INT8",
        "CLK_UNORM_INT16",
        "CLK_UNORM_SHORT_565",
        "CLK_UNORM_SHORT_555",
        "CLK_UNORM_SHORT_101010",
        "CLK_SIGNED_INT8",
        "CLK_SIGNED_INT16",
        "CLK_SIGNED_INT32",
        "CLK_UNSIGNED_INT8",
        "CLK_UNSIGNED_INT16",
        "CLK_UNSIGNED_INT32",
        "CLK_HALF_FLOAT",
        "CLK_FLOAT",
        "CLK_A",
        "CLK_R",
        "CLK_Rx",
        "CLK_RG",
        "CLK_RGx",
        "CLK_RA",
        "CLK_RGB",
        "CLK_RGBx",
        "CLK_RGBA",
        "CLK_ARGB",
        "CLK_BGRA",
        "CLK_INTENSITY",
        "CLK_LUMINANCE",
        # OpenCL >= 2.0
        "CLK_IMAE_MEM_FENCE",
        "memory_order_relaxed",
        "memory_order_acquire",
        "memory_order_release",
        "memory_order_acq_rel",
        "memory_order_seq_cst",
        "memory_scope_work_item",
        "memory_scope_work_group",
        "memory_scope_device",
        "memory_scope_all_svm_devices",
    ]

    class Function(object):
        def __init__(self, name="", return_type=None):
            self.name = name
            self.return_type = return_type

    class Declaration(object):
        def __init__(self):
            self.name = ""
            self.type = ""
            self.children = {}
            self.is_definition = False

        def __eq__(self, other):
            if isinstance(other, Minifier.Declaration):
                return self.name == other.name
            elif type(other) is str:
                return self.name == other
            else:
                return NotImplemented

        def __repr__(self):
            return "(%s) %s %s" % (self.type, self.name, repr(self.children))

    def __init__(self, replace_kernel_names, global_postfix):
        self.functions = {}
        self.functions_args = {}
        self.kernel_functions = []
        self.declaration_scopes = [{}]
        self.replace_kernel_names = replace_kernel_names
        self.global_postfix = global_postfix

    def generic_visit(self, node):
        if node is None:
            return
        else:
            print("FOUND UNSUPPORTED NODE: " + str(node), file=sys.stderr)
            print("Could not find method Minifier.visit_%s" % node.__class__.__name__, file=sys.stderr)
            node.show()
            sys.exit(-1)

    def visit_Constant(self, node):
        pass  # Unused.

    def visit_ID(self, node):
        node.name = self._get_new_declaration_name(node.name)

    def visit_ArrayRef(self, node):
        self.visit(node.name)
        self.visit(node.subscript)

    def visit_StructRef(self, node):
        # Get a list of sequential child struct references so we can walk them
        # and shorten any names as appropriate.
        refs = []
        node_ref = node
        while isinstance(node_ref, c_ast.StructRef):
            refs.append(node_ref)
            node_ref = node_ref.name

        # Walk through struct references in outer most order first
        # (ie. first.second.third). This way we can check the type of the
        # current reference when it's a member of another struct.
        last_ref_type = []
        for node_ref in reversed(refs):
            if not isinstance(node_ref.name, c_ast.StructRef):
                self.visit(node_ref.name)
            decl_type = self._get_structref_type(node_ref)
            if decl_type is None:
                decl_type = last_ref_type
            last_ref_type = []

            # If accessing an anonymous struct, try and use the shortened IDs.
            if isinstance(decl_type, Minifier.Declaration):
                declaration = decl_type
                if node_ref.field.name in declaration.children:
                    child = declaration.children[node_ref.field.name]
                    node_ref.field.name = child.name
                    last_ref_type = child.type
            elif len(decl_type) == 1:
                # If accessing indices of a vector, try and shorten the syntax.
                vector_components = "".join([char for char in decl_type[0] if char.isdigit()])
                vector_types = ["".join(a) for a in itertools.product(["char", "uchar", "short", "ushort", "int", "uint", "long", "ulong", "float", "double", "half"], ["2", "3", "4", "8", "16"])]
                if decl_type[0] in vector_types:
                    node_ref.field.name = self._shorten_vector_access(int(vector_components), node_ref.field.name)
                # If accessing a struct, try and use the shortened IDs.
                if decl_type[0] not in self.IGNORE_TYPE_SYMBOLS:
                    declaration = self._get_declaration_by_new_name(decl_type[0])
                    if declaration and declaration.type == "struct":
                        if node_ref.field.name in declaration.children:
                            last_ref_type = declaration.children[node_ref.field.name].type
                            if not isinstance(last_ref_type, list) and not isinstance(last_ref_type, Minifier.Declaration):
                                last_ref_type = [last_ref_type, ]
                            node_ref.field.name = declaration.children[node_ref.field.name].name

    def visit_FuncCall(self, node):
        node.name.name = self._get_new_function_name(node.name.name)
        self.visit(node.args)

    def visit_UnaryOp(self, node):
        self.visit(node.expr)

    def visit_BinaryOp(self, node):
        self.visit(node.left)
        self.visit(node.right)

    def visit_Assignment(self, node):
        self.visit(node.rvalue)
        self.visit(node.lvalue)

    def visit_IdentifierType(self, node):
        # Use shorter idenitifiers when available.
        if node.names == ["unsigned", "char"]:
            node.names = ["uchar"]
        elif node.names == ["unsigned", "short"]:
            node.names = ["ushort"]
        elif node.names == ["unsigned", "int"]:
            node.names = ["uint"]
        elif node.names == ["unsigned", "long"]:
            node.names = ["ulong"]
        if len(node.names) == 1:
            # If the identifier is another built in, skip.
            if node.names[0] in self.IGNORE_TYPE_SYMBOLS:
                return
            # If the identifier is a typedef, use the shortened name.
            new_name = self._get_new_declaration_name(node.names[0])
            if new_name and new_name != node.names[0]:
                node.names = [new_name, ]

    def visit_Decl(self, node, no_type=False):
        if node.init:
            self.visit(node.init)
        if node.funcspec and "__kernel" in node.funcspec:
            self.kernel_functions.append(node.name)
        self.visit(node.type)

    def visit_DeclList(self, node):
        for decl in node.decls:
            self.visit(decl)

    def visit_Cast(self, node):
        self.visit(node.to_type)
        if node.expr:
            self.visit(node.expr)

    def visit_ExprList(self, node):
        for expr in node.exprs:
            self.visit(expr)

    def visit_FileAST(self, node):
        for ext in node.ext:
            self.visit(ext)

    def visit_Compound(self, node):
        self.declaration_scopes.append({})
        if node.block_items is not None:
            for item in node.block_items:
                self.visit(item)
        self.declaration_scopes.pop()

    def visit_ParamList(self, node):
        for param in node.params:
            self.visit(param)

    def visit_Return(self, node):
        if node.expr:
            self.visit(node.expr)

    def visit_Continue(self, node):
        pass  # Unused.

    def visit_Break(self, node):
        pass  # Unused.

    def visit_If(self, node):
        if node.cond:
            self.visit(node.cond)
        self.visit(node.iftrue)
        if node.iffalse:
            self.visit(node.iffalse)

    def visit_For(self, node):
        if node.init:
            self.visit(node.init)
        if node.cond:
            self.visit(node.cond)
        if node.next:
            self.visit(node.next)
        self.visit(node.stmt)

    def visit_FuncDecl(self, node):
        # This should be only reachable for functions declared without
        # definitions (Function Prototype).
        # TODO: Check if the function has a definition provided and make sure
        # they share the same name.
        pass

    def visit_FuncDef(self, node):
        if "__kernel" in node.decl.funcspec:
            self.kernel_functions.append(node.decl.name)

        # Shorten function name unless it's a kernel and Minifier() was
        # initialized with replace_kernel_names=False. If outputting to a
        # C header, you probably want to replace kernel names. In other
        # situations, you probably don't want to replace kernel names or you
        # won't know which kernel is which.
        old_name = node.decl.type.type.declname
        if "__kernel" in node.decl.funcspec and not self.replace_kernel_names:
            new_name = old_name
        else:
            new_name = self._generate_unique_declaration_name()
        node.decl.type.type.declname = new_name

        self.functions[old_name] = Minifier.Function(new_name, [])  # Reserve the function name.
        self.declaration_scopes.append({})
        self.visit(node.decl.type.type.type)  # Return type
        self.visit(node.decl.type.args)  # Args
        self.functions_args[old_name] = self.declaration_scopes[-1]
        self.functions[old_name] = Minifier.Function(new_name, node.decl.type.type.type)  # Include return type after it's processed.

        self.visit(node.body)
        self.declaration_scopes.pop()

    def visit_PtrDecl(self, node):
        self.visit(node.type)

    def visit_ArrayDecl(self, node):
        self.visit(node.type)

    def visit_TypeDecl(self, node):
        self.visit(node.type)
        new_name = self._generate_unique_declaration_name()
        decl = Minifier.Declaration()
        decl.name = new_name

        if "names" in node.type.attr_names:
            decl.type = node.type.names
        elif isinstance(node.type, c_ast.Struct) and node.type.name is None:
            decl.type = self._struct_to_declaration(node.type)
        elif isinstance(node.type, c_ast.Struct):
            decl.type = self._get_declaration_by_new_name(node.type.name, "struct")

        if decl.type is None:
            if "name" in node.type.attr_names:
                decl.type = [node.type.name, ]
            else:
                print("DEBUG: No types for %s" % node.declname, file=sys.stderr)

        self.declaration_scopes[-1][node.declname] = decl
        node.declname = new_name

    def visit_TernaryOp(self, node):
        self.visit(node.cond)
        self.visit(node.iftrue)
        self.visit(node.iffalse)

    def visit_While(self, node):
        self.visit(node.cond)
        self.visit(node.stmt)

    def visit_Typedef(self, node):
        self.visit(node.type)

    def visit_TypeDeclExt(self, node):
        self.visit_TypeDecl(node)

    def visit_Struct(self, node):
        # If an anonymous struct, ignore because it requires special handling
        # to shrink the type declaration names and still make them accessible
        # later.
        if not node.name:
            return
        # Named struct being declared. Shorten name of struct and map the names
        # of its variables to something shorter.
        if node.decls:
            decl = self._struct_to_declaration(node)
            old_name = node.name
            node.name = decl.name
            self.declaration_scopes[-1][old_name] = decl
        # Struct is being declared as type of a variable, just get the new
        # name.
        else:
            node.name = self._get_new_declaration_name(node.name)

    def visit_Enum(self, node):
        if node.name:
            # Shrink name if provided. Considering the required enum prefix when
            # delcaring a variable of this type, we could probably have a set of
            # symbols in the current scope dedicated to enums but it's probably not
            # worth the added complexity.
            if node.values:
                old_name = node.name
                node.name = self._generate_unique_declaration_name()
                self.declaration_scopes[-1][old_name] = node
            # Enum is being declared as a type of a variable, just get the
            # new name.
            else:
                node.name = self._get_new_declaration_name(node.name)

        # Shrink names of each enum symbol.
        if node.values:
            for enum in node.values.enumerators:
                old_name = enum.name
                enum.name = self._generate_unique_declaration_name()
                self.declaration_scopes[-1][old_name] = enum

    def visit_EmptyStatement(self, node):
        pass  # Unused.

    def visit_InitList(self, node):
        for expr in node.exprs:
            self.visit(expr)

    def visit_Pragma(self, node):
        pass  # Unused.

    def visit_Typename(self, node):
        while "type" in dir(node) and not isinstance(node, c_ast.IdentifierType):
            node = node.type
        if isinstance(node, c_ast.IdentifierType):
            self.visit_IdentifierType(node)

    def visit_DoWhile(self, node):
        self.visit(node.stmt)
        self.visit(node.cond)

    def visit_Switch(self, node):
        self.visit(node.cond)
        self.visit(node.stmt)

    def visit_Case(self, node):
        self.visit(node.expr)
        for stmt in node.stmts:
            self.visit(stmt)

    def visit_Default(self, node):
        for stmt in node.stmts:
            self.visit(stmt)

    # TODO: Support these other node types where applicable to OpenCL.
    # def visit_Label(self, node):
    # def visit_Goto(self, node):
    # def visit_EllipsisParam(self, node):
    # def visit_Union(self, node):
    # def visit_NamedInitializer(self, node):

    def _index_to_alpha_str(self, index):
        # TODO: Make this alpha numeric for the first character only and alpha numeric + other supported symbols for the rest.
        if index == 0:
            return 'a'
        characters = list(range(ord('a'), ord('z') + 1)) + list(range(ord('A'), ord('Z') + 1))
        result = ""
        digit = 1
        while index >= 0:
            digit_min_value = len(characters) ** (digit - 1)
            if index < digit_min_value:
                break
            value = index % ((len(characters) ** digit) // len(characters) ** (digit - 1))
            result += chr(characters[value])
            index -= value
            digit += 1
        return "".join(reversed(result))

    def _get_new_function_name(self, name):
        if name in self.functions:
            return self.functions[name].name
        # Remaining functions are probably built-in.
        return name

    def _get_function_by_new_name(self, new_name):
        for func in self.functions.values():
            if func.name == new_name:
                return func
        # Remaining functions are probably built-in.
        return None

    def _is_declaration_name_unique(self, name):
        for scope in self.declaration_scopes:
            if name in [declaration.name for declaration in scope.values()]:
                return False
        return True

    def _generate_unique_declaration_name(self):
        postfix = self.global_postfix if len(self.declaration_scopes) == 1 else ""

        index = 0
        while True:
            name = self._index_to_alpha_str(index) + postfix
            index += 1
            # Make sure declaration name is not currently in use within the
            # visible scope. Also make sure the declaration name does not shadow
            # an existing declaration name.
            if self._is_declaration_name_unique(name) and not self._get_function_by_new_name(name):
                return name

    def _get_new_declaration_name(self, name):
        if name in self.CONSTANT_SYMBOLS:
            return name

        for scope in reversed(self.declaration_scopes):
            if name in scope:
                return scope[name].name
        print("Could not find new declaration name for '%s'" % name, file=sys.stderr)
        return name

    def _get_declaration_by_name(self, name, type_filters=None):
        def is_type_in_filters(decl_type):
            if type_filters is None:
                return True
            for type_filter in type_filters:
                if isinstance(decl_type, str) and isinstance(type_filter, str):
                    if decl_type == type_filter:
                        return True
                elif isinstance(type_filter, type) and isinstance(decl_type, type_filter):
                    return True
            return False

        for scope in reversed(self.declaration_scopes):
            if name in scope:
                if is_type_in_filters(scope[name].type):
                    return copy.deepcopy(scope[name])
        print("Could not find new declaration for '%s'" % name, file=sys.stderr)

    def _get_declaration_by_new_name(self, new_name, type_filter=None):
        for scope in reversed(self.declaration_scopes):
            for declaration in scope.values():
                if declaration.name == new_name:
                    if type_filter is None or declaration.type == type_filter:
                        return copy.deepcopy(declaration)
        print("Could not find declaration with new name '%s'" % new_name, file=sys.stderr)
        return None

    def _get_structref_type(self, node):
        def get_builtin_func_type(func_name, args):
            # Extract type of each argument so we can determine the return type
            # of the built-in function. Many, if not most, built-in functions
            # determine their return type based off of their arguments. If the
            # argument type is a pointer, the pointer part is stripped because
            # it makes it easier to figure out the return type. None of the
            # built-in functions, as of OpenCL 1.2, return a pointer type.
            arg_types = []
            for arg in args.exprs:
                if isinstance(arg, c_ast.ID):
                    declaration = self._get_declaration_by_new_name(arg.name)
                    if declaration is not None:
                        arg_types.append(declaration.type[0])
                        continue
                # TODO: Support figuring out the type of an expression.
                arg_types.append("void")

            from oclminify.functions import BUILTIN
            result = BUILTIN.get_func_return_type(func_name, arg_types)
            return result

        # Find type of struct variable being referenced. It might be accessed
        # as the result of a function, after indexing into an array, or just
        # through a variable directly. Structs inside of structs are a special
        # case handled by the caller of this function (visit_StructRef()).
        if isinstance(node.name, c_ast.StructRef):
            return None
        elif isinstance(node.name, c_ast.FuncCall):
            func_name = node.name.name.name
            func = self._get_function_by_new_name(func_name)
            if func is None:
                return [get_builtin_func_type(func_name, node.name.args), ]
            new_name = func.return_type.name
        elif isinstance(node.name, c_ast.UnaryOp):
            new_name = node.name.expr.name
        elif isinstance(node.name, c_ast.ArrayRef):
            new_name = node.name.name.name
        else:
            new_name = node.name.name

        declaration = self._get_declaration_by_new_name(new_name)
        if declaration:
            if declaration.type == "struct":
                decl_type = declaration.name
            else:
                decl_type = declaration.type
        else:
            decl_type = ["", ]

        return decl_type

    def _struct_to_declaration(self, node):
        declaration = Minifier.Declaration()
        declaration.type = "struct"
        declaration.is_definition = True

        # Generate a short name for this struct.
        declaration.name = self._generate_unique_declaration_name()

        # Generate short names for each declaration in the struct.
        self.declaration_scopes.append({node.name: declaration})
        self.declaration_scopes.append({})  # Allow outer struct name, defined immediately above, to be shadowed.
        for index, node_decl in enumerate(node.decls):
            if isinstance(node_decl.type, c_ast.Struct):
                minify_decl = self._struct_to_declaration(node_decl.type)
                old_declname = node_decl.type.name

                # Replace the generated name with a likely shorter one because
                # this is the scope inside of a struct. We don't have to worry
                # about shadowing.
                new_declname = self._index_to_alpha_str(index)
                minify_decl.name = new_declname
                node_decl.type.name = new_declname

                self.declaration_scopes[-1][old_declname] = minify_decl
            else:
                if isinstance(node_decl.type, c_ast.PtrDecl):
                    node_decl = node_decl.type

                minify_decl = Minifier.Declaration()
                old_declname = node_decl.type.declname
                self.visit(node_decl.type)

                # Generate child declaration name. It just has to be unique to this
                # struct, not to the scope or anything like that.
                new_declname = self._index_to_alpha_str(index)
                node_decl.type.declname = new_declname

                # Save as a child declaration so can rewrite references to this
                # declaration to use the shortened name.
                if isinstance(node_decl.type.type, c_ast.Struct):
                    minify_decl = self._get_declaration_by_name(old_declname, ["struct", Minifier.Declaration])
                    minify_decl.name = node_decl.type.declname
                else:
                    minify_decl.name = node_decl.type.declname
                    minify_decl.type = node_decl.type.type.names[0]

                declaration.children[old_declname] = minify_decl
        self.declaration_scopes.pop()
        self.declaration_scopes.pop()

        return declaration

    def _shorten_vector_access(cls, vector_component_count, vector_components_specified):
        # For vectors of 1-4 components in the form .s0123, convert to the form .xyzw.
        # According to the standard, the .xyzw syntax is only valid for vectors with
        # no more than 4 components.
        # https://www.khronos.org/registry/cl/specs/opencl-1.1.pdf#page=165
        if vector_component_count <= 4 and vector_components_specified.startswith("s"):
            return "".join(map(lambda a: {"0": "x", "1": "y", "2": "z", "3": "w"}[a], vector_components_specified[1:]))

        # For vectors of length 2 and 4 using the even and odd syntax, use the
        # shorter .xyzw syntax.
        if vector_component_count == 2 or vector_component_count == 4:

            def sequential_fast_components():
                return "xyzw"[:vector_component_count]

            def even_fast_components():
                return sequential_fast_components()[::2]

            def odd_fast_components():
                return sequential_fast_components()[1::2]

            if vector_components_specified == "even":
                return even_fast_components()
            elif vector_components_specified == "odd":
                return odd_fast_components()

        # For vectors with more than 4 components matching specific patterns
        # are shortened to use the lo, hi, even, and odd syntax.
        # https://www.khronos.org/registry/cl/specs/opencl-1.1.pdf#page=167
        elif vector_component_count > 4 and vector_components_specified.startswith("s"):
            assert(vector_component_count >= 1)

            def sequential_components():
                return "0123456789abcdef"[0:vector_component_count]

            def lo_components():
                return sequential_components()[:vector_component_count // 2]

            def hi_components():
                return sequential_components()[vector_component_count // 2:]

            def even_components():
                return sequential_components()[::2]

            def odd_components():
                return sequential_components()[1::2]

            indices = vector_components_specified[1:].lower()
            if indices == lo_components():
                return "lo"
            elif indices == hi_components():
                return "hi"
            elif indices == even_components():
                return "even"
            elif indices == odd_components():
                return "odd"
        return vector_components_specified
