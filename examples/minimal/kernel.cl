__kernel void add_one(__global float* input,__global float* output)
{
	uint index = get_global_id(0);
	output[index] = input[index] + 1.0f;
}

