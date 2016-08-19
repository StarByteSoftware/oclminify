#include <stdio.h>
#include <string.h>
#ifdef MAC
#include <OpenCL/cl.h>
#else
#include <CL/cl.h>
#endif
#include "opencl.cl.h"


int main(int argc,char* argv[])
{
	static const size_t BUFFER_SIZE = 16;
	static const size_t BUFFER_SIZE_BYTES = 16 * sizeof(float);

	//Setup a buffer of input data to be processed.
	float inputBuffer[BUFFER_SIZE];
	memset(inputBuffer,0,BUFFER_SIZE_BYTES);

	//Setup OpenCL.
	cl_platform_id platform;
	clGetPlatformIDs(1,&platform,NULL);
	cl_device_id device;
	clGetDeviceIDs(platform,CL_DEVICE_TYPE_GPU,1,&device,NULL);
	cl_context context = clCreateContext(NULL,1,&device,NULL,NULL,NULL);

	//Build minified OpenCL sources.
	const char* kernelSources[] = {KERNEL_DATA};
	const size_t kernelSourceSizes[] = {KERNEL_SIZE};
	cl_program program = clCreateProgramWithSource(context,1,kernelSources,kernelSourceSizes,NULL);
	clBuildProgram(program,0,NULL,NULL,NULL,NULL);

	//Prepare kernel to be run.
	cl_mem hostBuffer = clCreateBuffer(context,CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR,BUFFER_SIZE_BYTES,inputBuffer,NULL);
	cl_mem deviceBuffer = clCreateBuffer(context,CL_MEM_WRITE_ONLY,BUFFER_SIZE_BYTES,NULL,NULL);

	cl_kernel kernel = clCreateKernel(program,KERNEL_FUNCTION_ADD_ONE,NULL);
	clSetKernelArg(kernel,0,sizeof(cl_mem),&hostBuffer);
	clSetKernelArg(kernel,1,sizeof(cl_mem),&deviceBuffer);

	cl_command_queue queue = clCreateCommandQueue(context,device,0,NULL);

	//Run kernel.
	const size_t globalWorkSize = 16384;
	const size_t localWorkSize = 16;
	clEnqueueNDRangeKernel(queue,kernel,1,0,&globalWorkSize,&localWorkSize,0,NULL,NULL);

	//Fetch the processed data.
	float outputBuffer[BUFFER_SIZE];
	memset(outputBuffer,0xFF,BUFFER_SIZE_BYTES);
	clEnqueueReadBuffer(queue,deviceBuffer,CL_TRUE,0,BUFFER_SIZE_BYTES,outputBuffer,0,NULL,NULL);

	//Confirm data was processed successfully.
	for(unsigned int x = 0;x < BUFFER_SIZE;x++)
	{
		if(outputBuffer[x] != 1.0f)
		{
			printf("Kernel failed to run properly.\n");
			break;
		}
	}

	//Clean-up.
	clReleaseMemObject(hostBuffer);
	clReleaseMemObject(deviceBuffer);
	clReleaseKernel(kernel);
	clReleaseCommandQueue(queue);
	clReleaseProgram(program);
	clReleaseContext(context);

	return 0;
}

