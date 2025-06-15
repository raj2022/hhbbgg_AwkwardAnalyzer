ifeq ($(strip $(HiggsAnalysis-CombinedLimit/bin)),)
src_HiggsAnalysis-CombinedLimit_bin := self/HiggsAnalysis-CombinedLimit/bin
HiggsAnalysis-CombinedLimit/bin  := src_HiggsAnalysis-CombinedLimit_bin
src_HiggsAnalysis-CombinedLimit_bin_BuildFile    := $(WORKINGDIR)/cache/bf/src/HiggsAnalysis-CombinedLimit/bin/BuildFile
src_HiggsAnalysis-CombinedLimit_bin_LOC_USE := self 
src_HiggsAnalysis-CombinedLimit_bin_EX_USE   := $(foreach d,$(src_HiggsAnalysis-CombinedLimit_bin_LOC_USE),$(if $($(d)_EX_FLAGS_NO_RECURSIVE_EXPORT),,$d))
ALL_EXTERNAL_PRODS += src_HiggsAnalysis-CombinedLimit_bin
src_HiggsAnalysis-CombinedLimit_bin_INIT_FUNC += $$(eval $$(call EmptyPackage,src_HiggsAnalysis-CombinedLimit_bin,src/HiggsAnalysis-CombinedLimit/bin))
endif

