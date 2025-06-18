ALL_TOOLS      += celeritas
celeritas_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/celeritas/v0.4.1-80a69cbc75b90d06ccf5255c1969681d/include
celeritas_EX_LIB := accel celeritas corecel
celeritas_EX_USE := geant4core expat xerces-c vecgeom_interface vecgeom
celeritas_EX_FLAGS_REM_CXXFLAGS  := -Werror=missing-braces

