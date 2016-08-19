#include <cassert>
#include <iostream>
#include <vector>
#ifdef MAC
#include <OpenCL/cl.hpp>
#else
#include <CL/cl.hpp>
#endif
#include "kernel1.cl.h"
#include "kernel2.cl.h"


int main(int argc,char* argv[])
{
	static const size_t BUFFER_SIZE = 16;

	//Setup a buffer of input data to be processed.
	std::vector<float> inputData(BUFFER_SIZE);
	std::fill(inputData.begin(),inputData.end(),1.0f);

	//Setup OpenCL.
	std::vector<cl::Platform> platforms;
	cl::Platform::get(&platforms);
	if(platforms.empty())
		return -1;

	std::vector<cl::Device> devices;
	platforms[0].getDevices(CL_DEVICE_TYPE_ALL,&devices);
	if(devices.empty())
		return -1;

	devices.resize(1);
	cl::Context context(devices,nullptr,nullptr,nullptr,nullptr);

	//Build minified OpenCL sources.
	cl::Program::Sources sources;
	sources.push_back(std::pair<const char*,std::size_t>(reinterpret_cast<const char*>(KERNEL1_DATA),KERNEL1_SIZE));
	sources.push_back(std::pair<const char*,std::size_t>(reinterpret_cast<const char*>(KERNEL2_DATA),KERNEL2_SIZE));

	cl::Program program(context,sources,nullptr);
	program.build(devices,nullptr);

	//Setup data buffers.
	cl::Buffer buffer1(context,CL_MEM_READ_WRITE,BUFFER_SIZE * sizeof(float),nullptr,nullptr);
	cl::Buffer buffer2(context,CL_MEM_READ_WRITE,BUFFER_SIZE * sizeof(float),nullptr,nullptr);

	//Prepare kernels to be run.
	cl::Kernel kernel1(program,KERNEL1_FUNCTION_MULINDEX,nullptr);
	kernel1.setArg(0,buffer1);
	kernel1.setArg(1,buffer2);
	cl::Kernel kernel2(program,KERNEL2_FUNCTION_MUL2,nullptr);
	kernel2.setArg(0,buffer2);
	kernel2.setArg(1,buffer1);
	
	//Upload data to device.
	cl::CommandQueue commandQueue(context,devices[0],0,nullptr);
	commandQueue.enqueueWriteBuffer(buffer1,CL_TRUE,0,BUFFER_SIZE * sizeof(float),&inputData[0],0,nullptr);
	
	//Run kernels.
	const size_t globalWorkSize = 16384;
	const size_t localWorkSize = 16;
	commandQueue.enqueueNDRangeKernel(kernel1,0,globalWorkSize,localWorkSize,nullptr,nullptr);
	commandQueue.enqueueNDRangeKernel(kernel2,0,globalWorkSize,localWorkSize,nullptr,nullptr);
	
	//Download processed data from device.
	std::vector<float> outputData(BUFFER_SIZE);
	std::fill(outputData.begin(),outputData.end(),45.0f);
	commandQueue.enqueueReadBuffer(buffer1,CL_TRUE,0,BUFFER_SIZE * sizeof(float),&outputData[0],nullptr,nullptr);
	
	//Confirm data was processed successfully.
	for(unsigned int x = 0;x < BUFFER_SIZE;x++)
	{
		if(outputData[x] != (x * 2.0f))
		{
			std::cout << "Kernel failed to run properly." << std::endl;
			break;
		}
	}

	return 0;
}

