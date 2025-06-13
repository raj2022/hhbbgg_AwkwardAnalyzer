ALL_TOOLS      += grpc
grpc_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/grpc/1.35.0-50be0bb6dd40c37c7098253da39e9cfe/include
grpc_EX_LIB := grpc grpc++ grpc++_reflection
grpc_EX_USE := protobuf openssl pcre abseil-cpp c-ares re2
grpc_EX_FLAGS_SYSTEM_INCLUDE  := 1

