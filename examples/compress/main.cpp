#include <iostream>
#include <vector>
#include <zlib.h>
#include "addone.cl.h"


int main(int argc,char* argv[])
{
	//Setup zlib.
	z_stream strm;
	strm.zalloc = Z_NULL;
	strm.zfree = Z_NULL;
	strm.opaque = Z_NULL;
	strm.avail_in = 0;
	strm.next_in = Z_NULL;
	int result = inflateInit(&strm);
	if(result != Z_OK)
	{
		std::cout << "Could not initialize zlib." << std::endl;
		return -1;
	}

	//Create a new input buffer with the required zlib header. Run oclminify
	//without the --strip-zlib-header flag to automatically include these two
	//bytes.
	std::vector<unsigned char> inBufferWithHeader(ADDONE_SIZE + 2);
	inBufferWithHeader[0] = 0x78;
	inBufferWithHeader[1] = 0xDA;
	std::copy(ADDONE_DATA,ADDONE_DATA + ADDONE_SIZE,inBufferWithHeader.begin() + 2);

	unsigned int outBufferSize = 0;
	std::vector<char> outBuffer(512);

	//Decompress buffer.
	strm.avail_in = inBufferWithHeader.size();
	strm.next_in = &inBufferWithHeader[0];
	do
	{
		if(outBuffer.size() < outBufferSize + 512)
			outBuffer.resize(outBufferSize + 512);

		strm.avail_out = 512;
		strm.next_out = reinterpret_cast<unsigned char*>(&outBuffer[outBufferSize]);
		result = inflate(&strm,Z_NO_FLUSH);
		switch(result)
		{
			case Z_STREAM_ERROR:
			case Z_NEED_DICT:
			case Z_DATA_ERROR:
			case Z_MEM_ERROR:
				inflateEnd(&strm);
				std::cout << "Zlib error. Input buffer corrupt?" << std::endl;
				return -1;
			default:
				break;
		}

		outBufferSize += 512 - strm.avail_out;
	} while(strm.avail_out == 0);

	//Clean-up.
	inflateEnd(&strm);

	//Print the decompressed OpenCL source.
	std::cout.write(outBuffer.data(),outBufferSize);
	std::cout << std::endl;

	return 0;
}

