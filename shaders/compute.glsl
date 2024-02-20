#version 430

layout (local_size_x = 1, local_size_y = 1, local_size_z = 1) in;

layout(binding = 0) buffer InputBuffer {
    uint inputData[30000];
};

layout(binding = 1) buffer OutputBuffer {
    uint outputData[938];
};

void main() {
    uint globalID = gl_GlobalInvocationID.x + 200 * gl_GlobalInvocationID.y;
    uint data = inputData[globalID] & 1u;

    // avoid collisions
    atomicOr(outputData[int(globalID / 32)], data << int(globalID % 32));
}
