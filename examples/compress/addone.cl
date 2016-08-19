__kernel void AddOne(__global float* input,__global float* output)
{
	uint index = get_global_id(0);
	output[index] = input[index] + 1.0f;
}

