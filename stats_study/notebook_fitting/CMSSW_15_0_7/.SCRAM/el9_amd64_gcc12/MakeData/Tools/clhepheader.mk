ALL_TOOLS      += clhepheader
clhepheader_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/clhep/2.4.7.1-00d95dad51c51a565a6a059e09321311/include
clhepheader_EX_USE := root_cxxdefaults
clhepheader_EX_FLAGS_ROOTCLING_ARGS  := -moduleMapFile=$(CLHEP_BASE)/include/module.modulemap
clhepheader_EX_FLAGS_SYSTEM_INCLUDE  := 1

