ALL_TOOLS      += rocm
rocm_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/rocm/6.3.2-dd4ace0770f12ddb6078527b081d5a79/include
rocm_EX_LIB := amdhip64 hsa-runtime64 rocm_smi64
rocm_EX_USE := fmt
rocm_EX_FLAGS_CPPDEFINES  := -D__HIP_PLATFORM_HCC__ -D__HIP_PLATFORM_AMD__
rocm_EX_FLAGS_REM_ROCM_HOST_CXXFLAGS  := -march=%
rocm_EX_FLAGS_ROCM_FLAGS  := --offload-arch=gfx908:sramecc+ --offload-arch=gfx90a:sramecc+ --offload-arch=gfx942:sramecc+ --offload-arch=gfx1030 --offload-arch=gfx1100 --offload-arch=gfx1102 -fgpu-rdc --target=x86_64-redhat-linux-gnu --gcc-toolchain=$(COMPILER_PATH)
rocm_EX_FLAGS_ROCM_HOST_CXXFLAGS  := -march=x86-64-v2
rocm_EX_FLAGS_SYSTEM_INCLUDE  := 1

