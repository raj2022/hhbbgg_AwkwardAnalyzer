ALL_TOOLS      += llvm-cxxcompiler
llvm-cxxcompiler_EX_USE := gcc-cxxcompiler
llvm-cxxcompiler_EX_FLAGS_CXXFLAGS  := -Wno-c99-extensions -Wno-c++11-narrowing -D__STRICT_ANSI__ -Wno-unused-private-field -Wno-unknown-pragmas -Wno-unused-command-line-argument -Wno-unknown-warning-option -ftemplate-depth=512 -Wno-error=potentially-evaluated-expression -Wno-tautological-type-limit-compare -Wno-vla-cxx-extension -fsized-deallocation --gcc-toolchain=/cvmfs/cms.cern.ch/el9_amd64_gcc12/external/gcc/12.3.1-40d504be6370b5a30e3947a6e575ca28
llvm-cxxcompiler_EX_FLAGS_REM_CXXFLAGS  := -Wno-non-template-friend -Werror=format-contains-nul -Werror=maybe-uninitialized -Werror=unused-but-set-variable -Werror=return-local-addr -fipa-pta -frounding-math -mrecip -fno-crossjumping -fno-aggressive-loop-optimizations -funroll-all-loops
llvm-cxxcompiler_EX_FLAGS_REM_LTO_FLAGS  := -fipa-icf -flto-odr-type-merging -fno-fat-lto-objects
llvm-cxxcompiler_EX_FLAGS_REM_PGO_FLAGS  := -fprofile%

