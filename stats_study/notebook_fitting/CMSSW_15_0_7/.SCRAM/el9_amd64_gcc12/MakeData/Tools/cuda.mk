ALL_TOOLS      += cuda
ALL_LIB_TYPES += CUDA_LIB
cuda_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/cuda/12.8.0-5a6d49e4693d62148340846b99d6a8e3/include
cuda_EX_LIB := cudart cudadevrt nvToolsExt
cuda_EX_CUDA_LIB := cudadevrt
cuda_EX_USE := cuda-stubs
cuda_EX_FLAGS_CUDA_FLAGS  := -std=c++20 -O3 --generate-line-info --source-in-ptx --display-error-number --expt-relaxed-constexpr --extended-lambda -gencode arch=compute_60,code=[sm_60,compute_60] -gencode arch=compute_70,code=[sm_70,compute_70] -gencode arch=compute_75,code=[sm_75,compute_75] -gencode arch=compute_80,code=[sm_80,compute_80] -gencode arch=compute_89,code=[sm_89,compute_89] -Wno-deprecated-gpu-targets -diag-suppress=3012 -diag-suppress=3189 -Xcudafe --diag_suppress=esa_on_defaulted_function_ignored -Xcudafe --gnu_version=120300 --cudart shared
cuda_EX_FLAGS_CUDA_HOST_CXXFLAGS  := -std=c++20 -march=x86-64-v2
cuda_EX_FLAGS_REM_CUDA_HOST_CXXFLAGS  := -std=% %potentially-evaluated-expression -march=%

