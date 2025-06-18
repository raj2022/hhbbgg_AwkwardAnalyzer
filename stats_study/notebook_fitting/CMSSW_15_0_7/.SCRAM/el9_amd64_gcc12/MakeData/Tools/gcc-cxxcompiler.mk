ALL_TOOLS      += gcc-cxxcompiler
gcc-cxxcompiler_EX_FLAGS_CPPDEFINES  := -DGNU_GCC -D_GNU_SOURCE
gcc-cxxcompiler_EX_FLAGS_CXXFLAGS  := -O3 -pthread -pipe -Werror=main -Werror=pointer-arith -Werror=overlength-strings -Wno-vla -Werror=overflow -std=c++20 -ftree-vectorize -Werror=array-bounds -Werror=format-contains-nul -Werror=type-limits -fvisibility-inlines-hidden -fno-math-errno --param vect-max-version-for-alias-checks=50 -Xassembler --compress-debug-sections -Wno-error=array-bounds -Warray-bounds -fuse-ld=bfd -march=x86-64-v3 -felide-constructors -fmessage-length=0 -Wall -Wno-non-template-friend -Wno-long-long -Wreturn-type -Wextra -Wpessimizing-move -Wclass-memaccess -Wno-cast-function-type -Wno-unused-but-set-parameter -Wno-ignored-qualifiers -Wno-unused-parameter -Wunused -Wparentheses -Werror=return-type -Werror=missing-braces -Werror=unused-value -Werror=unused-label -Werror=address -Werror=format -Werror=sign-compare -Werror=write-strings -Werror=delete-non-virtual-dtor -Werror=strict-aliasing -Werror=narrowing -Werror=unused-but-set-variable -Werror=reorder -Werror=unused-variable -Werror=conversion-null -Werror=return-local-addr -Wnon-virtual-dtor -Werror=switch -fdiagnostics-show-option -Wno-unused-local-typedefs -Wno-attributes -Wno-psabi
gcc-cxxcompiler_EX_FLAGS_CXXFLAGS_TARGETS_X86_64_V2  := -march=x86-64-v2
gcc-cxxcompiler_EX_FLAGS_CXXSHAREDFLAGS  := -shared -Wl,-E
gcc-cxxcompiler_EX_FLAGS_CXXSHAREDOBJECTFLAGS  := -fPIC
gcc-cxxcompiler_EX_FLAGS_LDFLAGS  := -Wl,-E -Wl,--hash-style=gnu -Wl,--as-needed -Wl,-z,noexecstack
gcc-cxxcompiler_EX_FLAGS_LD_UNIT  := -r -z muldefs
gcc-cxxcompiler_EX_FLAGS_LTO_FLAGS  := -flto=auto -fipa-icf -flto-odr-type-merging -fno-fat-lto-objects -Wodr
gcc-cxxcompiler_EX_FLAGS_PGO_FLAGS  := -fprofile-prefix-path=$(LOCALTOP) -fprofile-update=prefer-atomic -fprofile-correction
gcc-cxxcompiler_EX_FLAGS_PGO_GENERATE_FLAGS  := -fprofile-generate=%q{CMSSW_PGO_DIRECTORY}/cmssw/%q{CMSSW_CPU_TYPE}
gcc-cxxcompiler_EX_FLAGS_PGO_USE_FLAGS  := -fprofile-use=@{CMSSW_PGO_DIRECTORY}/cmssw/@{CMSSW_CPU_TYPE} -fprofile-partial-training
gcc-cxxcompiler_EX_FLAGS_REM_CXXFLAGS_TARGETS_X86_64_V2  := -march=x86-64-v3

