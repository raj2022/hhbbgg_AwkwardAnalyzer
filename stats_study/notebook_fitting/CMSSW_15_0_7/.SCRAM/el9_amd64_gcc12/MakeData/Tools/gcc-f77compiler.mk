ALL_TOOLS      += gcc-f77compiler
gcc-f77compiler_EX_LIB := gfortran m
gcc-f77compiler_EX_FLAGS_FFLAGS  := -fno-second-underscore -Wunused -Wuninitialized -O3 -cpp -std=legacy
gcc-f77compiler_EX_FLAGS_FOPTIMISEDFLAGS  := -O3
gcc-f77compiler_EX_FLAGS_FSHAREDOBJECTFLAGS  := -fPIC

