SRC=/eos/cms/store/group/phys_b2g/HHbbgg/HiggsDNA_parquet/v7

samples=(
    DDQCDGJets
    bbHtoGG
    GGJets_MGG-80
    GluGluHtoGG
    TTGG
    ttHtoGG
    VBFHtoGG
    VHtoGG
)

for year in Run3_2022 Run3_2023 Run3_2024 Run3_2025; do
    for sample in "${samples[@]}"; do
        find "$SRC/$year/sim" -type d -name "$sample" | while read -r dir; do

            # Get path relative to v7/
            rel="${dir#$SRC/}"

            echo "================================================"
            echo "Copying: $rel"
            echo "================================================"

            mkdir -p "$rel"

            rsync -ah --info=progress2 \
                "$dir/" \
                "$rel/"
        done
    done
done