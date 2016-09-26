from __future__ import absolute_import
import sys
import unittest
sys.path.insert(0, "..")
from oclminify.build import try_build
from oclminify.minify import minify


class TestMinifier(unittest.TestCase):
    def assert_minify(self, data, expected_result, **kwargs):
        if not try_build(data):
            raise AssertionError("Input OpenCL code could not be built.")
        result = minify(data, **kwargs)
        self.assertEqual(result, expected_result)
        if not try_build(result):
            raise AssertionError("Minified OpenCL code could not be built.")

    def test_simple(self):
        data = r"""
            __kernel void main()
            {
            }"""
        self.assert_minify(data, "__kernel void a(){}")

    def test_no_extra_casting_brackets(self):
        data = r"""
            __kernel void main()
            {
                ushort4 test = (ushort4)(0,1,2,3);
                ushort test2 = (ushort)1.0f;
            }"""
        self.assert_minify(data, "__kernel void a(){ushort4 b=(ushort4)(0,1,2,3);ushort c=(ushort)1.0f;}")
        data = r"""
            __kernel void main()
            {
                float4 test1 = (float4)(0.0f,1.0f,2.0f,3.0f);
                ushort4 test2 = convert_ushort4(test1 - (float4)(0.0f,1.0f,2.0f,3.0f));
                test2 = convert_ushort4((float4)(0.0f,1.0f,2.0f,3.0f) - (float4)(0.0f,1.0f,2.0f,3.0f));
            }"""
        self.assert_minify(data, "__kernel void a(){float4 b=(float4)(0.0f,1.0f,2.0f,3.0f);ushort4 c=convert_ushort4(b-(float4)(0.0f,1.0f,2.0f,3.0f));c=convert_ushort4((float4)(0.0f,1.0f,2.0f,3.0f)-(float4)(0.0f,1.0f,2.0f,3.0f));}")

    def test_simple_operator_precedence(self):
        data = r"""
            __kernel void main()
            {
                float test1 = 1.0f;
                int test2 = 2;
                float test3 = test1 / (2.0f * (float)test2);
            }"""
        self.assert_minify(data, "__kernel void a(){float b=1.0f;int c=2;float d=b/(2.0f*(float)c);}")

    def test_no_brackets_when_implied_operator_precedence(self):
        data = r"""
            __kernel void main()
            {
                int a = 3;
                int b = 5;
                int test = a * b - a + b / a;
                test = a * (b - a) + b / a;
                test = (b - a) * (b - a);
            }"""
        self.assert_minify(data, "__kernel void a(){int b=3,c=5,d=b*c-b+c/b;d=b*(c-b)+c/b;d=(c-b)*(c-b);}")
        data = r"""
        __kernel void main()
        {
            int a = 3;
            int b = 5;
            int test = (((((((((((((((((a % b) / a) * b) - a) + b) >> a) << b) >= a) > b) <= a) < b) != a) == b) & a) ^ b) | a) && b) || a;
        }"""
        self.assert_minify(data, "__kernel void a(){int b=3,c=5,d=b%c/b*c-b+c>>b<<c>=b>c<=b<c!=b==c&b^c|b&&c||b;}")

    def test_brackets_when_no_operator_precedence(self):
        data = r"""
        __kernel void main()
        {
            int a = 3;
            int b = 5;
            int test = (((((((((((((((((a || b) && a) | b) ^ a) & b) == a) != b) < a) <= b) > a) >= b) << a) >> b) + a) - b) * a) / b) % a;
        }"""
        self.assert_minify(data, "__kernel void a(){int b=3,c=5,d=(((((((((b||c)&&b)|c)^b)&c)==b!=c)<b<=c>b>=c)<<b>>c)+b-c)*b/c%b;}")

    def test_shrink_data_types(self):
        data = r"""
            __kernel void main()
            {
                typedef unsigned int t;
                t test = 0;
            }"""
        self.assert_minify(data, "__kernel void a(){typedef uint b;b c=0;}")
        data = r"""
            typedef unsigned int typedef_uint;
            __kernel void main()
            {
                unsigned char a = 0;
                unsigned short b = 0;
                unsigned int c = 0;
                unsigned long d = 0;
                typedef_uint e = 0;
            }"""
        self.assert_minify(data, "typedef uint a;__kernel void b(){uchar c=0;ushort d=0;uint e=0;ulong f=0;a g=0;}")
        data = r"""
            __kernel void main()
            {
                int test = sizeof(unsigned char);
            }"""
        self.assert_minify(data, "__kernel void a(){int b=sizeof(uchar);}")
        data = r"""
            __kernel void main()
            {
                uint* test = 0;
                *(volatile unsigned int*)test;
            }"""
        self.assert_minify(data, "__kernel void a(){uint*b=0;*(volatile uint*)b;}")
        data = r"""
            unsigned int func(unsigned int arg)
            {
            }"""
        self.assert_minify(data, "uint a(uint b){}")

    def test_preserve_attributes(self):
        data = r"""
            typedef unsigned int aligned_uint __attribute__ ((alligned(8)));
            __kernel void main()
            {
                aligned_uint test = 0;
                int test2[8] __attribute__((unused));
            }"""
        self.assert_minify(data, "typedef uint a __attribute__((alligned(8)));__kernel void b(){a c=0;int d[8] __attribute__((unused));}")

    def test_struct(self):
        data = r"""
            typedef unsigned int typedef_uint;
            struct TestStruct
            {
                unsigned char test1;
                unsigned short test2;
                unsigned int test3;
                unsigned long test4;
                typedef_uint test5;
                float4 test6;
                unsigned int test7 __attribute__ ((alligned(8)));
            };
            __kernel void main()
            {
                struct TestStruct ts;
                ts.test1 = 0;
                ts.test2 = 0;
                ts.test3 = 0;
                ts.test4 = 0;
                ts.test5 = 0;
                ts.test6.xy = (float2)0.0f;
                ts.test7 = 0;
            }"""
        self.assert_minify(data, "typedef uint a;struct b{uchar a;ushort b;uint c;ulong d;a e;float4 f;uint g __attribute__((alligned(8)));};__kernel void c(){struct b d;d.a=0;d.b=0;d.c=0;d.d=0;d.e=0;d.f.xy=(float2)0.0f;d.g=0;}")
        data = r"""
            __kernel void main()
            {
                struct
                {
                    unsigned char test;
                } ts;
                ts.test = 0;
            }"""
        self.assert_minify(data, "__kernel void a(){struct{uchar a;}b;b.a=0;}")
        data = r"""
            __kernel void main()
            {
                typedef struct Node
                {
                    struct Node* node;
                } node;
            }"""
        self.assert_minify(data, "__kernel void a(){typedef struct b{struct b*a;}c;}")

    def test_struct_inside_struct(self):
        data = r"""
            struct Struct1
            {
                unsigned short value;
            };
            struct Struct2
            {
                unsigned short value;
                struct Struct1 struct1;
                struct Struct3
                {
                    unsigned short value;
                    struct Struct1 struct1;
                };
                struct Struct3 struct3;
                struct
                {
                    unsigned short value;
                    struct Struct1 struct1;
                } struct4;
            };
            __kernel void main()
            {
                struct Struct2 test;
                test.value = 0;
                test.struct1.value = 0;
                test.struct3.value = 0;
                test.struct3.struct1.value = 0;
                test.struct4.value = 0;
                test.struct4.struct1.value = 0;
            }"""
        self.assert_minify(data, "struct a{ushort a;};struct b{ushort a;struct a b;struct c{ushort a;struct a b;};struct c d;struct{ushort a;struct a b;}e;};__kernel void c(){struct b d;d.a=0;d.b.a=0;d.d.a=0;d.d.b.a=0;d.e.a=0;d.e.b.a=0;}")

    def test_struct_rvalue_reference(self):
        # User specified function.
        data = r"""
            struct TestStruct
            {
                unsigned short value1;
                float8 value2;
            };
            struct TestStruct Func()
            {
                struct TestStruct result;
                result.value1 = 0;
                result.value2 = (float8)0.0f;
                return result;
            }
            __kernel void main()
            {
                unsigned short value1 = Func().value1;
                float4 value2 = Func().value2.s0123;
            }"""
        self.assert_minify(data, "struct a{ushort a;float8 b;};struct a b(){struct a c;c.a=0;c.b=(float8)0.0f;return c;}__kernel void c(){ushort d=b().a;float4 e=b().b.lo;}")
        # Built-in functions.
        data = r"""
            __kernel void main()
            {
                int8 test = (int8)0;
                float4 test2 = convert_float8(test).s0123;
                test2 = as_float8(test).s0123;
            }"""
        self.assert_minify(data, "__kernel void a(){int8 b=(int8)0;float4 c=convert_float8(b).lo;c=as_float8(b).lo;}")
        # Built-in function with return types dependent on arguments.
        data = r"""
            __kernel void main()
            {
                float8 test = (float8)0.0f;
                sin(test).s0123;
                sin(test + (float8)1.0f).s0123;
                sin(test + convert_float8((int8)0)).s0123;
            }"""
        self.assert_minify(data, "__kernel void a(){float8 b=(float8)0.0f;sin(b).lo;sin(b+(float8)1.0f).lo;sin(b+convert_float8((int8)0)).lo;}")

    def test_shrink_vector_indices(self):
        data = r"""
            __kernel void main()
            {
                float4 test = (float4)(0.0f,1.0f,2.0f,3.0f);
                test = test.s0123; //no accessor

                uchar16 test2 = (uchar16)(1);
                uchar8 test3 = test2.s01234567; //.lo
                test3 = test2.s89abcdef; //.hi
                test3 = test2.s02468ace; //.even
                test3 = test2.s13579bdf; //.odd

                float2 test4 = test.even; //.xz
                test4 = test.odd; //.yw
            }"""
        self.assert_minify(data, "__kernel void a(){float4 b=(float4)(0.0f,1.0f,2.0f,3.0f);b=b;uchar16 c=(uchar16)1;uchar8 d=c.lo;d=c.hi;d=c.even;d=c.odd;float2 e=b.xz;e=b.yw;}")

    def test_enum(self):
        data = r"""
            enum
            {
                ANON_UNVALUED,
                ANON_VALUED = 100
            };
            enum Named
            {
                NAMED_UNVALUED,
                NAMED_VALUED = 100
            };
            __kernel void main()
            {
                int anonVar = ANON_UNVALUED;
                anonVar = ANON_VALUED;

                enum Named namedVar = NAMED_UNVALUED;
                namedVar = NAMED_VALUED;

                enum
                {
                    ANONVAR_UNVALUED,
                    ANONVAR_VALUED = 100
                } enumVar;
                enumVar = ANONVAR_UNVALUED;
                enumVar = ANONVAR_VALUED;
            }"""
        self.assert_minify(data, "enum{a,b=100};enum c{d,e=100};__kernel void f(){int g=a;g=b;enum c h=d;h=e;enum{i,j=100}k;k=i;k=j;}")

    def test_do_while(self):
        data = r"""
            __kernel void main()
            {
                int test = 0;
                do
                {
                    test += 1;
                } while(test < 5);
            }"""
        self.assert_minify(data, "__kernel void a(){int b=0;do b+=1;while(b<5);}")

    def test_switch(self):
        data = r"""
            __kernel void main()
            {
                int value = 0;
                switch(value)
                {
                    case 0:
                        value = 5;
                        break;
                    default:
                        value = 4;
                        break;
                };
            }"""
        self.assert_minify(data, "__kernel void a(){int b=0;switch(b){case 0:b=5;break;default:b=4;break;};}")

    def test_ternary(self):
        data = r"""
            __kernel void main()
            {
                int test1 = 5;
                int test2 = test1 < 6 ? 1 + 1 : 10 * 10;
            }"""
        self.assert_minify(data, "__kernel void a(){int b=5,c=b<6?1+1:10*10;}")

    def test_init_list(self):
        data = r"""
            __kernel void main()
            {
                float test[4] = {
                    0.0f,
                    1.0f,
                    2.0f,
                    3.0f
                };
            }"""
        self.assert_minify(data, "__kernel void a(){float b[4]={0.0f,1.0f,2.0f,3.0f};}")

    def test_preserve_pragmas(self):
        data = r"""
            #pragma OPENCL EXTENSION cl_khr_fp64 : enable
            __kernel void main()
            {
            }"""
        self.assert_minify(data, "#pragma OPENCL EXTENSION cl_khr_fp64 : enable\n__kernel void a(){}")
        data = r"""
            __kernel void main()
            {
                #pragma unroll
                for(uint x = 0;x < 16;x++)
                {
                }
            }"""
        self.assert_minify(data, "__kernel void a(){\n#pragma unroll\nfor(uint b=0;b<16;b++){}}")

    def test_statement_brackets(self):
        # Single statement, no brackets.
        data = r"""
            __kernel void main()
            {
                int test = 0;
                if(true)
                {
                    test = 0;
                }
                else if(false)
                {
                    test = 0;
                }
                else
                {
                    test = 0;
                }

                while(true)
                {
                    test = 0;
                }

                do
                {
                    test = 0;
                } while(true);

                for(;;)
                {
                    test = 0;
                }
            }"""
        self.assert_minify(data, "__kernel void a(){int b=0;if(true)b=0;else if(false)b=0;else b=0;while(true)b=0;do b=0;while(true);for(;;)b=0;}")
        # Multiple statements, brackets.
        data = r"""
            __kernel void main()
            {
                int test = 0;
                if(true)
                {
                    test = 0;
                    test = 1;
                }
                else if(false)
                {
                    test = 0;
                    test = 1;
                }
                else
                {
                    test = 0;
                    test = 1;
                }

                while(true)
                {
                    test = 0;
                    test = 1;
                }

                do
                {
                    test = 0;
                    test = 1;
                } while(true);

                for(;;)
                {
                    test = 0;
                    test = 1;
                }
            }"""
        self.assert_minify(data, "__kernel void a(){int b=0;if(true){b=0;b=1;}else if(false){b=0;b=1;}else{b=0;b=1;}while(true){b=0;b=1;}do{b=0;b=1;}while(true);for(;;){b=0;b=1;}}")

    def test_group_variable_declarations(self):
        data = r"""
            __kernel void main()
            {
                struct Test
                {
                    float first;
                    float second;
                    float third;
                    int fourth;
                    float fifth;
                };

                float first;
                float second = 1.0f;
                float third;
                int fourth;
                float fifth;
            }"""
        self.assert_minify(data, "__kernel void a(){struct b{float a,b,c;int d;float e;};float c,d=1.0f,e;int f;float g;}")
        data = r"""
            __kernel void main()
            {
                struct Test
                {
                    float* first;
                    float* second;
                    float* third;
                    int* fourth;
                    float* fifth;
                };

                float* first;
                float* second = 0;
                float* third;
                int* fourth;
                float* fifth;
            }"""
        self.assert_minify(data, "__kernel void a(){struct b{float*a,*b,*c;int*d;float*e;};float*c,*d=0,*e;int*f;float*g;}")

    def test_minify_kernel_names(self):
        data = r"""
            void func()
            {
            }
            __kernel void main()
            {
            }"""
        self.assert_minify(data, "void a(){}__kernel void b(){}", minify_kernel_names=True)
        self.assert_minify(data, "void a(){}__kernel void main(){}", minify_kernel_names=False)

    def test_global_postfix(self):
        data = r"""
            typedef uint gtypedef;
            struct gstruct
            {
                gtypedef var;
            };
            void gfunc()
            {
            }
            __kernel void gkernel()
            {
                typedef uint ltypedef;
                struct lstruct
                {
                    gtypedef gvar;
                    ltypedef lvar;
                };
            }"""
        self.assert_minify(data, "typedef uint a_global;struct b_global{a_global a;};void c_global(){}__kernel void d_global(){typedef uint a;struct b{a_global a;a b;};}", global_postfix="_global")

    def test_function_args(self):
        data = r"""
            void func(__global float* arg0,int arg1,float arg2[10])
            {
            }"""
        self.assert_minify(data, "void a(__global float*b,int c,float d[10]){}")

    def test_remove_unnecessary_vector_accessors(self):
        data = r"""
            __kernel void main()
            {
                float4 test = (float4)(0.0f,1.0f,2.0f,3.0f);
                float4 test2 = test.xyzw;
                test2 = test.s0123;
            }"""
        self.assert_minify(data, "__kernel void a(){float4 b=(float4)(0.0f,1.0f,2.0f,3.0f),c=b;c=b;}")


if __name__ == "__main__":
    unittest.main()
