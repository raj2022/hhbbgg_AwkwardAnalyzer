ALL_TOOLS      += triton-inference-client
triton-inference-client_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/triton-inference-client/2.25.0-1962fddc1ae79a2aa1cc3a14471f1925/include
triton-inference-client_EX_LIB := grpcclient tritoncommonmodelconfig
triton-inference-client_EX_USE := protobuf grpc cuda re2

