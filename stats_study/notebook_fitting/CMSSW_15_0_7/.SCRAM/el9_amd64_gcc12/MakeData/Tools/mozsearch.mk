ALL_TOOLS      += mozsearch
mozsearch_EX_FLAGS_INDEX_FLAGS  := -Xclang -load -Xclang libclang-index-plugin.so -Xclang -add-plugin -Xclang mozsearch-index -Xclang -plugin-arg-mozsearch-index -Xclang src/ -Xclang -plugin-arg-mozsearch-index -Xclang mozsearch/ -Xclang -plugin-arg-mozsearch-index -Xclang tmp/el9_amd64_gcc12/src/

