ALL_SUBSYSTEMS+=HiggsAnalysis
subdirs_src_HiggsAnalysis = src_HiggsAnalysis_CombinedLimit
subdirs_src += src_HiggsAnalysis
ALL_PACKAGES += HiggsAnalysis/CombinedLimit
subdirs_src_HiggsAnalysis_CombinedLimit := src_HiggsAnalysis_CombinedLimit_bin src_HiggsAnalysis_CombinedLimit_python src_HiggsAnalysis_CombinedLimit_scripts src_HiggsAnalysis_CombinedLimit_src src_HiggsAnalysis_CombinedLimit_test
ifeq ($(strip $(PerfTest)),)
PerfTest := self/src/HiggsAnalysis/CombinedLimit/bin
PerfTest_files := $(patsubst src/HiggsAnalysis/CombinedLimit/bin/%,%,$(foreach file,PerfTest.cpp,$(eval xfile:=$(wildcard src/HiggsAnalysis/CombinedLimit/bin/$(file)))$(if $(xfile),$(xfile),$(warning No such file exists: src/HiggsAnalysis/CombinedLimit/bin/$(file). Please fix src/HiggsAnalysis/CombinedLimit/bin/BuildFile.))))
PerfTest_BuildFile    := $(WORKINGDIR)/cache/bf/src/HiggsAnalysis/CombinedLimit/bin/BuildFile
PerfTest_LOC_USE := self   HiggsAnalysis/CombinedLimit boost_program_options
PerfTest_PACKAGE := self/src/HiggsAnalysis/CombinedLimit/bin
ALL_PRODS += PerfTest
PerfTest_INIT_FUNC        += $$(eval $$(call Binary,PerfTest,src/HiggsAnalysis/CombinedLimit/bin,src_HiggsAnalysis_CombinedLimit_bin,$(SCRAMSTORENAME_BIN),,$(SCRAMSTORENAME_BIN),bin,$(SCRAMSTORENAME_LOGS)))
PerfTest_CLASS := BINARY
else
$(eval $(call MultipleWarningMsg,PerfTest,src/HiggsAnalysis/CombinedLimit/bin))
endif
ifeq ($(strip $(combine)),)
combine := self/src/HiggsAnalysis/CombinedLimit/bin
combine_files := $(patsubst src/HiggsAnalysis/CombinedLimit/bin/%,%,$(foreach file,combine.cpp,$(eval xfile:=$(wildcard src/HiggsAnalysis/CombinedLimit/bin/$(file)))$(if $(xfile),$(xfile),$(warning No such file exists: src/HiggsAnalysis/CombinedLimit/bin/$(file). Please fix src/HiggsAnalysis/CombinedLimit/bin/BuildFile.))))
combine_BuildFile    := $(WORKINGDIR)/cache/bf/src/HiggsAnalysis/CombinedLimit/bin/BuildFile
combine_LOC_USE := self   HiggsAnalysis/CombinedLimit boost_program_options
combine_PACKAGE := self/src/HiggsAnalysis/CombinedLimit/bin
ALL_PRODS += combine
combine_INIT_FUNC        += $$(eval $$(call Binary,combine,src/HiggsAnalysis/CombinedLimit/bin,src_HiggsAnalysis_CombinedLimit_bin,$(SCRAMSTORENAME_BIN),,$(SCRAMSTORENAME_BIN),bin,$(SCRAMSTORENAME_LOGS)))
combine_CLASS := BINARY
else
$(eval $(call MultipleWarningMsg,combine,src/HiggsAnalysis/CombinedLimit/bin))
endif
ALL_COMMONRULES += src_HiggsAnalysis_CombinedLimit_bin
src_HiggsAnalysis_CombinedLimit_bin_parent := HiggsAnalysis/CombinedLimit
src_HiggsAnalysis_CombinedLimit_bin_INIT_FUNC += $$(eval $$(call CommonProductRules,src_HiggsAnalysis_CombinedLimit_bin,src/HiggsAnalysis/CombinedLimit/bin,BINARY))
ifeq ($(strip $(PyHiggsAnalysisCombinedLimit)),)
PyHiggsAnalysisCombinedLimit := self/src/HiggsAnalysis/CombinedLimit/python
src_HiggsAnalysis_CombinedLimit_python_parent := src/HiggsAnalysis/CombinedLimit
ALL_PYTHON_DIRS += $(patsubst src/%,%,src/HiggsAnalysis/CombinedLimit/python)
PyHiggsAnalysisCombinedLimit_files := $(patsubst src/HiggsAnalysis/CombinedLimit/python/%,%,$(wildcard $(foreach dir,src/HiggsAnalysis/CombinedLimit/python ,$(foreach ext,$(SRC_FILES_SUFFIXES),$(dir)/*.$(ext)))))
PyHiggsAnalysisCombinedLimit_LOC_USE := self   
PyHiggsAnalysisCombinedLimit_PACKAGE := self/src/HiggsAnalysis/CombinedLimit/python
ALL_PRODS += PyHiggsAnalysisCombinedLimit
PyHiggsAnalysisCombinedLimit_INIT_FUNC        += $$(eval $$(call PythonProduct,PyHiggsAnalysisCombinedLimit,src/HiggsAnalysis/CombinedLimit/python,src_HiggsAnalysis_CombinedLimit_python))
else
$(eval $(call MultipleWarningMsg,PyHiggsAnalysisCombinedLimit,src/HiggsAnalysis/CombinedLimit/python))
endif
ALL_COMMONRULES += src_HiggsAnalysis_CombinedLimit_python
src_HiggsAnalysis_CombinedLimit_python_INIT_FUNC += $$(eval $$(call CommonProductRules,src_HiggsAnalysis_CombinedLimit_python,src/HiggsAnalysis/CombinedLimit/python,PYTHON))
src_HiggsAnalysis_CombinedLimit_scripts_files := $(filter-out \#% %\#,$(notdir $(wildcard $(foreach dir,$(LOCALTOP)/src/HiggsAnalysis/CombinedLimit/scripts,$(dir)/*))))
$(eval $(call Src2StoreCopy,src_HiggsAnalysis_CombinedLimit_scripts,src/HiggsAnalysis/CombinedLimit/scripts,$(SCRAMSTORENAME_BIN),*))
