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
