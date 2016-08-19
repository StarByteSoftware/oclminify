__kernel void Mul2(__global float* input,__global float* output)
{
	uint index = get_global_id(0);
	output[index] = input[index] * 2.0f;
}

