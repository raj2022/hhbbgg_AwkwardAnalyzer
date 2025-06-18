ALL_TOOLS      += abseil-cpp
abseil-cpp_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/abseil-cpp/20220623.1-9b98bf0b6fbdbf3c6ad1edfd9552f7ea/include
abseil-cpp_EX_LIB := absl_bad_any_cast_impl absl_bad_optional_access absl_bad_variant_access absl_base absl_city absl_civil_time absl_cord absl_debugging_internal absl_demangle_internal absl_examine_stack absl_exponential_biased absl_failure_signal_handler absl_flags_commandlineflag_internal absl_flags_commandlineflag absl_flags_config absl_flags_internal absl_flags_marshalling absl_flags_parse absl_flags_private_handle_accessor absl_flags_program_name absl_flags_reflection absl_flags absl_flags_usage_internal absl_flags_usage absl_graphcycles_internal absl_hash absl_hashtablez_sampler absl_int128 absl_leak_check absl_log_severity absl_malloc_internal absl_periodic_sampler absl_random_distributions absl_random_internal_distribution_test_util absl_random_internal_platform absl_random_internal_pool_urbg absl_random_internal_randen_hwaes_impl absl_random_internal_randen_hwaes absl_random_internal_randen_slow absl_random_internal_randen absl_random_internal_seed_material absl_random_seed_gen_exception absl_random_seed_sequences absl_raw_hash_set absl_raw_logging_internal absl_scoped_set_env absl_spinlock_wait absl_stacktrace absl_statusor absl_status absl_strerror absl_str_format_internal absl_strings_internal absl_strings absl_symbolize absl_synchronization absl_throw_delegate absl_time absl_time_zone

ALL_TOOLS      += alpaka-cuda
alpaka-cuda_EX_USE := alpaka cuda
alpaka-cuda_EX_FLAGS_CUDA_FLAGS  := -DALPAKA_ACC_GPU_CUDA_ENABLED -DALPAKA_ACC_GPU_CUDA_ONLY_MODE -UALPAKA_HOST_ONLY
alpaka-cuda_EX_FLAGS_CXXFLAGS  := -DALPAKA_ACC_GPU_CUDA_ENABLED -DALPAKA_ACC_GPU_CUDA_ONLY_MODE -DALPAKA_HOST_ONLY
alpaka-cuda_EX_FLAGS_GENREFLEX_CPPFLAGS  := -DALPAKA_ACC_GPU_CUDA_ENABLED -DALPAKA_ACC_GPU_CUDA_ONLY_MODE -DALPAKA_HOST_ONLY

ALL_TOOLS      += alpaka-rocm
alpaka-rocm_EX_USE := alpaka rocm
alpaka-rocm_EX_FLAGS_CXXFLAGS  := -DALPAKA_ACC_GPU_HIP_ENABLED -DALPAKA_ACC_GPU_HIP_ONLY_MODE -DALPAKA_HOST_ONLY
alpaka-rocm_EX_FLAGS_GENREFLEX_CPPFLAGS  := -DALPAKA_ACC_GPU_HIP_ENABLED -DALPAKA_ACC_GPU_HIP_ONLY_MODE -DALPAKA_HOST_ONLY
alpaka-rocm_EX_FLAGS_ROCM_FLAGS  := -DALPAKA_ACC_GPU_HIP_ENABLED -DALPAKA_ACC_GPU_HIP_ONLY_MODE -UALPAKA_HOST_ONLY

ALL_TOOLS      += alpaka-serial
alpaka-serial_EX_USE := alpaka
alpaka-serial_EX_FLAGS_CXXFLAGS  := -DALPAKA_ACC_CPU_B_SEQ_T_SEQ_ENABLED
alpaka-serial_EX_FLAGS_GENREFLEX_CPPFLAGS  := -DALPAKA_ACC_CPU_B_SEQ_T_SEQ_ENABLED

ALL_TOOLS      += alpaka-tbb
alpaka-tbb_EX_USE := alpaka tbb
alpaka-tbb_EX_FLAGS_CXXFLAGS  := -DALPAKA_ACC_CPU_B_TBB_T_SEQ_ENABLED
alpaka-tbb_EX_FLAGS_GENREFLEX_CPPFLAGS  := -DALPAKA_ACC_CPU_B_TBB_T_SEQ_ENABLED

ALL_TOOLS      += alpaka
alpaka_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/alpaka/1.2.0-394ec8bfe735ddd431905e16166bcefe/include
alpaka_EX_USE := boost
alpaka_EX_FLAGS_CUDA_FLAGS  := -DALPAKA_DEFAULT_HOST_MEMORY_ALIGNMENT=128 -DALPAKA_DISABLE_VENDOR_RNG
alpaka_EX_FLAGS_CXXFLAGS  := -DALPAKA_DEFAULT_HOST_MEMORY_ALIGNMENT=128 -DALPAKA_DISABLE_VENDOR_RNG
alpaka_EX_FLAGS_GENREFLEX_CPPFLAGS  := -DALPAKA_DEFAULT_HOST_MEMORY_ALIGNMENT=128 -DALPAKA_DISABLE_VENDOR_RNG

ALL_TOOLS      += alpgen

ALL_TOOLS      += axol1tl

ALL_TOOLS      += blackhat
blackhat_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/blackhat/0.9.9-1c4d15453173567f06dd11a7f5263d1e/include
blackhat_EX_LIB := Ampl_eval BG BH BHcore CutPart Cut_wCI Cuteval Integrals Interface OLA RatPart Rateval Spinors assembly ratext
blackhat_EX_USE := qd

ALL_TOOLS      += boost
boost_EX_LIB := boost_thread boost_date_time
boost_EX_USE := boost_header

ALL_TOOLS      += boost_chrono
boost_chrono_EX_LIB := boost_chrono
boost_chrono_EX_USE := boost_system boost

ALL_TOOLS      += boost_filesystem
boost_filesystem_EX_LIB := boost_filesystem
boost_filesystem_EX_USE := boost_system boost

ALL_TOOLS      += boost_header
boost_header_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/boost/1.80.0-37bdc3309b0baa2e05e8d12d5a3ece01/include
boost_header_EX_USE := sockets root_cxxdefaults
boost_header_EX_FLAGS_CPPDEFINES  := -DBOOST_SPIRIT_THREADSAFE -DPHOENIX_THREADSAFE -DBOOST_MATH_DISABLE_STD_FPCLASSIFY -DBOOST_UUID_RANDOM_PROVIDER_FORCE_POSIX
boost_header_EX_FLAGS_CXXFLAGS  := -Wno-error=unused-variable
boost_header_EX_FLAGS_SYSTEM_INCLUDE  := 1

ALL_TOOLS      += boost_iostreams
boost_iostreams_EX_LIB := boost_iostreams
boost_iostreams_EX_USE := boost

ALL_TOOLS      += boost_mpi
boost_mpi_EX_LIB := boost_mpi
boost_mpi_EX_USE := boost boost_serialization

ALL_TOOLS      += boost_program_options
boost_program_options_EX_LIB := boost_program_options
boost_program_options_EX_USE := boost

ALL_TOOLS      += boost_python
boost_python_EX_LIB := boost_python39
boost_python_EX_USE := boost_header python3

ALL_TOOLS      += boost_regex
boost_regex_EX_LIB := boost_regex
boost_regex_EX_USE := boost

ALL_TOOLS      += boost_serialization
boost_serialization_EX_LIB := boost_serialization
boost_serialization_EX_USE := boost

ALL_TOOLS      += boost_system
boost_system_EX_LIB := boost_system
boost_system_EX_USE := boost

ALL_TOOLS      += boost_test
boost_test_EX_LIB := boost_unit_test_framework
boost_test_EX_USE := boost

ALL_TOOLS      += bz2lib
bz2lib_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/bz2lib/1.0.6-d065ccd79984efc6d4660f410e4c81de/include
bz2lib_EX_LIB := bz2
bz2lib_EX_USE := root_cxxdefaults

ALL_TOOLS      += c-ares
c-ares_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/c-ares/1.15.0-bdde3279d139e03a19f0e9ee4aa57885/include
c-ares_EX_LIB := cares

ALL_TOOLS      += catch2
catch2_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/catch2/2.13.6-17102db92de47c6a473c6e67627c548a/include

ALL_TOOLS      += celeritas
celeritas_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/celeritas/v0.4.1-80a69cbc75b90d06ccf5255c1969681d/include
celeritas_EX_LIB := accel celeritas corecel
celeritas_EX_USE := geant4core expat xerces-c vecgeom_interface vecgeom
celeritas_EX_FLAGS_REM_CXXFLAGS  := -Werror=missing-braces

ALL_TOOLS      += cepgen
cepgen_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/cepgen/1.2.5-863f869abe1d3ab358ea5a01a4f07b31/include
cepgen_EX_LIB := CepGen CepGenHepMC2 CepGenHepMC3 CepGenLHAPDF CepGenProcesses CepGenPythia6
cepgen_EX_USE := gsl openblas hepmc hepmc3 lhapdf pythia6

ALL_TOOLS      += cicada

ALL_TOOLS      += clang-uml
clang-uml_EX_USE := yaml-cpp zlib

ALL_TOOLS      += classlib
classlib_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/classlib/3.1.3-2827e9dbeb7dd2aced5a46b8a966dfab/include
classlib_EX_LIB := classlib
classlib_EX_USE := pcre root_cxxdefaults
classlib_EX_FLAGS_CPPDEFINES  := -D__STDC_LIMIT_MACROS -D__STDC_FORMAT_MACROS

ALL_TOOLS      += clhep
clhep_EX_LIB := CLHEP
clhep_EX_USE := clhepheader

ALL_TOOLS      += clhepheader
clhepheader_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/clhep/2.4.7.1-00d95dad51c51a565a6a059e09321311/include
clhepheader_EX_USE := root_cxxdefaults
clhepheader_EX_FLAGS_ROOTCLING_ARGS  := -moduleMapFile=$(CLHEP_BASE)/include/module.modulemap
clhepheader_EX_FLAGS_SYSTEM_INCLUDE  := 1

ALL_TOOLS      += clue
clue_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/clue/1.0.0-efd24f218ee12cf4a23695b1c8e69866/include
clue_EX_USE := alpaka

ALL_TOOLS      += cmssw-config

ALL_TOOLS      += cmsswdata
cmsswdata_EX_FLAGS_CMSSW_DATA_PACKAGE  := Alignment/OfflineValidation=V00-03-00 CalibCalorimetry/CaloMiscalibTools=V01-00-00 CalibCalorimetry/EcalTrivialCondModules=V00-03-00 CalibPPS/ESProducers=V01-05-00 CalibTracker/SiPixelESProducers=V02-04-00 CalibTracker/SiStripDCS=V01-01-00 Calibration/Tools=V01-00-00 CondFormats/JetMETObjects=V01-00-03 CondTools/Hcal=V00-01-00 CondTools/SiPhase2Tracker=V00-02-00 CondTools/SiStrip=V00-02-00 Configuration/Generator=V01-10-00 DQM/DTMonitorClient=V00-01-00 DQM/EcalMonitorClient=V00-03-00 DQM/HcalTasks=V00-01-00 DQM/Integration=V00-09-00 DQM/PhysicsHWW=V01-00-00 DQM/SiStripMonitorClient=V01-01-00 DataFormats/Common=V00-02-00 DataFormats/DetId=V00-02-00 DataFormats/FEDRawData=V00-02-00 DataFormats/HLTReco=V00-02-00 DataFormats/L1Scouting=V00-04-00 DataFormats/L1ScoutingRawData=V00-03-00 DataFormats/L1TGlobal=V00-03-00 DataFormats/PatCandidates=V01-01-00 DataFormats/Scouting=V00-04-00 DataFormats/SiStripCluster=V00-02-00 DetectorDescription/Schema=V02-03-00 EgammaAnalysis/ElectronTools=V00-04-00 EventFilter/L1TRawToDigi=V01-00-00 FWCore/Modules=V00-01-00 FastSimulation/MaterialEffects=V05-00-00 FastSimulation/TrackingRecHitProducer=V01-00-03 Fireworks/Geometry=V07-06-00 GeneratorInterface/EvtGenInterface=V02-11-00 GeneratorInterface/ReggeGribovPartonMCInterface=V00-00-02 Geometry/DTGeometryBuilder=V00-01-00 Geometry/HGCalMapping=V00-01-00 Geometry/TestReference=V00-16-00 HLTrigger/JetMET=V01-00-00 HeterogeneousCore/SonicTriton=V00-03-00 IOPool/Input=V00-03-00 L1Trigger/CSCTriggerPrimitives=V00-12-00 L1Trigger/DTTriggerPhase2=V00-03-00 L1Trigger/L1CaloTrigger=V00-01-00 L1Trigger/L1TCalorimeter=V01-03-00 L1Trigger/L1TGlobal=V00-04-00 L1Trigger/L1THGCal=V01-08-00 L1Trigger/L1TMuon=V01-12-00 L1Trigger/L1TMuonEndCapPhase2=V00-01-00 L1Trigger/L1TTrackMatch=V00-01-00 L1Trigger/Phase2L1ParticleFlow=V00-07-00 L1Trigger/RPCTrigger=V00-15-00 L1Trigger/TrackFindingTMTT=V00-02-00 L1Trigger/TrackFindingTracklet=V00-04-00 L1Trigger/TrackTrigger=V00-03-00 L1Trigger/VertexFinder=V00-01-00 L1TriggerConfig/L1TConfigProducers=V00-01-00 MagneticField/Engine=V00-01-00 MagneticField/Interpolation=V01-02-00 PhysicsTools/NanoAOD=V01-06-00 PhysicsTools/PatUtils=V00-05-00 RecoBTag/CTagging=V01-00-03 RecoBTag/Combined=V01-30-00 RecoBTag/SecondaryVertex=V02-00-04 RecoBTag/SoftLepton=V01-00-01 RecoCTPPS/TotemRPLocal=V00-02-00 RecoEcal/EgammaClusterProducers=V00-04-00 RecoEgamma/EgammaPhotonProducers=V00-05-00 RecoEgamma/ElectronIdentification=V01-14-00 RecoEgamma/PhotonIdentification=V01-08-00 RecoHGCal/TICL=V00-05-00 RecoHI/HiJetAlgos=V01-00-01 RecoJets/JetProducers=V05-15-00 RecoLocalCalo/EcalDeadChannelRecoveryAlgos=V01-01-00 RecoMET/METPUSubtraction=V01-03-00 RecoMTD/TimingIDTools=V00-01-00 RecoMuon/MuonIdentification=V01-16-00 RecoMuon/TrackerSeedGenerator=V00-07-00 RecoPPS/Local=V00-02-00 RecoParticleFlow/PFBlockProducer=V02-04-02 RecoParticleFlow/PFProducer=V16-02-00 RecoParticleFlow/PFTracking=V13-01-00 RecoTauTag/TrainingFiles=V00-10-00 RecoTracker/DisplacedRegionalTracking=V00-01-00 RecoTracker/FinalTrackSelectors=V01-05-00 RecoTracker/LSTCore=V00-01-00 RecoTracker/MkFit=V00-15-00 RecoTracker/TkSeedGenerator=V00-03-00 SLHCUpgradeSimulations/Geometry=V01-00-10 SimCalorimetry/EcalEBTrigPrimProducers=V00-01-00 SimG4CMS/Calo=V03-05-00 SimG4CMS/Forward=V02-04-00 SimG4CMS/HGCalTestBeam=V01-00-00 SimPPS/PPSPixelDigiProducer=V00-00-02 SimTracker/SiStripDigitizer=V01-01-00 SimTransport/HectorProducer=V01-00-01 SimTransport/PPSProtonTransport=V00-02-00 SimTransport/TotemRPProtonTransportParametrization=V00-01-00 Validation/Geometry=V00-07-00 Validation/HGCalValidation=V00-08-00

ALL_TOOLS      += collier

ALL_TOOLS      += conifer
conifer_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/conifer/1.3-8388cac5c18380ea10ff4333c0917bbc/include
conifer_EX_USE := json

ALL_TOOLS      += coral
ALL_SCRAM_PROJECTS += coral
coral_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/cms/coral/CORAL_2_3_21-886c84ed39d66c87e88d0d2b0fa9d158/include/LCG
coral_EX_USE := root_cxxdefaults
coral_ORDER := 98000

ALL_TOOLS      += correctionlib
correctionlib_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/py3-correctionlib/2.6.4-1de964987efb91372e4d54c3ac6e84ea/lib/python3.9/site-packages/correctionlib/include
correctionlib_EX_LIB := correctionlib

ALL_TOOLS      += cppunit
cppunit_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/cppunit/1.15.x-9c5e10ac1b9ff043c0e3d26ccceb0058/include
cppunit_EX_LIB := cppunit
cppunit_EX_USE := root_cxxdefaults sockets

ALL_TOOLS      += cpu_features
cpu_features_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/cpu_features/0.9.0-1ab2439bfcc72ad9dee41653155c4b63/include
cpu_features_EX_LIB := cpu_features

ALL_TOOLS      += csctrackfinderemulation
csctrackfinderemulation_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/cms/CSCTrackFinderEmulation/1.2-4d8fc45bae4641b9aeb067b33fc0e482/include
csctrackfinderemulation_EX_LIB := CSCTrackFinderEmulation

ALL_TOOLS      += cuda-compatible-runtime
cuda-compatible-runtime_EX_USE := cuda cuda-stubs

ALL_TOOLS      += cuda-cublas
cuda-cublas_EX_LIB := cublas cublasLt
cuda-cublas_EX_USE := cuda

ALL_TOOLS      += cuda-cufft
cuda-cufft_EX_LIB := cufft cufftw
cuda-cufft_EX_USE := cuda

ALL_TOOLS      += cuda-curand
cuda-curand_EX_LIB := curand
cuda-curand_EX_USE := cuda

ALL_TOOLS      += cuda-cusolver
cuda-cusolver_EX_LIB := cusolver cusolverMg
cuda-cusolver_EX_USE := cuda

ALL_TOOLS      += cuda-cusparse
cuda-cusparse_EX_LIB := cusparse
cuda-cusparse_EX_USE := cuda

ALL_TOOLS      += cuda-gcc-support

ALL_TOOLS      += cuda-npp
cuda-npp_EX_LIB := nppial nppicc nppidei nppif nppig nppim nppist nppisu nppitc npps nppc
cuda-npp_EX_USE := cuda

ALL_TOOLS      += cuda-nvgraph
cuda-nvgraph_EX_LIB := nvgraph
cuda-nvgraph_EX_USE := cuda

ALL_TOOLS      += cuda-nvjpeg
cuda-nvjpeg_EX_LIB := nvjpeg
cuda-nvjpeg_EX_USE := cuda

ALL_TOOLS      += cuda-nvml
cuda-nvml_EX_LIB := nvidia-ml
cuda-nvml_EX_USE := cuda-stubs

ALL_TOOLS      += cuda-nvrtc
cuda-nvrtc_EX_LIB := nvrtc
cuda-nvrtc_EX_USE := cuda

ALL_TOOLS      += cuda-stubs
cuda-stubs_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/cuda/12.8.0-5a6d49e4693d62148340846b99d6a8e3/include
cuda-stubs_EX_LIB := cuda
cuda-stubs_EX_LIBDIR := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/cuda/12.8.0-5a6d49e4693d62148340846b99d6a8e3/lib64/stubs
cuda-stubs_EX_FLAGS_SKIP_TOOL_SYMLINKS  := 1

ALL_TOOLS      += cuda
ALL_LIB_TYPES += CUDA_LIB
cuda_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/cuda/12.8.0-5a6d49e4693d62148340846b99d6a8e3/include
cuda_EX_LIB := cudart cudadevrt nvToolsExt
cuda_EX_CUDA_LIB := cudadevrt
cuda_EX_USE := cuda-stubs
cuda_EX_FLAGS_CUDA_FLAGS  := -std=c++20 -O3 --generate-line-info --source-in-ptx --display-error-number --expt-relaxed-constexpr --extended-lambda -gencode arch=compute_60,code=[sm_60,compute_60] -gencode arch=compute_70,code=[sm_70,compute_70] -gencode arch=compute_75,code=[sm_75,compute_75] -gencode arch=compute_80,code=[sm_80,compute_80] -gencode arch=compute_89,code=[sm_89,compute_89] -Wno-deprecated-gpu-targets -diag-suppress=3012 -diag-suppress=3189 -Xcudafe --diag_suppress=esa_on_defaulted_function_ignored -Xcudafe --gnu_version=120300 --cudart shared
cuda_EX_FLAGS_CUDA_HOST_CXXFLAGS  := -std=c++20 -march=x86-64-v2
cuda_EX_FLAGS_REM_CUDA_HOST_CXXFLAGS  := -std=% %potentially-evaluated-expression -march=%

ALL_TOOLS      += cudnn
cudnn_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/cudnn/9.6.0.74-63c6bd34160b0d796117c27e09ddc3dc/include
cudnn_EX_LIB := cudnn
cudnn_EX_USE := cuda

ALL_TOOLS      += cupti
cupti_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/cuda/12.8.0-5a6d49e4693d62148340846b99d6a8e3/include
cupti_EX_LIB := cupti

ALL_TOOLS      += curl
curl_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/curl/7.79.0-d8c0d5017cfad573d276c56bd08114b8/include
curl_EX_LIB := curl
curl_EX_USE := root_cxxdefaults

ALL_TOOLS      += dablooms
dablooms_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/dablooms/0.9.1-6a52f3a6ac2cb636047ac50c3673033a/include
dablooms_EX_LIB := dablooms

ALL_TOOLS      += das_client

ALL_TOOLS      += davix
davix_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/davix/0.8.7-ebe196154268a6eae18fd579b3ff8ae3/include/davix
davix_EX_LIB := davix
davix_EX_USE := boost_system libxml2

ALL_TOOLS      += db6
db6_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/db6/6.2.32-0b5a52d56859c2628499360eaabc790e/include
db6_EX_LIB := db

ALL_TOOLS      += dcap
dcap_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/dcap/2.47.12-5739970a201e5ecc2d22619681b1a468/include
dcap_EX_LIB := dcap
dcap_EX_USE := root_cxxdefaults

ALL_TOOLS      += dd4hep-core
dd4hep-core_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/dd4hep/v01-29-00-5da0cfe2f5786b6dd912cac759c57571/include
dd4hep-core_EX_LIB := DDCore DDParsers
dd4hep-core_EX_USE := root_cxxdefaults root boost xerces-c clhep
dd4hep-core_EX_FLAGS_CPPDEFINES  := -DDD4HEP_USE_GEANT4_UNITS=1
dd4hep-core_EX_FLAGS_LISTCOMPONENTS  := $(DD4HEP_CORE_BASE)/bin/listcomponents_dd4hep

ALL_TOOLS      += dd4hep-geant4
dd4hep-geant4_EX_LIB := DDG4-static
dd4hep-geant4_EX_USE := geant4core dd4hep-core

ALL_TOOLS      += dd4hep
dd4hep_EX_LIB := DDAlign DDCond
dd4hep_EX_USE := dd4hep-core

ALL_TOOLS      += dip-platform-dependent
dip-platform-dependent_EX_LIB := platform-dependent
dip-platform-dependent_EX_USE := dip_interface

ALL_TOOLS      += dip
dip_EX_LIB := dip
dip_EX_USE := dip-platform-dependent log4cplus

ALL_TOOLS      += dip_interface
dip_interface_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/dip/8693f00cc422b4a15858fcd84249acaeb07b6316-999ed0028942c69e90b8ec111d6bec52/include

ALL_TOOLS      += eigen
eigen_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/eigen/3bb6a48d8c171cf20b5f8e48bfb4e424fbd4f79e-e265b266d2b30c1bebdd883980d0f9d0/include /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/eigen/3bb6a48d8c171cf20b5f8e48bfb4e424fbd4f79e-e265b266d2b30c1bebdd883980d0f9d0/include/eigen3
eigen_EX_FLAGS_CUDA_FLAGS  := --diag-suppress 20014
eigen_EX_FLAGS_CXXFLAGS  := -DEIGEN_DONT_PARALLELIZE -DEIGEN_MAX_ALIGN_BYTES=64

ALL_TOOLS      += evtgen
evtgen_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/evtgen/2.0.0-e4a6eca2058f3ba55c6b4a07949aab35/include
evtgen_EX_LIB := EvtGen EvtGenExternal
evtgen_EX_USE := hepmc pythia8 tauolapp photospp

ALL_TOOLS      += expat
expat_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/expat/2.4.8-b093687a482bf386f8f8c236c5b2efa2/include
expat_EX_LIB := expat
expat_EX_USE := root_cxxdefaults

ALL_TOOLS      += fastjet-contrib-archive
fastjet-contrib-archive_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/fastjet-contrib/1.051-6b2cbf7b2399385490e165663710d5e0/include
fastjet-contrib-archive_EX_LIB := EnergyCorrelator GenericSubtractor JetCleanser JetFFMoments Nsubjettiness ScJet SubjetCounting VariableR

ALL_TOOLS      += fastjet-contrib
fastjet-contrib_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/fastjet-contrib/1.051-6b2cbf7b2399385490e165663710d5e0/include
fastjet-contrib_EX_LIB := fastjetcontribfragile

ALL_TOOLS      += fastjet
fastjet_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/fastjet/3.4.1-71044756ca7b67339b95a884df339811/include
fastjet_EX_LIB := fastjetplugins fastjettools siscone siscone_spherical fastjet
fastjet_EX_USE := root_cxxdefaults

ALL_TOOLS      += fastjet_x86-64-v2

ALL_TOOLS      += fftjet
fftjet_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/fftjet/1.5.0-4c95f831c41530ec8fa31a87717d9e5b/include
fftjet_EX_LIB := fftjet
fftjet_EX_USE := root_cxxdefaults

ALL_TOOLS      += fftw3
fftw3_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/fftw3/3.3.8-5270bdf9998065b38f91e9aa053c73ec/include
fftw3_EX_LIB := fftw3
fftw3_EX_USE := root_cxxdefaults

ALL_TOOLS      += flatbuffers
flatbuffers_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/flatbuffers/2.0.6-979a53f6d5acdef69953225fb5d283d0/include
flatbuffers_EX_LIB := flatbuffers

ALL_TOOLS      += fmt
fmt_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/fmt/10.2.1-e35fd1db5eb3abc8ac0452e8ee427196/include
fmt_EX_LIB := fmt

ALL_TOOLS      += freetype
freetype_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/freetype/2.10.0-0a3e7e7418f34ddc4d3b2760dcabc963/include
freetype_EX_LIB := freetype-cms
freetype_EX_USE := root_cxxdefaults

ALL_TOOLS      += frontier_client
frontier_client_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/frontier_client/2.10.2-424f23c2544a35dfa84598f1f15afcc6/include
frontier_client_EX_LIB := frontier_client
frontier_client_EX_USE := root_cxxdefaults zlib expat

ALL_TOOLS      += g4hepem_interface
g4hepem_interface_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/g4hepem/20250203-b654bc164e291a346cbc61133bbb061f/include/G4HepEm

ALL_TOOLS      += g4hepemcore
g4hepemcore_EX_LIB := g4HepEmData g4HepEmInit g4HepEmRun g4HepEm
g4hepemcore_EX_USE := g4hepem_interface

ALL_TOOLS      += g4hepemstatic
g4hepemstatic_EX_LIB := g4hepem-static
g4hepemstatic_EX_USE := g4hepem_interface

ALL_TOOLS      += gbl
gbl_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/gbl/V03-01-01-b92d577a3b69b4555d76af8edac90279/include
gbl_EX_LIB := GBL
gbl_EX_USE := eigen

ALL_TOOLS      += gbl_x86-64-v2

ALL_TOOLS      += gcc-atomic
gcc-atomic_EX_LIB := atomic

ALL_TOOLS      += gcc-ccompiler
gcc-ccompiler_EX_FLAGS_CFLAGS  := -O3 -pthread
gcc-ccompiler_EX_FLAGS_CSHAREDOBJECTFLAGS  := -fPIC

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

ALL_TOOLS      += gcc-f77compiler
gcc-f77compiler_EX_LIB := gfortran m
gcc-f77compiler_EX_FLAGS_FFLAGS  := -fno-second-underscore -Wunused -Wuninitialized -O3 -cpp -std=legacy
gcc-f77compiler_EX_FLAGS_FOPTIMISEDFLAGS  := -O3
gcc-f77compiler_EX_FLAGS_FSHAREDOBJECTFLAGS  := -fPIC

ALL_TOOLS      += gcc-plugin
gcc-plugin_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/gcc/12.3.1-40d504be6370b5a30e3947a6e575ca28/bin/../lib/gcc/x86_64-redhat-linux-gnu/12.3.1/plugin/include
gcc-plugin_EX_LIB := cc1plugin cp1plugin

ALL_TOOLS      += gdb

ALL_TOOLS      += gdbm
gdbm_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/gdbm/1.10-1f0ec10a142f21150eef9d32ba579779/include
gdbm_EX_LIB := gdbm
gdbm_EX_USE := root_cxxdefaults

ALL_TOOLS      += gdrcopy
gdrcopy_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/gdrcopy/2.4.4-173591af4569f51d3f267de11c6f8c19/include
gdrcopy_EX_LIB := gdrapi

ALL_TOOLS      += geant4
geant4_EX_USE := geant4core geant4vis

ALL_TOOLS      += geant4_interface
geant4_interface_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/geant4/11.2.2-52b9dc70f3ca8efebf82b291217bc6c2/include/Geant4 /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/geant4/11.2.2-52b9dc70f3ca8efebf82b291217bc6c2/include
geant4_interface_EX_USE := clhep vecgeom zlib expat xerces-c root_cxxdefaults
geant4_interface_EX_FLAGS_CPPDEFINES  := -DGNU_GCC -DG4V9
geant4_interface_EX_FLAGS_CXXFLAGS  := -ftls-model=global-dynamic -pthread

ALL_TOOLS      += geant4core
geant4core_EX_LIB := G4digits_hits G4error_propagation G4event G4geometry G4global G4graphics_reps G4intercoms G4interfaces G4materials G4parmodels G4particles G4geomtext G4mctruth G4gdml G4physicslists G4processes G4readout G4run G4tracking G4track G4analysis
geant4core_EX_USE := geant4_interface
geant4core_EX_FLAGS_CPPDEFINES  := -DGNU_GCC -DG4V9

ALL_TOOLS      += geant4data

ALL_TOOLS      += geant4static
geant4static_EX_LIB := geant4-static
geant4static_EX_USE := geant4_interface

ALL_TOOLS      += geant4vis
geant4vis_EX_LIB := G4FR G4modeling G4RayTracer G4Tree G4visHepRep G4vis_management G4VRML G4GMocren
geant4vis_EX_USE := geant4core

ALL_TOOLS      += giflib
giflib_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/giflib/5.2.1-63b47ba870c324f0f780aad18786582a/include
giflib_EX_LIB := gif
giflib_EX_USE := root_cxxdefaults

ALL_TOOLS      += git-lfs

ALL_TOOLS      += git

ALL_TOOLS      += glimpse

ALL_TOOLS      += gmake

ALL_TOOLS      += gnuplot

ALL_TOOLS      += google-benchmark-main
google-benchmark-main_EX_LIB := benchmark_main
google-benchmark-main_EX_USE := google-benchmark

ALL_TOOLS      += google-benchmark
google-benchmark_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/google-benchmark/1.7.x-329ba6ad4cdda03c215d0e63644a5752/include
google-benchmark_EX_LIB := benchmark
google-benchmark_EX_USE := sockets

ALL_TOOLS      += gosam

ALL_TOOLS      += gosamcontrib
gosamcontrib_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/gosamcontrib/2.0-20180708-24ee63d96e0de928b2dd0a3fbddfd69d/include

ALL_TOOLS      += gperf
gperf_EX_USE := gperf_profiler

ALL_TOOLS      += gperf_interface
gperf_interface_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/gperftools/2.11-fbc5201d6cd1b434ea6f7a6becab597d/include
gperf_interface_EX_USE := libunwind

ALL_TOOLS      += gperf_profiler
gperf_profiler_EX_LIB := profiler
gperf_profiler_EX_USE := gperf_interface

ALL_TOOLS      += gperf_tcmalloc_and_profiler
gperf_tcmalloc_and_profiler_EX_LIB := tcmalloc_and_profiler
gperf_tcmalloc_and_profiler_EX_USE := gperf_interface

ALL_TOOLS      += grpc
grpc_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/grpc/1.35.0-50be0bb6dd40c37c7098253da39e9cfe/include
grpc_EX_LIB := grpc grpc++ grpc++_reflection
grpc_EX_USE := protobuf openssl pcre abseil-cpp c-ares re2
grpc_EX_FLAGS_SYSTEM_INCLUDE  := 1

ALL_TOOLS      += gsl
gsl_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/gsl/2.6-f7574c606b0ce57ff601d3ca9534cd01/include
gsl_EX_LIB := gsl
gsl_EX_USE := openblas root_cxxdefaults

ALL_TOOLS      += hdf5
hdf5_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/hdf5/1.14.1-27bf63f2b1ecffe45a93f1817b549f46/include
hdf5_EX_LIB := hdf5 hdf5_hl
hdf5_EX_USE := openmpi

ALL_TOOLS      += heaptrack

ALL_TOOLS      += hector
hector_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/hector/1.3.4_patch1-d2fc5538362f8adb6603752040614198/include
hector_EX_LIB := Hector
hector_EX_USE := root_cxxdefaults

ALL_TOOLS      += hepmc
hepmc_EX_LIB := HepMCfio HepMC
hepmc_EX_USE := hepmc_headers

ALL_TOOLS      += hepmc3
hepmc3_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/hepmc3/3.2.7-f10dce5b16f0246f8cac8378933b9681/include
hepmc3_EX_LIB := HepMC3 HepMC3search

ALL_TOOLS      += hepmc_headers
hepmc_headers_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/hepmc/2.06.10-262d73524c32528e87adc31a98f68d52/include
hepmc_headers_EX_USE := root_cxxdefaults

ALL_TOOLS      += heppdt
heppdt_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/heppdt/3.04.01-0ef13ec7c94f9af4e098178f31f8e22b/include
heppdt_EX_LIB := HepPDT HepPID
heppdt_EX_USE := root_cxxdefaults

ALL_TOOLS      += herwig7
herwig7_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/herwig7/7.2.2-ed6d4951ea9f2cd9bf31ab3ffcb0286b/include
herwig7_EX_LIB := HerwigAPI
herwig7_EX_USE := root_cxxdefaults lhapdf thepeg madgraph5amcatnlo openloops

ALL_TOOLS      += highfive
highfive_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/highfive/2.3.1-95eb92e269739c3c50b550522847e3cb/include
highfive_EX_USE := boost hdf5

ALL_TOOLS      += histfactory
histfactory_EX_LIB := HistFactory
histfactory_EX_USE := roofitcore roofit roostats rootcore roothistmatrix rootgpad rootxml rootfoam

ALL_TOOLS      += hls
hls_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/hls/2025.05-4da036171b10090d7d21e15c49bb27a1/include
hls_EX_USE := root_cxxdefaults
hls_EX_FLAGS_SYSTEM_INCLUDE  := 1

ALL_TOOLS      += hls4mlemulatorextras
hls4mlemulatorextras_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/hls4mlEmulatorExtras/1.1.4-7f1f5ec35d8cc94e9bab71c7ff9456f1/include
hls4mlemulatorextras_EX_LIB := emulator_interface
hls4mlemulatorextras_EX_USE := sockets

ALL_TOOLS      += hwloc
hwloc_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/hwloc/2.12.0-4549567922b24470cbde03bce2601e1a/include/hwloc
hwloc_EX_LIB := hwloc

ALL_TOOLS      += hydjet
hydjet_EX_LIB := hydjet
hydjet_EX_USE := pyquen pythia6 lhapdf

ALL_TOOLS      += hydjet2
hydjet2_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/hydjet2/2.4.4-cdab34d0a1a13f1415b5eb795b9c5f81/include
hydjet2_EX_LIB := hydjet2
hydjet2_EX_USE := pyquen pythia6 lhapdf root
hydjet2_EX_FLAGS_SYSTEM_INCLUDE  := 1

ALL_TOOLS      += igprof

ALL_TOOLS      += intel-license

ALL_TOOLS      += isal
isal_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/isal/2.30.0-2fac74a6bb303092cba6f554ca947fe3/include
isal_EX_LIB := isal
isal_EX_USE := eigen

ALL_TOOLS      += ittnotify
ittnotify_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/ittnotify/16.06.18-f963cc841dbf061b8143306db7c66b39/include
ittnotify_EX_LIB := ittnotify

ALL_TOOLS      += iwyu-cxxcompiler
iwyu-cxxcompiler_EX_USE := llvm-cxxcompiler

ALL_TOOLS      += jemalloc-debug
jemalloc-debug_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/jemalloc-debug/5.3.0-4144d7f94ef06dc82cab21306f98c999/include
jemalloc-debug_EX_LIB := jemalloc-debug
jemalloc-debug_EX_USE := root_cxxdefaults

ALL_TOOLS      += jemalloc-prof
jemalloc-prof_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/jemalloc-prof/5.3.0-75ab9431f9b38624b64e8680404206c5/include
jemalloc-prof_EX_LIB := jemalloc-prof
jemalloc-prof_EX_USE := root_cxxdefaults

ALL_TOOLS      += jemalloc
jemalloc_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/jemalloc/5.3.0-0d50beec355425ed72b8a6798b9a125f/include
jemalloc_EX_LIB := jemalloc
jemalloc_EX_USE := root_cxxdefaults

ALL_TOOLS      += json
json_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/json/3.11.3-fe8b14080d05d6ff46ded7c91e3977bc/include

ALL_TOOLS      += ktjet
ktjet_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/ktjet/1.06-0c32371d0b63d85c811afb5ccda85c86/include
ktjet_EX_LIB := KtEvent
ktjet_EX_USE := root_cxxdefaults
ktjet_EX_FLAGS_CPPDEFINES  := -DKTDOUBLEPRECISION

ALL_TOOLS      += l1metml

ALL_TOOLS      += lcov

ALL_TOOLS      += lhapdf
lhapdf_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/lhapdf/6.4.0-e7c4b9323f96fa15c22775e405ec99ed/include
lhapdf_EX_LIB := LHAPDF
lhapdf_EX_USE := root_cxxdefaults

ALL_TOOLS      += libffi
libffi_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/libffi/3.4.2-9aa8487f9a3ce11ee7e4e6433e82c48d/include
libffi_EX_LIB := ffi

ALL_TOOLS      += libibumad
libibumad_EX_LIB := ibumad
libibumad_EX_USE := rdma-core

ALL_TOOLS      += libibverbs
libibverbs_EX_LIB := ibverbs
libibverbs_EX_USE := rdma-core

ALL_TOOLS      += libjpeg-turbo
libjpeg-turbo_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/libjpeg-turbo/2.0.2-3cab08429be43a78d2ecd1c6598ee750/include
libjpeg-turbo_EX_LIB := jpeg turbojpeg
libjpeg-turbo_EX_USE := root_cxxdefaults

ALL_TOOLS      += libpciaccess
libpciaccess_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/libpciaccess/0.16-7dd5044f5a0951e81ea792d5aac03fee/include
libpciaccess_EX_LIB := libpciaccess

ALL_TOOLS      += libpng
libpng_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/libpng/1.6.37-ac24a052f0764e050f1085e744b63e73/include
libpng_EX_LIB := png
libpng_EX_USE := root_cxxdefaults zlib

ALL_TOOLS      += librdmacm
librdmacm_EX_LIB := rdmacm
librdmacm_EX_USE := rdma-core libibverbs

ALL_TOOLS      += libtiff
libtiff_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/libtiff/4.0.10-d510c78a51ec326b33bb71bb87e5fbf2/include
libtiff_EX_LIB := tiff
libtiff_EX_USE := root_cxxdefaults libjpeg-turbo zlib

ALL_TOOLS      += libungif
libungif_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/libungif/4.1.4-2f91a77bad1564f8547f5d13089fd857/include
libungif_EX_LIB := ungif
libungif_EX_USE := root_cxxdefaults zlib

ALL_TOOLS      += libunwind
libunwind_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/libunwind/1.8.1-master-beabc0e9d66c563126dd61440aa2c705/include
libunwind_EX_LIB := unwind
libunwind_EX_USE := root_cxxdefaults

ALL_TOOLS      += libuuid
libuuid_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/libuuid/2.34-27ce4c3579b5b1de2808ea9c4cd8ed29/include
libuuid_EX_LIB := uuid
libuuid_EX_USE := root_cxxdefaults sockets

ALL_TOOLS      += libxml2
libxml2_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/libxml2/2.9.10-c415f3b7eaab8ebdde4f72b236d004a0/include/libxml2
libxml2_EX_LIB := xml2
libxml2_EX_USE := root_cxxdefaults

ALL_TOOLS      += libxslt
libxslt_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/libxslt/1.1.28-e05ac6df927e9e49132fa3223a096a2b/include/libxslt
libxslt_EX_LIB := xslt

ALL_TOOLS      += libzmq
libzmq_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/libzmq/4.3.5-5bf04ee-cb3803affc80ed9905772e8d99c56db6/include
libzmq_EX_LIB := zmq

ALL_TOOLS      += llvm-analyzer-ccompiler
llvm-analyzer-ccompiler_EX_USE := llvm-ccompiler

ALL_TOOLS      += llvm-analyzer-cxxcompiler
llvm-analyzer-cxxcompiler_EX_USE := llvm-cxxcompiler

ALL_TOOLS      += llvm-ccompiler
llvm-ccompiler_EX_USE := gcc-ccompiler
llvm-ccompiler_EX_FLAGS_CFLAGS  := --gcc-toolchain=/cvmfs/cms.cern.ch/el9_amd64_gcc12/external/gcc/12.3.1-40d504be6370b5a30e3947a6e575ca28

ALL_TOOLS      += llvm-cxxcompiler
llvm-cxxcompiler_EX_USE := gcc-cxxcompiler
llvm-cxxcompiler_EX_FLAGS_CXXFLAGS  := -Wno-c99-extensions -Wno-c++11-narrowing -D__STRICT_ANSI__ -Wno-unused-private-field -Wno-unknown-pragmas -Wno-unused-command-line-argument -Wno-unknown-warning-option -ftemplate-depth=512 -Wno-error=potentially-evaluated-expression -Wno-tautological-type-limit-compare -Wno-vla-cxx-extension -fsized-deallocation --gcc-toolchain=/cvmfs/cms.cern.ch/el9_amd64_gcc12/external/gcc/12.3.1-40d504be6370b5a30e3947a6e575ca28
llvm-cxxcompiler_EX_FLAGS_REM_CXXFLAGS  := -Wno-non-template-friend -Werror=format-contains-nul -Werror=maybe-uninitialized -Werror=unused-but-set-variable -Werror=return-local-addr -fipa-pta -frounding-math -mrecip -fno-crossjumping -fno-aggressive-loop-optimizations -funroll-all-loops
llvm-cxxcompiler_EX_FLAGS_REM_LTO_FLAGS  := -fipa-icf -flto-odr-type-merging -fno-fat-lto-objects
llvm-cxxcompiler_EX_FLAGS_REM_PGO_FLAGS  := -fprofile%

ALL_TOOLS      += llvm-f77compiler
llvm-f77compiler_EX_USE := gcc-f77compiler

ALL_TOOLS      += llvm
llvm_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/llvm/18.1.6-46165be3f70ec2619c579730b86daad1/include
llvm_EX_LIB := clang
llvm_EX_FLAGS_CXXFLAGS  := -D_DEBUG -D_GNU_SOURCE -D__STDC_CONSTANT_MACROS -D__STDC_FORMAT_MACROS -D__STDC_LIMIT_MACROS -O3 -fomit-frame-pointer -fPIC -Wno-enum-compare -Wno-strict-aliasing -fno-rtti
llvm_EX_FLAGS_LDFLAGS  := -Wl,-undefined -Wl,suppress

ALL_TOOLS      += log4cplus
log4cplus_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/log4cplus/2.0.7-3c0cfdbf50b70756a8ee62b68aa72168/include
log4cplus_EX_LIB := log4cplusS

ALL_TOOLS      += lwtnn
lwtnn_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/lwtnn/2.14.1-b6afb6e710d49cdf0a007020d89be257/include
lwtnn_EX_LIB := lwtnn
lwtnn_EX_USE := root_cxxdefaults eigen boost_system

ALL_TOOLS      += lwtnn_x86-64-v2

ALL_TOOLS      += lz4
lz4_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/lz4/1.9.2-e478fcd3e5e191d5bb4ade190474ad76/include
lz4_EX_LIB := lz4
lz4_EX_USE := root_cxxdefaults

ALL_TOOLS      += madgraph5amcatnlo
madgraph5amcatnlo_EX_USE := root_cxxdefaults gosamcontrib

ALL_TOOLS      += mctester
mctester_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/mctester/1.25.1-e3621381b0ab3bbf621059a7f6cba8cb/include
mctester_EX_LIB := HEPEvent HepMCEvent MCTester
mctester_EX_USE := root_cxxdefaults root hepmc

ALL_TOOLS      += md5
md5_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/md5/1.0.0-5b594b264e04ae51e893b1d69a797ec6/include
md5_EX_LIB := cms-md5

ALL_TOOLS      += meschach
meschach_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/meschach/1.2.pCMS1-79435924678a8cc522f783c34e3865d7/include
meschach_EX_LIB := meschach
meschach_EX_USE := root_cxxdefaults

ALL_TOOLS      += millepede
millepede_EX_USE := sockets pcre zlib

ALL_TOOLS      += mozsearch
mozsearch_EX_FLAGS_INDEX_FLAGS  := -Xclang -load -Xclang libclang-index-plugin.so -Xclang -add-plugin -Xclang mozsearch-index -Xclang -plugin-arg-mozsearch-index -Xclang src/ -Xclang -plugin-arg-mozsearch-index -Xclang mozsearch/ -Xclang -plugin-arg-mozsearch-index -Xclang tmp/el9_amd64_gcc12/src/

ALL_TOOLS      += no-array-bounds-flag
no-array-bounds-flag_EX_FLAGS_CXXFLAGS  := -Wno-error=array-bounds -Wno-array-bounds

ALL_TOOLS      += numactl
numactl_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/numactl/2.0.14-b52604abfe0049e6a7aca40a3d26c569/include
numactl_EX_LIB := numa

ALL_TOOLS      += numpy-c-api
numpy-c-api_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/py3-numpy/1.24.3-4b3f1d182846dd5b8cdd065bebf4e7f2/c-api/core/include
numpy-c-api_EX_LIB := npymath
numpy-c-api_EX_USE := root_cxxdefaults

ALL_TOOLS      += nvidia-drivers
nvidia-drivers_EX_LIBDIR := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/cuda/12.8.0-5a6d49e4693d62148340846b99d6a8e3/drivers
nvidia-drivers_EX_FLAGS_SKIP_TOOL_SYMLINKS  := 1

ALL_TOOLS      += nvperf
nvperf_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/cuda/12.8.0-5a6d49e4693d62148340846b99d6a8e3/include
nvperf_EX_LIB := nvperf_host nvperf_target

ALL_TOOLS      += ofast-flag
ofast-flag_EX_FLAGS_CXXFLAGS  := -Ofast -fno-reciprocal-math -mrecip=none
ofast-flag_EX_FLAGS_NO_RECURSIVE_EXPORT  := 1

ALL_TOOLS      += onnxruntime
onnxruntime_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/onnxruntime/1.20.1-6271b3bf78eab220472448f905c26f9c/include
onnxruntime_EX_LIB := onnxruntime
onnxruntime_EX_USE := protobuf cuda cudnn re2

ALL_TOOLS      += openblas
openblas_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/OpenBLAS/0.3.27-70a9dd2c9f309171934f13e3003b0540/include
openblas_EX_LIB := openblas

ALL_TOOLS      += openblas_x86-64-v2

ALL_TOOLS      += opencv
opencv_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/opencv/4.9.0-de47c6eb879e9d696e08706b5d44b828/include
opencv_EX_LIB := opencv_core
opencv_EX_USE := libpng libjpeg-turbo zlib eigen openblas

ALL_TOOLS      += opencv_x86-64-v2

ALL_TOOLS      += opengl
opengl_EX_LIB := GL GLU
opengl_EX_USE := x11

ALL_TOOLS      += openldap
openldap_EX_USE := db6

ALL_TOOLS      += openloops

ALL_TOOLS      += openmpi
openmpi_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/openmpi/4.1.6-8e5425474f92a0c10d9a24c521413a1c/include
openmpi_EX_LIB := mpi mpi_cxx

ALL_TOOLS      += openssl
openssl_EX_LIB := ssl crypto

ALL_TOOLS      += oracle
oracle_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/oracle/19.11.0.0.0dbru-0ef9ee763c1e7a90d8c4515a5af97f0b/include
oracle_EX_LIB := clntsh
oracle_EX_USE := root_cxxdefaults sockets

ALL_TOOLS      += oracleocci
oracleocci_EX_LIB := occi
oracleocci_EX_USE := oracle

ALL_TOOLS      += pacparser
pacparser_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/pacparser/1.4.2-d62b951e0455795e0d154beda504125a/include
pacparser_EX_LIB := pacparser
pacparser_EX_USE := root_cxxdefaults

ALL_TOOLS      += pcre
pcre_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/pcre/8.43-2d141998cfe5424b8f7aff48035cc2da/include
pcre_EX_LIB := pcre
pcre_EX_USE := root_cxxdefaults zlib bz2lib

ALL_TOOLS      += pcre2
pcre2_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/pcre2/10.36-cdcfcb112d100e048938c4777a0a1836/include
pcre2_EX_LIB := pcre2
pcre2_EX_USE := root_cxxdefaults zlib bz2lib

ALL_TOOLS      += photospp
photospp_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/photospp/3.64-07662bd7a63a16d3d0530624e45f242c/include
photospp_EX_LIB := Photospp PhotosppHepMC PhotosppHepMC3 PhotosppHEPEVT
photospp_EX_USE := hepmc hepmc3

ALL_TOOLS      += professor2
professor2_EX_USE := py3-numpy root yoda eigen

ALL_TOOLS      += protobuf
protobuf_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/protobuf/3.21.9-d5949ee2f313d8eb1bcc8de115b32a05/include
protobuf_EX_LIB := protobuf
protobuf_EX_USE := root_cxxdefaults

ALL_TOOLS      += py3-absl-py

ALL_TOOLS      += py3-annotated-types

ALL_TOOLS      += py3-anyio

ALL_TOOLS      += py3-appdirs

ALL_TOOLS      += py3-argon2-cffi-bindings

ALL_TOOLS      += py3-argon2-cffi

ALL_TOOLS      += py3-argparse

ALL_TOOLS      += py3-asn1crypto

ALL_TOOLS      += py3-astor

ALL_TOOLS      += py3-astroid

ALL_TOOLS      += py3-asttokens

ALL_TOOLS      += py3-astunparse

ALL_TOOLS      += py3-async-lru

ALL_TOOLS      += py3-atomicwrites

ALL_TOOLS      += py3-attrs

ALL_TOOLS      += py3-autopep8

ALL_TOOLS      += py3-avro

ALL_TOOLS      += py3-awkward-cpp

ALL_TOOLS      += py3-awkward-pandas

ALL_TOOLS      += py3-awkward

ALL_TOOLS      += py3-babel

ALL_TOOLS      += py3-backcall

ALL_TOOLS      += py3-backports-entry-points-selectable

ALL_TOOLS      += py3-backports-tarfile

ALL_TOOLS      += py3-beautifulsoup4

ALL_TOOLS      += py3-beniget

ALL_TOOLS      += py3-bleach

ALL_TOOLS      += py3-blosc2

ALL_TOOLS      += py3-boost-histogram

ALL_TOOLS      += py3-bottleneck

ALL_TOOLS      += py3-cachecontrol

ALL_TOOLS      += py3-cachetools

ALL_TOOLS      += py3-cachy

ALL_TOOLS      += py3-calver

ALL_TOOLS      += py3-certifi

ALL_TOOLS      += py3-cffi

ALL_TOOLS      += py3-chardet

ALL_TOOLS      += py3-charset-normalizer

ALL_TOOLS      += py3-cleo

ALL_TOOLS      += py3-click

ALL_TOOLS      += py3-clikit

ALL_TOOLS      += py3-cloudpickle

ALL_TOOLS      += py3-cms-tfaot

ALL_TOOLS      += py3-cmsml

ALL_TOOLS      += py3-colorama

ALL_TOOLS      += py3-comm

ALL_TOOLS      += py3-commonmark

ALL_TOOLS      += py3-contextlib2

ALL_TOOLS      += py3-contourpy

ALL_TOOLS      += py3-correctionlib

ALL_TOOLS      += py3-coverage

ALL_TOOLS      += py3-cppy

ALL_TOOLS      += py3-cramjam

ALL_TOOLS      += py3-crashtest

ALL_TOOLS      += py3-cryptography

ALL_TOOLS      += py3-cx-oracle

ALL_TOOLS      += py3-cycler

ALL_TOOLS      += py3-cython

ALL_TOOLS      += py3-dask-awkward

ALL_TOOLS      += py3-dask

ALL_TOOLS      += py3-debugpy

ALL_TOOLS      += py3-decorator

ALL_TOOLS      += py3-defusedxml

ALL_TOOLS      += py3-deprecated

ALL_TOOLS      += py3-deprecation

ALL_TOOLS      += py3-dill

ALL_TOOLS      += py3-distlib

ALL_TOOLS      += py3-distro

ALL_TOOLS      += py3-docopt

ALL_TOOLS      += py3-docutils

ALL_TOOLS      += py3-dulwich

ALL_TOOLS      += py3-dxr

ALL_TOOLS      += py3-editables

ALL_TOOLS      += py3-entrypoints

ALL_TOOLS      += py3-exceptiongroup

ALL_TOOLS      += py3-execnet

ALL_TOOLS      += py3-executing

ALL_TOOLS      += py3-fastjsonschema

ALL_TOOLS      += py3-filelock

ALL_TOOLS      += py3-fire

ALL_TOOLS      += py3-flake8

ALL_TOOLS      += py3-flatbuffers

ALL_TOOLS      += py3-flawfinder

ALL_TOOLS      += py3-flit-core

ALL_TOOLS      += py3-flit

ALL_TOOLS      += py3-fonttools

ALL_TOOLS      += py3-fsspec

ALL_TOOLS      += py3-funcsigs

ALL_TOOLS      += py3-future

ALL_TOOLS      += py3-gast

ALL_TOOLS      += py3-gitdb

ALL_TOOLS      += py3-gitpython

ALL_TOOLS      += py3-google-auth-oauthlib

ALL_TOOLS      += py3-google-auth

ALL_TOOLS      += py3-google-pasta

ALL_TOOLS      += py3-grpcio-tools

ALL_TOOLS      += py3-grpcio

ALL_TOOLS      += py3-h11

ALL_TOOLS      += py3-h5py

ALL_TOOLS      += py3-hatch-fancy-pypi-readme

ALL_TOOLS      += py3-hatch-vcs

ALL_TOOLS      += py3-hatchling

ALL_TOOLS      += py3-hepdata-lib

ALL_TOOLS      += py3-hepdata-validator

ALL_TOOLS      += py3-hist

ALL_TOOLS      += py3-histogrammar

ALL_TOOLS      += py3-histoprint

ALL_TOOLS      += py3-html5lib

ALL_TOOLS      += py3-httpcore

ALL_TOOLS      += py3-httpx

ALL_TOOLS      += py3-idna

ALL_TOOLS      += py3-iminuit

ALL_TOOLS      += py3-importlib-metadata

ALL_TOOLS      += py3-importlib-resources

ALL_TOOLS      += py3-iniconfig

ALL_TOOLS      += py3-ipaddress

ALL_TOOLS      += py3-ipykernel

ALL_TOOLS      += py3-ipython

ALL_TOOLS      += py3-ipython_genutils

ALL_TOOLS      += py3-ipywidgets

ALL_TOOLS      += py3-isort

ALL_TOOLS      += py3-jaraco-classes

ALL_TOOLS      += py3-jaraco-context

ALL_TOOLS      += py3-jaraco-functools

ALL_TOOLS      += py3-jax

ALL_TOOLS      += py3-jedi

ALL_TOOLS      += py3-jeepney

ALL_TOOLS      += py3-jinja2

ALL_TOOLS      += py3-joblib

ALL_TOOLS      += py3-json5

ALL_TOOLS      += py3-jsonpickle

ALL_TOOLS      += py3-jsonschema-specifications

ALL_TOOLS      += py3-jsonschema

ALL_TOOLS      += py3-jupyter-client

ALL_TOOLS      += py3-jupyter-console

ALL_TOOLS      += py3-jupyter-core

ALL_TOOLS      += py3-jupyter-events

ALL_TOOLS      += py3-jupyter-lsp

ALL_TOOLS      += py3-jupyter-packaging

ALL_TOOLS      += py3-jupyter-server-terminals

ALL_TOOLS      += py3-jupyter-server

ALL_TOOLS      += py3-jupyterlab-pygments

ALL_TOOLS      += py3-jupyterlab-server

ALL_TOOLS      += py3-jupyterlab-widgets

ALL_TOOLS      += py3-jupyterlab

ALL_TOOLS      += py3-keras-applications

ALL_TOOLS      += py3-keras-preprocessing

ALL_TOOLS      += py3-keras

ALL_TOOLS      += py3-keras2onnx

ALL_TOOLS      += py3-keyring

ALL_TOOLS      += py3-kiwisolver

ALL_TOOLS      += py3-law

ALL_TOOLS      += py3-lazy-object-proxy

ALL_TOOLS      += py3-lizard

ALL_TOOLS      += py3-locket

ALL_TOOLS      += py3-lockfile

ALL_TOOLS      += py3-luigi

ALL_TOOLS      += py3-lxml

ALL_TOOLS      += py3-lz4

ALL_TOOLS      += py3-mako

ALL_TOOLS      += py3-markdown-it-py

ALL_TOOLS      += py3-markdown

ALL_TOOLS      += py3-markupsafe

ALL_TOOLS      += py3-matplotlib-inline

ALL_TOOLS      += py3-matplotlib

ALL_TOOLS      += py3-mccabe

ALL_TOOLS      += py3-mdurl

ALL_TOOLS      += py3-meson-python

ALL_TOOLS      += py3-meson

ALL_TOOLS      += py3-mistune

ALL_TOOLS      += py3-ml_dtypes

ALL_TOOLS      += py3-mock

ALL_TOOLS      += py3-more-itertools

ALL_TOOLS      += py3-mplhep-data

ALL_TOOLS      += py3-mplhep

ALL_TOOLS      += py3-mpmath

ALL_TOOLS      += py3-msgpack

ALL_TOOLS      += py3-nbclient

ALL_TOOLS      += py3-nbconvert

ALL_TOOLS      += py3-nbformat

ALL_TOOLS      += py3-ndindex

ALL_TOOLS      += py3-nest-asyncio

ALL_TOOLS      += py3-networkx

ALL_TOOLS      += py3-notebook-shim

ALL_TOOLS      += py3-notebook

ALL_TOOLS      += py3-numexpr

ALL_TOOLS      += py3-numpy

ALL_TOOLS      += py3-nvidia-ml-py

ALL_TOOLS      += py3-oauthlib

ALL_TOOLS      += py3-onnx

ALL_TOOLS      += py3-onnxconverter-common

ALL_TOOLS      += py3-onnxmltools

ALL_TOOLS      += py3-opt-einsum

ALL_TOOLS      += py3-overrides

ALL_TOOLS      += py3-packaging

ALL_TOOLS      += py3-pandas

ALL_TOOLS      += py3-pandocfilters

ALL_TOOLS      += py3-parsimonious

ALL_TOOLS      += py3-parso

ALL_TOOLS      += py3-partd

ALL_TOOLS      += py3-pastel

ALL_TOOLS      += py3-pathlib2

ALL_TOOLS      += py3-pathspec

ALL_TOOLS      += py3-pbr

ALL_TOOLS      += py3-pexpect

ALL_TOOLS      += py3-pickleshare

ALL_TOOLS      += py3-pillow

ALL_TOOLS      += py3-pip

ALL_TOOLS      += py3-pkgconfig

ALL_TOOLS      += py3-pkginfo

ALL_TOOLS      += py3-plac

ALL_TOOLS      += py3-platformdirs

ALL_TOOLS      += py3-pluggy

ALL_TOOLS      += py3-ply

ALL_TOOLS      += py3-poetry-core

ALL_TOOLS      += py3-poetry-plugin-export

ALL_TOOLS      += py3-poetry

ALL_TOOLS      += py3-prettytable

ALL_TOOLS      += py3-prometheus-client

ALL_TOOLS      += py3-prompt_toolkit

ALL_TOOLS      += py3-protobuf

ALL_TOOLS      += py3-prwlock

ALL_TOOLS      += py3-psutil

ALL_TOOLS      += py3-ptyprocess

ALL_TOOLS      += py3-pure-eval

ALL_TOOLS      += py3-py-cpuinfo

ALL_TOOLS      += py3-pyasn1-modules

ALL_TOOLS      += py3-pyasn1

ALL_TOOLS      += py3-pybind11
py3-pybind11_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/py3-pybind11/2.13.6-f0652a29d5d13fd1a1400eac82293778/lib/python3.9/site-packages/pybind11/include

ALL_TOOLS      += py3-pycodestyle

ALL_TOOLS      += py3-pycparser

ALL_TOOLS      += py3-pycuda

ALL_TOOLS      += py3-pycurl

ALL_TOOLS      += py3-pydantic-core

ALL_TOOLS      += py3-pydantic

ALL_TOOLS      += py3-pydot

ALL_TOOLS      += py3-pyflakes

ALL_TOOLS      += py3-pygithub

ALL_TOOLS      += py3-pygments

ALL_TOOLS      += py3-pyjwt

ALL_TOOLS      += py3-pylev

ALL_TOOLS      += py3-pylint

ALL_TOOLS      += py3-pynacl

ALL_TOOLS      += py3-pyparsing

ALL_TOOLS      += py3-pyproject-metadata

ALL_TOOLS      += py3-pysocks

ALL_TOOLS      += py3-pysqlite3

ALL_TOOLS      += py3-pytest-cov

ALL_TOOLS      += py3-pytest-runner

ALL_TOOLS      += py3-pytest-xdist

ALL_TOOLS      += py3-pytest

ALL_TOOLS      += py3-python-daemon

ALL_TOOLS      += py3-python-dateutil

ALL_TOOLS      += py3-python-json-logger

ALL_TOOLS      += py3-python-ldap

ALL_TOOLS      += py3-python-rapidjson

ALL_TOOLS      += py3-pythran

ALL_TOOLS      += py3-pytoml

ALL_TOOLS      += py3-pytools

ALL_TOOLS      += py3-pytz

ALL_TOOLS      += py3-pyyaml

ALL_TOOLS      += py3-pyzmq

ALL_TOOLS      += py3-rapidfuzz

ALL_TOOLS      += py3-referencing

ALL_TOOLS      += py3-regex

ALL_TOOLS      += py3-repoze-lru

ALL_TOOLS      += py3-requests-oauthlib

ALL_TOOLS      += py3-requests-toolbelt

ALL_TOOLS      += py3-requests

ALL_TOOLS      += py3-rfc3339-validator

ALL_TOOLS      += py3-rfc3986-validator

ALL_TOOLS      += py3-rich

ALL_TOOLS      += py3-rpds-py

ALL_TOOLS      += py3-rsa

ALL_TOOLS      += py3-scandir

ALL_TOOLS      += py3-schema

ALL_TOOLS      += py3-scikit-build

ALL_TOOLS      += py3-scikit-learn

ALL_TOOLS      += py3-scinum

ALL_TOOLS      += py3-scipy

ALL_TOOLS      += py3-seaborn

ALL_TOOLS      += py3-secretstorage

ALL_TOOLS      += py3-semantic-version

ALL_TOOLS      += py3-send2trash

ALL_TOOLS      += py3-setuptools-rust

ALL_TOOLS      += py3-setuptools-scm

ALL_TOOLS      += py3-setuptools

ALL_TOOLS      += py3-shellingham

ALL_TOOLS      += py3-simplegeneric

ALL_TOOLS      += py3-singledispatch

ALL_TOOLS      += py3-six

ALL_TOOLS      += py3-skl2onnx

ALL_TOOLS      += py3-smmap

ALL_TOOLS      += py3-sniffio

ALL_TOOLS      += py3-soupsieve

ALL_TOOLS      += py3-sqlalchemy

ALL_TOOLS      += py3-stack-data

ALL_TOOLS      += py3-stevedore

ALL_TOOLS      += py3-subprocess32

ALL_TOOLS      += py3-sympy

ALL_TOOLS      += py3-tables

ALL_TOOLS      += py3-tabulate

ALL_TOOLS      += py3-tenacity

ALL_TOOLS      += py3-tensorboard-data-server

ALL_TOOLS      += py3-tensorboard-plugin-wit

ALL_TOOLS      += py3-tensorboard

ALL_TOOLS      += py3-tensorflow-estimator

ALL_TOOLS      += py3-tensorflow-io-gcs-filesystem

ALL_TOOLS      += py3-tensorflow

ALL_TOOLS      += py3-termcolor

ALL_TOOLS      += py3-terminado

ALL_TOOLS      += py3-testpath

ALL_TOOLS      += py3-threadpoolctl

ALL_TOOLS      += py3-tinycss2

ALL_TOOLS      += py3-toml

ALL_TOOLS      += py3-tomli-w

ALL_TOOLS      += py3-tomli

ALL_TOOLS      += py3-tomlkit

ALL_TOOLS      += py3-toolz

ALL_TOOLS      += py3-tornado

ALL_TOOLS      += py3-tqdm

ALL_TOOLS      += py3-traitlets

ALL_TOOLS      += py3-trove-classifiers

ALL_TOOLS      += py3-typed-ast

ALL_TOOLS      += py3-typing-extensions

ALL_TOOLS      += py3-tzdata

ALL_TOOLS      += py3-uhi

ALL_TOOLS      += py3-uncertainties

ALL_TOOLS      += py3-uproot

ALL_TOOLS      += py3-urllib3

ALL_TOOLS      += py3-vector

ALL_TOOLS      += py3-versioneer

ALL_TOOLS      += py3-virtualenv-clone

ALL_TOOLS      += py3-virtualenv

ALL_TOOLS      += py3-virtualenvwrapper

ALL_TOOLS      += py3-wcwidth

ALL_TOOLS      += py3-webencodings

ALL_TOOLS      += py3-websocket-client

ALL_TOOLS      += py3-werkzeug

ALL_TOOLS      += py3-wheel

ALL_TOOLS      += py3-widgetsnbextension

ALL_TOOLS      += py3-wrapt

ALL_TOOLS      += py3-xgboost

ALL_TOOLS      += py3-zipp

ALL_TOOLS      += pyclang

ALL_TOOLS      += pydata
pydata_EX_FLAGS_LDFLAGS  := $(PYDATA_BASE)/lib/pydata.o
pydata_EX_FLAGS_NO_RECURSIVE_EXPORT  := 1

ALL_TOOLS      += pyquen
pyquen_EX_LIB := pyquen
pyquen_EX_USE := pythia6 lhapdf

ALL_TOOLS      += pythia6
pythia6_EX_LIB := pythia6 pythia6_dummy
pythia6_EX_USE := lhapdf pythia6_headers f77compiler

ALL_TOOLS      += pythia6_headers
pythia6_headers_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/pythia6/426-c430ea6f2967f65248af15c71e6c653e/include
pythia6_headers_EX_USE := root_cxxdefaults

ALL_TOOLS      += pythia6_pdfdummy
pythia6_pdfdummy_EX_LIB := pythia6_pdfdummy
pythia6_pdfdummy_EX_FLAGS_NO_RECURSIVE_EXPORT  := 1

ALL_TOOLS      += pythia8
pythia8_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/pythia8/311-62f197bacb831a8defc23e576ff6b2ab/include
pythia8_EX_LIB := pythia8
pythia8_EX_USE := root_cxxdefaults hepmc3 hepmc lhapdf
pythia8_EX_FLAGS_SYSTEM_INCLUDE  := 1

ALL_TOOLS      += python-paths

ALL_TOOLS      += python3
python3_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/python3/3.9.14-2cc3edc74f38772096f1e8978a9716da/include/python3.9
python3_EX_LIB := python3.9
python3_EX_USE := sockets

ALL_TOOLS      += python_tools

ALL_TOOLS      += pytorch-cluster
pytorch-cluster_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/pytorch-cluster/1.6.3-b3262d6635641713afe0bb75eebf3ac7/include /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/pytorch-cluster/1.6.3-b3262d6635641713afe0bb75eebf3ac7/include/torchcluster/
pytorch-cluster_EX_LIB := torchcluster
pytorch-cluster_EX_USE := pytorch
pytorch-cluster_EX_FLAGS_FORCE_LINK  := 1

ALL_TOOLS      += pytorch-cuda
pytorch-cuda_EX_LIB := torch_cuda c10_cuda
pytorch-cuda_EX_USE := cuda torch-interface

ALL_TOOLS      += pytorch-custom-ops
pytorch-custom-ops_EX_USE := pytorch pytorch-scatter pytorch-cluster pytorch-sparse

ALL_TOOLS      += pytorch-scatter
pytorch-scatter_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/pytorch-scatter/2.1.2-78d4b7844a01439eaef057407e2300e7/include /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/pytorch-scatter/2.1.2-78d4b7844a01439eaef057407e2300e7/include/torchscatter/
pytorch-scatter_EX_LIB := torchscatter
pytorch-scatter_EX_USE := pytorch
pytorch-scatter_EX_FLAGS_FORCE_LINK  := 1

ALL_TOOLS      += pytorch-sparse
pytorch-sparse_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/pytorch-sparse/0.6.18-3d45bcd3c448790e73701a0978b39bb5/include /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/pytorch-sparse/0.6.18-3d45bcd3c448790e73701a0978b39bb5/include/torchsparse/
pytorch-sparse_EX_LIB := torchsparse
pytorch-sparse_EX_USE := pytorch
pytorch-sparse_EX_FLAGS_FORCE_LINK  := 1

ALL_TOOLS      += pytorch
pytorch_EX_LIB := torch torch_cpu c10
pytorch_EX_USE := torch-interface
pytorch_EX_FLAGS_FORCE_LINK  := 1

ALL_TOOLS      += pytorch_x86-64-v2

ALL_TOOLS      += qd
qd_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/qd/2.3.13-869155c589873939757066b8f1c8a798/include
qd_EX_LIB := qdmod qd

ALL_TOOLS      += qd_f_main
qd_f_main_EX_LIB := qd_f_main
qd_f_main_EX_USE := qd

ALL_TOOLS      += rdma-core
rdma-core_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/rdma-core/50.0-7f830a17690a1bbee43e16785640eae7/include

ALL_TOOLS      += re2
re2_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/re2/2021-06-01-9effece1d52fe4315cd5231654cb2160/include
re2_EX_LIB := re2

ALL_TOOLS      += rivet
rivet_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/rivet/4.0.2-10fd8ac8444ecfccd5f8a5ec84857591/include
rivet_EX_LIB := Rivet
rivet_EX_USE := hepmc fastjet fastjet-contrib gsl yoda hdf5 highfive onnxruntime

ALL_TOOLS      += rivet_x86-64-v2

ALL_TOOLS      += rocm-rccl
rocm-rccl_EX_LIB := rccl
rocm-rccl_EX_USE := rocm

ALL_TOOLS      += rocm-rocrand
rocm-rocrand_EX_LIB := hiprand rocrand
rocm-rocrand_EX_USE := rocm

ALL_TOOLS      += rocm
rocm_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/rocm/6.3.2-dd4ace0770f12ddb6078527b081d5a79/include
rocm_EX_LIB := amdhip64 hsa-runtime64 rocm_smi64
rocm_EX_USE := fmt
rocm_EX_FLAGS_CPPDEFINES  := -D__HIP_PLATFORM_HCC__ -D__HIP_PLATFORM_AMD__
rocm_EX_FLAGS_REM_ROCM_HOST_CXXFLAGS  := -march=%
rocm_EX_FLAGS_ROCM_FLAGS  := --offload-arch=gfx908:sramecc+ --offload-arch=gfx90a:sramecc+ --offload-arch=gfx942:sramecc+ --offload-arch=gfx1030 --offload-arch=gfx1100 --offload-arch=gfx1102 -fgpu-rdc --target=x86_64-redhat-linux-gnu --gcc-toolchain=$(COMPILER_PATH)
rocm_EX_FLAGS_ROCM_HOST_CXXFLAGS  := -march=x86-64-v2
rocm_EX_FLAGS_SYSTEM_INCLUDE  := 1

ALL_TOOLS      += roofit
roofit_EX_LIB := RooFit
roofit_EX_USE := roofitcore rootcore rootmath roothistmatrix

ALL_TOOLS      += roofitcore
roofitcore_EX_LIB := RooFitCore
roofitcore_EX_USE := rootcore roothistmatrix rootgpad rootminuit root_cxxdefaults

ALL_TOOLS      += roostats
roostats_EX_LIB := RooStats
roostats_EX_USE := roofitcore roofit rootcore roothistmatrix rootgpad

ALL_TOOLS      += root
root_EX_USE := rootphysics
root_EX_FLAGS_CXXMODULES  := 0
root_EX_FLAGS_GENREFLEX_FAILES_ON_WARNS  := -failOnWarnings

ALL_TOOLS      += root_cxxdefaults

ALL_TOOLS      += root_interface
root_interface_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/lcg/root/6.32.13-3ea6c37f14e3f39c0c3ce338c09aec10/include
root_interface_EX_USE := root_cxxdefaults
root_interface_EX_FLAGS_SYSTEM_INCLUDE  := 1

ALL_TOOLS      += rootcling
rootcling_EX_LIB := Core
rootcling_EX_USE := root_interface sockets pcre zlib xz
TOOLS_OVERRIDABLE_FLAGS  +=ROOTCLING_ARGS

ALL_TOOLS      += rootcore
rootcore_EX_LIB := Tree Net
rootcore_EX_USE := rootmathcore rootthread

ALL_TOOLS      += rootdataframe
rootdataframe_EX_LIB := ROOTDataFrame
rootdataframe_EX_USE := rootcore rootgraphics roothistmatrix rootrio rootvecops

ALL_TOOLS      += rooteg
rooteg_EX_LIB := EG
rooteg_EX_USE := rootgraphics

ALL_TOOLS      += rooteve
rooteve_EX_LIB := Eve
rooteve_EX_USE := rootgeompainter rootrgl rootged

ALL_TOOLS      += rootfoam
rootfoam_EX_LIB := Foam
rootfoam_EX_USE := roothistmatrix

ALL_TOOLS      += rootged
rootged_EX_LIB := Ged
rootged_EX_USE := rootgui

ALL_TOOLS      += rootgeom
rootgeom_EX_LIB := Geom
rootgeom_EX_USE := rootrio rootmathcore

ALL_TOOLS      += rootgeompainter
rootgeompainter_EX_LIB := GeomPainter
rootgeompainter_EX_USE := rootgeom rootgraphics

ALL_TOOLS      += rootglew
rootglew_EX_LIB := GLEW

ALL_TOOLS      += rootgpad
rootgpad_EX_LIB := Gpad Graf
rootgpad_EX_USE := roothistmatrix

ALL_TOOLS      += rootgraphics
rootgraphics_EX_LIB := TreePlayer Graf3d Postscript
rootgraphics_EX_USE := rootgpad

ALL_TOOLS      += rootgui
rootgui_EX_LIB := Gui
rootgui_EX_USE := rootgpad

ALL_TOOLS      += rootguihtml
rootguihtml_EX_LIB := GuiHtml
rootguihtml_EX_USE := rootgui rootinteractive

ALL_TOOLS      += roothistmatrix
roothistmatrix_EX_LIB := Hist Matrix
roothistmatrix_EX_USE := rootcore

ALL_TOOLS      += roothistpainter
roothistpainter_EX_LIB := HistPainter
roothistpainter_EX_USE := roothistmatrix rootgpad rootimt

ALL_TOOLS      += roothtml
roothtml_EX_LIB := Html
roothtml_EX_USE := rootgpad

ALL_TOOLS      += rootimt
rootimt_EX_LIB := Imt
rootimt_EX_USE := rootthread tbb

ALL_TOOLS      += rootinteractive
rootinteractive_EX_LIB := Gui
rootinteractive_EX_USE := libjpeg-turbo libpng rootgpad rootrint

ALL_TOOLS      += rootmath
rootmath_EX_LIB := GenVector MathMore
rootmath_EX_USE := rootcore gsl

ALL_TOOLS      += rootmathcore
rootmathcore_EX_LIB := MathCore
rootmathcore_EX_USE := rootcling

ALL_TOOLS      += rootminuit
rootminuit_EX_LIB := Minuit
rootminuit_EX_USE := rootgpad

ALL_TOOLS      += rootminuit2
rootminuit2_EX_LIB := Minuit2
rootminuit2_EX_USE := rootgpad

ALL_TOOLS      += rootmlp
rootmlp_EX_LIB := MLP
rootmlp_EX_USE := rootgraphics

ALL_TOOLS      += rootntuple
rootntuple_EX_LIB := ROOTNTuple
rootntuple_EX_USE := rootvecops rootthread

ALL_TOOLS      += rootphysics
rootphysics_EX_LIB := Physics
rootphysics_EX_USE := roothistmatrix

ALL_TOOLS      += rootpy
rootpy_EX_USE := rootgraphics

ALL_TOOLS      += rootpymva
rootpymva_EX_LIB := PyMVA
rootpymva_EX_USE := roottmva numpy-c-api

ALL_TOOLS      += rootrflx
rootrflx_EX_USE := root_interface rootcling
rootrflx_EX_FLAGS_GENREFLEX_CPPFLAGS  := -DCMS_DICT_IMPL -D_REENTRANT -DGNUSOURCE -D__STRICT_ANSI__
rootrflx_EX_FLAGS_GENREFLEX_GCCXMLOPT  := -m64
TOOLS_OVERRIDABLE_FLAGS  +=GENREFLEX_CPPFLAGS

ALL_TOOLS      += rootrgl
rootrgl_EX_LIB := RGL
rootrgl_EX_USE := rootglew rootgui rootinteractive rootgraphics

ALL_TOOLS      += rootrint
rootrint_EX_LIB := Rint
rootrint_EX_USE := rootcling

ALL_TOOLS      += rootrio
rootrio_EX_LIB := RIO
rootrio_EX_USE := rootcling

ALL_TOOLS      += rootsmatrix
rootsmatrix_EX_LIB := Smatrix
rootsmatrix_EX_USE := rootcling

ALL_TOOLS      += rootspectrum
rootspectrum_EX_LIB := Spectrum
rootspectrum_EX_USE := roothistmatrix

ALL_TOOLS      += rootthread
rootthread_EX_LIB := Thread
rootthread_EX_USE := rootrio

ALL_TOOLS      += roottmva
roottmva_EX_LIB := TMVA
roottmva_EX_USE := rootmlp rootminuit

ALL_TOOLS      += rootvecops
rootvecops_EX_LIB := ROOTVecOps
rootvecops_EX_USE := rootcore

ALL_TOOLS      += rootx11
rootx11_EX_LIB := GX11
rootx11_EX_USE := rootcling

ALL_TOOLS      += rootxml
rootxml_EX_LIB := XMLParser
rootxml_EX_USE := rootcore libxml2

ALL_TOOLS      += rootxmlio
rootxmlio_EX_LIB := XMLIO
rootxmlio_EX_USE := rootrio

ALL_TOOLS      += ruff

ALL_TOOLS      += sanitizer-flags-asan

ALL_TOOLS      += sanitizer-flags-ubsan

ALL_TOOLS      += self
self_EX_INCLUDE := /eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/stats_study/notebook_fitting/CMSSW_15_0_7/src /eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/stats_study/notebook_fitting/CMSSW_15_0_7/include/el9_amd64_gcc12/src /eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/stats_study/notebook_fitting/CMSSW_15_0_7/include/LCG /cvmfs/cms.cern.ch/el9_amd64_gcc12/cms/cmssw/CMSSW_15_0_7/src
self_EX_LIBDIR := /eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/stats_study/notebook_fitting/CMSSW_15_0_7/biglib/el9_amd64_gcc12 /eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/stats_study/notebook_fitting/CMSSW_15_0_7/lib/el9_amd64_gcc12 /eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/stats_study/notebook_fitting/CMSSW_15_0_7/external/el9_amd64_gcc12/lib /cvmfs/cms.cern.ch/el9_amd64_gcc12/cms/cmssw/CMSSW_15_0_7/biglib/el9_amd64_gcc12 /cvmfs/cms.cern.ch/el9_amd64_gcc12/cms/cmssw/CMSSW_15_0_7/lib/el9_amd64_gcc12 /cvmfs/cms.cern.ch/el9_amd64_gcc12/cms/cmssw/CMSSW_15_0_7/external/el9_amd64_gcc12/lib
self_EX_FLAGS_ALPAKA_BACKENDS  := cuda rocm serial
self_EX_FLAGS_CHECK_PRIVATE_HEADERS  := 1
self_EX_FLAGS_CODE_CHECK_ALPAKA_BACKEND  := serial
self_EX_FLAGS_DEFAULT_COMPILER  := gcc
self_EX_FLAGS_ENABLE_LTO  := 1
self_EX_FLAGS_ENABLE_PGO  := 0
self_EX_FLAGS_EXTERNAL_SYMLINK  := PATH LIBDIR CMSSW_SEARCH_PATH
self_EX_FLAGS_LLVM_ANALYZER  := llvm-analyzer
self_EX_FLAGS_NO_EXTERNAL_RUNTIME  := LD_LIBRARY_PATH PATH CMSSW_SEARCH_PATH
TOOLS_OVERRIDABLE_FLAGS  +=CPPDEFINES CXXFLAGS FFLAGS CFLAGS CPPFLAGS LDFLAGS CUDA_FLAGS CUDA_LDFLAGS LTO_FLAGS PGO_FLAGS ROCM_FLAGS ROCM_LDFLAGS
self_EX_FLAGS_SCRAM_TARGETS  := x86-64-v2
self_EX_FLAGS_SKIP_TOOLS_SYMLINK  := cxxcompiler ccompiler f77compiler gcc-cxxcompiler gcc-ccompiler gcc-f77compiler llvm-cxxcompiler llvm-ccompiler llvm-f77compiler llvm-analyzer-cxxcompiler llvm-analyzer-ccompiler icc-cxxcompiler icc-ccompiler icc-f77compiler x11 dpm
self_EX_FLAGS_SYMLINK_DEPTH_CMSSW_SEARCH_PATH  := 2
self_ORDER := 20000
IS_PATCH:=

ALL_TOOLS      += sherpa
sherpa_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/sherpa/2.2.15-54baac332792323ee60637a5bae8c9e0/include/SHERPA-MC
sherpa_EX_LIB := SherpaMain ToolsMath ToolsOrg
sherpa_EX_USE := root_cxxdefaults hepmc lhapdf qd blackhat fastjet sqlite openmpi openloops

ALL_TOOLS      += sigcpp
sigcpp_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/sigcpp/3.2.0-822d85000b677f1f6fbe907af08d7c8c/include/sigc++-3.0
sigcpp_EX_LIB := sigc-3.0
sigcpp_EX_USE := root_cxxdefaults

ALL_TOOLS      += sloccount

ALL_TOOLS      += sockets
sockets_EX_LIB := crypt dl rt

ALL_TOOLS      += sqlite
sqlite_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/sqlite/3.36.0-6a61dda6b4338fb9b6c26060efd5fd9a/include
sqlite_EX_LIB := sqlite3
sqlite_EX_USE := root_cxxdefaults

ALL_TOOLS      += starlight
starlight_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/starlight/r193-4299dc1b161e57f922e485fd167df6f2/include
starlight_EX_LIB := Starlib
starlight_EX_USE := root_cxxdefaults clhep

ALL_TOOLS      += stdcxx-fs
stdcxx-fs_EX_LIB := stdc++fs

ALL_TOOLS      += tauolapp
tauolapp_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/tauolapp/1.1.8-5ab06e9798ab285a134976a78de0cc19/include
tauolapp_EX_LIB := TauolaCxxInterface TauolaFortran TauolaTauSpinner TauolaHepMC TauolaHEPEVT
tauolapp_EX_USE := root_cxxdefaults hepmc f77compiler pythia8 lhapdf

ALL_TOOLS      += tbb
tbb_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/tbb/v2021.9.0-923065ff62d6d3ff52c3b52f6657aed2/include
tbb_EX_LIB := tbb
tbb_EX_USE := root_cxxdefaults
tbb_EX_FLAGS_CPPDEFINES  := -DTBB_USE_GLIBCXX_VERSION=120301 -DTBB_SUPPRESS_DEPRECATED_MESSAGES -DTBB_PREVIEW_RESUMABLE_TASKS=1 -DTBB_PREVIEW_TASK_GROUP_EXTENSIONS=1
tbb_EX_FLAGS_SYSTEM_INCLUDE  := 1

ALL_TOOLS      += tbbbind
tbbbind_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/tbb/v2021.9.0-923065ff62d6d3ff52c3b52f6657aed2/include
tbbbind_EX_LIB := tbbbind_2_0
tbbbind_EX_USE := tbb
tbbbind_EX_FLAGS_SYSTEM_INCLUDE  := 1

ALL_TOOLS      += tcmalloc
tcmalloc_EX_LIB := tcmalloc

ALL_TOOLS      += tcmalloc_minimal
tcmalloc_minimal_EX_LIB := tcmalloc_minimal

ALL_TOOLS      += tensorflow-c
tensorflow-c_EX_LIB := tensorflow
tensorflow-c_EX_USE := tensorflow-framework eigen libpng sqlite

ALL_TOOLS      += tensorflow-cc
tensorflow-cc_EX_LIB := tensorflow_cc
tensorflow-cc_EX_USE := tensorflow-framework eigen libpng sqlite

ALL_TOOLS      += tensorflow-executable_run_options
tensorflow-executable_run_options_EX_LIB := executable_run_options
tensorflow-executable_run_options_EX_USE := tensorflow

ALL_TOOLS      += tensorflow-framework
tensorflow-framework_EX_LIB := tensorflow_framework
tensorflow-framework_EX_USE := tensorflow giflib zlib libjpeg-turbo protobuf

ALL_TOOLS      += tensorflow-includes
tensorflow-includes_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/py3-tensorflow/2.12.0-c7c9c2a4eefe016b534fe162ae0a297f/lib/python3.9/site-packages/tensorflow/include

ALL_TOOLS      += tensorflow-runtime
tensorflow-runtime_EX_LIB := cpu_function_runtime
tensorflow-runtime_EX_USE := tensorflow

ALL_TOOLS      += tensorflow-tf2xla
tensorflow-tf2xla_EX_LIB := tf2xla
tensorflow-tf2xla_EX_USE := tensorflow

ALL_TOOLS      += tensorflow-xla-runtime
tensorflow-xla-runtime_EX_LIB := tf_xla_runtime
tensorflow-xla-runtime_EX_USE := eigen tensorflow-includes

ALL_TOOLS      += tensorflow-xla_compiled_cpu_function
tensorflow-xla_compiled_cpu_function_EX_LIB := xla_compiled_cpu_function
tensorflow-xla_compiled_cpu_function_EX_USE := tensorflow

ALL_TOOLS      += tensorflow
tensorflow_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/tensorflow/2.12.0-ce8818179b409c7625f54fe10b43fd64/include
tensorflow_EX_FLAGS_SYSTEM_INCLUDE  := 1

ALL_TOOLS      += tensorflow_x86-64-v2

ALL_TOOLS      += tfaot-model-test-multi
tfaot-model-test-multi_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/tfaot-model-test-multi/1.0.1-854da5ec5f7a09213186c3ee7377dba0/include
tfaot-model-test-multi_EX_USE := tensorflow-xla-runtime
tfaot-model-test-multi_EX_FLAGS_LDFLAGS  := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/tfaot-model-test-multi/1.0.1-854da5ec5f7a09213186c3ee7377dba0/lib/test_multi_bs1.o /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/tfaot-model-test-multi/1.0.1-854da5ec5f7a09213186c3ee7377dba0/lib/test_multi_bs2.o /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/tfaot-model-test-multi/1.0.1-854da5ec5f7a09213186c3ee7377dba0/lib/test_multi_bs4.o

ALL_TOOLS      += tfaot-model-test-simple
tfaot-model-test-simple_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/tfaot-model-test-simple/1.0.1-27ab7a3d1c5f5ca5ca6ece8080acc5cb/include
tfaot-model-test-simple_EX_USE := tensorflow-xla-runtime
tfaot-model-test-simple_EX_FLAGS_LDFLAGS  := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/tfaot-model-test-simple/1.0.1-27ab7a3d1c5f5ca5ca6ece8080acc5cb/lib/test_simple_bs1.o /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/tfaot-model-test-simple/1.0.1-27ab7a3d1c5f5ca5ca6ece8080acc5cb/lib/test_simple_bs2.o /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/tfaot-model-test-simple/1.0.1-27ab7a3d1c5f5ca5ca6ece8080acc5cb/lib/test_simple_bs4.o

ALL_TOOLS      += thepeg
thepeg_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/thepeg/2.2.2-2d68a4ff51961664ebbdae906fc34c82/include
thepeg_EX_LIB := ThePEG LesHouches
thepeg_EX_USE := root_cxxdefaults lhapdf gsl

ALL_TOOLS      += tinyxml2
tinyxml2_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/tinyxml2/6.2.0-f99ae2781d074227d47e8a3e7c8ec87e/include
tinyxml2_EX_LIB := tinyxml2

ALL_TOOLS      += tkonlinesw
tkonlinesw_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/tkonlinesw/4.2.0-1_gcc7-94d84a23305e2f0c66475ec9e64dda5f/include
tkonlinesw_EX_LIB := ICUtils Fed9UUtils
tkonlinesw_EX_USE := root_cxxdefaults xerces-c
tkonlinesw_EX_FLAGS_CXXFLAGS  := -DCMS_TK_64BITS

ALL_TOOLS      += tkonlineswdb
tkonlineswdb_EX_LIB := DeviceDescriptions Fed9UDeviceFactory
tkonlineswdb_EX_USE := tkonlinesw oracle oracleocci

ALL_TOOLS      += toollip

ALL_TOOLS      += torch-interface
torch-interface_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/pytorch/2.4.0-a39ed39a9c0b03843cd3c8eafad089bd/include /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/pytorch/2.4.0-a39ed39a9c0b03843cd3c8eafad089bd/include/torch/csrc/api/include
torch-interface_EX_USE := protobuf zlib

ALL_TOOLS      += triton-inference-client
triton-inference-client_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/triton-inference-client/2.25.0-1962fddc1ae79a2aa1cc3a14471f1925/include
triton-inference-client_EX_LIB := grpcclient tritoncommonmodelconfig
triton-inference-client_EX_USE := protobuf grpc cuda re2

ALL_TOOLS      += ucx
ucx_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/ucx/1.17.0-478182f7b088173854842d2e9aa63e57/include
ucx_EX_LIB := ucp uct ucs ucm

ALL_TOOLS      += utm
utm_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/utm/utm_0.13.0-7d8758dac157043a741ed83ec5719cff/include
utm_EX_LIB := tmeventsetup tmtable tmxsd tmgrammar tmutil
utm_EX_USE := root_cxxdefaults

ALL_TOOLS      += valgrind
valgrind_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/valgrind/3.24.0-cc012d7fe78884d4e0706577d85bee44/include
valgrind_EX_USE := root_cxxdefaults

ALL_TOOLS      += vdt
vdt_EX_LIB := vdt
vdt_EX_USE := vdt_headers

ALL_TOOLS      += vdt_headers
vdt_headers_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/cms/vdt/0.4.3-4870967f2eba63db6db5f9d739812ca1/include
vdt_headers_EX_USE := root_cxxdefaults

ALL_TOOLS      += vecgeom
vecgeom_EX_LIB := vecgeom
vecgeom_EX_USE := vecgeom_interface

ALL_TOOLS      += vecgeom_interface
vecgeom_interface_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/vecgeom/v1.2.7-6ef41c1a0471ffb9768e0b73b7641584/include /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/vecgeom/v1.2.7-6ef41c1a0471ffb9768e0b73b7641584/include/VecGeom
vecgeom_interface_EX_USE := root_cxxdefaults

ALL_TOOLS      += x11
x11_EX_USE := sockets

ALL_TOOLS      += xerces-c
xerces-c_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/xerces-c/3.1.3-c7b88eaa36d0408120f3c29826a04bf6/include
xerces-c_EX_LIB := xerces-c
xerces-c_EX_USE := root_cxxdefaults

ALL_TOOLS      += xgboost
xgboost_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/xgboost/1.7.5-a05d32b24fba11208da3df9807f8bb22/include
xgboost_EX_LIB := xgboost

ALL_TOOLS      += xpmem
xpmem_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/xpmem/v2.6.3-20220308-e317a33b47b8cbde38eda98c6a7ec259/include
xpmem_EX_LIB := xpmem

ALL_TOOLS      += xrdcl-record

ALL_TOOLS      += xrootd
xrootd_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/xrootd/5.7.2-ea80ee0ca8d46f1e87201dd16c9b691f/include/xrootd /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/xrootd/5.7.2-ea80ee0ca8d46f1e87201dd16c9b691f/include/xrootd/private
xrootd_EX_LIB := XrdUtils XrdCl
xrootd_EX_USE := root_cxxdefaults isal

ALL_TOOLS      += xtensor
xtensor_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/xtensor/0.24.1-52eec7873c5a54d268dc6f845af30e3a/include
xtensor_EX_USE := xtl

ALL_TOOLS      += xtl
xtl_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/xtl/0.7.4-a631280c43b3f845b80482d513652b18/include

ALL_TOOLS      += xz
xz_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/xz/5.2.5-87b9f5597eaeb8b5e9cedb5d183d5089/include
xz_EX_LIB := lzma
xz_EX_USE := root_cxxdefaults

ALL_TOOLS      += yaml-cpp
yaml-cpp_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/yaml-cpp/0.8.0-daa831833cbf55b73029800cc340c2bb/include
yaml-cpp_EX_LIB := yaml-cpp

ALL_TOOLS      += yoda
yoda_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/yoda/2.0.2-14c4599cca5ddebefd1918511ed783ea/include
yoda_EX_LIB := YODA
yoda_EX_USE := root_cxxdefaults

ALL_TOOLS      += zlib
zlib_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/zlib/1.2.13-d217cdbdd8d586e845e05946de2796be/include
zlib_EX_LIB := z
zlib_EX_USE := root_cxxdefaults

ALL_TOOLS      += zstd
zstd_EX_INCLUDE := /cvmfs/cms.cern.ch/el9_amd64_gcc12/external/zstd/1.5.2-c5e6a53d5921f82c7542f1a4c5fbcc3d/include
zstd_EX_LIB := zstd
zstd_EX_USE := root_cxxdefaults

