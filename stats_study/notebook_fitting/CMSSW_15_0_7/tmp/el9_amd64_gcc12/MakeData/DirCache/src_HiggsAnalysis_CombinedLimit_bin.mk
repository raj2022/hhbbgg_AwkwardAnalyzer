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
