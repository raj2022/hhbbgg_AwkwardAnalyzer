# #!/bin/bash
# ###############################
# ## Copying nominal parquet files for postEE: sraj
# ###############################


# #!/bin/bash

# SRC_BASE="/eos/user/s/sraj/Work_/CUA_20--/Analysis/output_parquet/systematics_v3/2022_postEE/merged"
# DEST_BASE="/afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/postEE"

# mkdir -p "${DEST_BASE}"

# echo "=============================="
# echo " Copying nominal parquet files"
# echo "   (only Y > 85)"
# echo "=============================="

# # ----------------------------
# # COPY FILES
# # ----------------------------
# for dir in ${SRC_BASE}/NMSSM_X*_Y*; do
#     base=$(basename "${dir}")

#     # Parse X and Y
#     if [[ "${base}" =~ X([0-9]+)_Y([0-9]+) ]]; then
#         MX="${BASH_REMATCH[1]}"
#         MY="${BASH_REMATCH[2]}"
#     else
#         echo "WARNING: could not parse masses from ${base}"
#         continue
#     fi

#     # Apply Y cut
#     if (( MY <= 85 )); then
#         continue
#     fi

#     src_file="${dir}/nominal/NOTAG_merged.parquet"
#     dest_file="${DEST_BASE}/NMSSM_X${MX}_Y${MY}.parquet"

#     if [[ -f "${src_file}" ]]; then
#         echo "Copying NMSSM_X${MX}_Y${MY}"
#         cp "${src_file}" "${dest_file}"
#     else
#         echo "WARNING: missing ${src_file}"
#     fi
# done


# ----------------------------
# CHECK MISSING MASS POINTS
# ----------------------------
# echo
# echo "=============================="
# echo " Checking missing mass points "
# echo "   (only Y > 90 considered)  "
# echo "=============================="

# python3 << 'EOF'
# import os
# import re
# from collections import defaultdict

# base_dir = "/eos/user/s/sraj/Work_/CUA_20--/Analysis/output_parquet/systematics_v3/2022_postEE/merged"
# MY_MIN = 85

# mass_points = {
#     300: [90, 95, 100, 125, 150, 170],
#     320: [90, 95, 100, 125, 150, 170],
#     350: [90, 95, 100, 125, 150, 170, 200],
#     400: [90, 95, 100, 125, 150, 170, 200, 250],
#     450: [90, 95, 100, 125, 150, 170, 200, 250, 300],
#     500: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350],
#     550: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400],
#     600: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450],
#     650: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500],
#     700: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550],
#     750: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600],
#     800: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650],
#     850: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
#     900: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
#     950: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
#     1000:[90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
# }

# # Expected grid with Y > 90
# expected = {
#     mx: [my for my in mys if my > MY_MIN]
#     for mx, mys in mass_points.items()
# }

# # Parse existing directories
# pattern = re.compile(r"X(\d+)_Y(\d+)")
# existing = defaultdict(set)

# for d in os.listdir(base_dir):
#     m = pattern.search(d)
#     if m:
#         mx = int(m.group(1))
#         my = int(m.group(2))
#         if my > MY_MIN:
#             existing[mx].add(my)

# # Find missing points
# missing = defaultdict(list)

# for mx, mys in expected.items():
#     for my in mys:
#         if my not in existing.get(mx, set()):
#             missing[mx].append(my)

# # Print summary
# total = 0
# for mx in sorted(missing):
#     if missing[mx]:
#         print(f"MX={mx} missing Y={missing[mx]}")
#         total += len(missing[mx])

# if total == 0:
#     print("✅ No missing mass points (Y > 90)")
# else:
#     print(f"\n❌ Total missing points (Y > 90): {total}")
# EOF









# ###############################
# ## Copying nominal parquet files for preEE: bsinghal
# ###############################

# ##############################
# # Copying nominal parquet files for preEE and preBPix
# ##############################
# !/bin/bash

# SRC_BASE="/eos/user/b/bsinghal/analysis/output/2023preBPix/merged"
# DEST_BASE="/afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/preBPix"


# mkdir -p "${DEST_BASE}"

# echo "=============================="
# echo " Copying nominal parquet files"
# echo "=============================="

# for dir in ${SRC_BASE}/NMSSM-XtoYH-MX-*-MY-*; do
#     base=$(basename "${dir}")

#     # Extract MX and MY
#     MX=$(echo "${base}" | sed -n 's/.*MX-\([0-9]\+\)-MY-\([0-9]\+\).*/\1/p')
#     MY=$(echo "${base}" | sed -n 's/.*MX-\([0-9]\+\)-MY-\([0-9]\+\).*/\2/p')

#     if [[ -z "${MX}" || -z "${MY}" ]]; then
#         echo "WARNING: could not parse masses from ${base}"
#         continue
#     fi

#     src_file="${dir}/nominal/NOTAG_merged.parquet"
#     dest_file="${DEST_BASE}/NMSSM_X${MX}_Y${MY}.parquet"

#     if [[ -f "${src_file}" ]]; then
#         echo "Copying NMSSM_X${MX}_Y${MY}"
#         cp "${src_file}" "${dest_file}"
#     else
#         echo "WARNING: missing ${src_file}"
#     fi
# done

# ###############################
# ## Copying nominal parquet files for postBPix
# ###############################

# #!/bin/bash

# SRC_BASE="/eos/user/b/bsahu/HiggsDNA_v3/HiggsDNA/output_23PostBPix/merged"
# DEST_BASE="/afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/postBPix"

# mkdir -p "${DEST_BASE}"

# echo "=============================="
# echo " Copying nominal parquet files (MY > 90 only)"
# echo "=============================="

# for dir in ${SRC_BASE}/NMSSM_XtoYHto2B2G_MX-*_MY-*; do
#     base=$(basename "${dir}")

#     # Parse MX and MY
#     if [[ "${base}" =~ MX-([0-9]+)_MY-([0-9]+) ]]; then
#         MX="${BASH_REMATCH[1]}"
#         MY="${BASH_REMATCH[2]}"
#     else
#         echo "WARNING: could not parse masses from ${base}"
#         continue
#     fi

#     # ---- FILTER HERE ----
#     if (( MY <= 90 )); then
#         echo "Skipping NMSSM_X${MX}_Y${MY} (MY <= 90)"
#         continue
#     fi
#     # ---------------------

#     src_file="${dir}/nominal/NOTAG_merged.parquet"
#     dest_file="${DEST_BASE}/NMSSM_X${MX}_Y${MY}.parquet"

#     if [[ -f "${src_file}" ]]; then
#         echo "Copying NMSSM_X${MX}_Y${MY}"
#         cp "${src_file}" "${dest_file}"
#     else
#         echo "WARNING: missing ${src_file}"
#     fi
# done



# # ----------------------------
# # CHECK MISSING MASS POINTS preEE and preBPix
# # ----------------------------
# echo
# echo "=============================="
# echo " Checking missing mass points "
# echo "=============================="

# python3 << 'EOF'
# import os
# import re
# from collections import defaultdict

# base_dir = "/eos/user/b/bsinghal/analysis/output/2023preBPix/merged/"

# mass_points = {
#     300: [90, 95, 100, 125, 150, 170],
#     320: [90, 95, 100, 125, 150, 170],
#     350: [90, 95, 100, 125, 150, 170, 200],
#     400: [90, 95, 100, 125, 150, 170, 200, 250],
#     450: [90, 95, 100, 125, 150, 170, 200, 250, 300],
#     500: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350],
#     550: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400],
#     600: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450],
#     650: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500],
#     700: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550],
#     750: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600],
#     800: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650],
#     850: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
#     900: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
#     950: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
#     1000:[90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
# }

# pattern = re.compile(r"MX-(\d+)-MY-(\d+)")
# existing = defaultdict(set)

# for d in os.listdir(base_dir):
#     m = pattern.search(d)
#     if m:
#         existing[int(m.group(1))].add(int(m.group(2)))

# missing = defaultdict(list)

# for mx, mys in mass_points.items():
#     for my in mys:
#         if my not in existing.get(mx, set()):
#             missing[mx].append(my)

# total = 0
# for mx in sorted(missing):
#     if missing[mx]:
#         print(f"MX={mx} missing MY={missing[mx]}")
#         total += len(missing[mx])

# if total == 0:
#     print("✅ No missing mass points")
# else:
#     print(f"\n❌ Total missing points: {total}")
# EOF








# #### ------------------------
# # check for postBPix: bsahu

# # ----------------------------
# # CHECK MISSING MASS POINTS (MY > 90 only)
# # ----------------------------
# echo
# echo "=============================="
# echo " Checking missing mass points "
# echo "   (only MY > 90 considered)  "
# echo "=============================="

# python3 << 'EOF'
# import os
# import re
# from collections import defaultdict

# base_dir = "/eos/user/b/bsahu/HiggsDNA_v3/HiggsDNA/output_23PostBPix/merged"
# MY_MIN = 90   # apply same cut as copy step

# mass_points = {
#     300: [90, 95, 100, 125, 150, 170],
#     320: [90, 95, 100, 125, 150, 170],
#     350: [90, 95, 100, 125, 150, 170, 200],
#     400: [90, 95, 100, 125, 150, 170, 200, 250],
#     450: [90, 95, 100, 125, 150, 170, 200, 250, 300],
#     500: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350],
#     550: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400],
#     600: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450],
#     650: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500],
#     700: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550],
#     750: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600],
#     800: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650],
#     850: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
#     900: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
#     950: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
#     1000:[90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
# }

# # Keep only MY > 90 in expected grid
# expected = {
#     mx: [my for my in mys if my > MY_MIN]
#     for mx, mys in mass_points.items()
# }

# # Parse existing directories (new naming!)
# pattern = re.compile(r"MX-(\d+)_MY-(\d+)")
# existing = defaultdict(set)

# for d in os.listdir(base_dir):
#     m = pattern.search(d)
#     if m:
#         mx = int(m.group(1))
#         my = int(m.group(2))
#         if my > MY_MIN:
#             existing[mx].add(my)

# # Find missing points
# missing = defaultdict(list)

# for mx, mys in expected.items():
#     for my in mys:
#         if my not in existing.get(mx, set()):
#             missing[mx].append(my)

# # Print summary
# total = 0
# for mx in sorted(missing):
#     if missing[mx]:
#         print(f"MX={mx} missing MY={missing[mx]}")
#         total += len(missing[mx])

# if total == 0:
#     print("✅ No missing mass points (MY > 90)")
# else:
#     print(f"\n❌ Total missing points (MY > 90): {total}")
# EOF





## Unified script
#!/bin/bash
set -e

########################################
# GLOBAL CONFIG
########################################
Y_MIN=85   # global Y cut (used everywhere)

########################################
# MASS GRID (single source of truth)
########################################
# read -r -d '' MASS_POINTS_PY << 'EOF'
MASS_POINTS_PY=$(cat << 'EOF'
mass_points = {
    300: [90, 95, 100, 125, 150, 170],
    320: [90, 95, 100, 125, 150, 170],
    350: [90, 95, 100, 125, 150, 170, 200],
    400: [90, 95, 100, 125, 150, 170, 200, 250],
    450: [90, 95, 100, 125, 150, 170, 200, 250, 300],
    500: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350],
    550: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400],
    600: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450],
    650: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500],
    700: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550],
    750: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600],
    800: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650],
    850: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
    900: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
    950: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
    1000:[90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
}
EOF
)


########################################
# FUNCTION: copy files
########################################
copy_nmssm() {
    local SRC_BASE=$1
    local DEST_BASE=$2
    local REGEX=$3

    # mkdir -p "${DEST_BASE}"
    if [[ ! -d "${DEST_BASE}" ]]; then
        echo "ERROR: Destination directory does not exist: ${DEST_BASE}"
        exit 1
    fi

    echo
    echo "=============================="
    echo " Copying from ${SRC_BASE}"
    echo "   (Y > ${Y_MIN})"
    echo "=============================="

    for dir in ${SRC_BASE}/*; do
        base=$(basename "${dir}")

        if [[ "${base}" =~ ${REGEX} ]]; then
            MX="${BASH_REMATCH[1]}"
            MY="${BASH_REMATCH[2]}"
        else
            continue
        fi

        (( MY <= Y_MIN )) && continue

        src_file="${dir}/nominal/NOTAG_merged.parquet"
        dest_file="${DEST_BASE}/NMSSM_X${MX}_Y${MY}.parquet"

        if [[ -f "${src_file}" ]]; then
            echo "Copying NMSSM_X${MX}_Y${MY}"
            cp "${src_file}" "${dest_file}"
        else
            echo "WARNING: missing ${src_file}"
        fi
    done
}

########################################
# FUNCTION: check missing points
########################################
check_missing() {
    local BASE_DIR=$1
    local REGEX=$2

    echo
    echo "=============================="
    echo " Checking missing mass points "
    echo "   (Y > ${Y_MIN})"
    echo "=============================="

    python3 << EOF
import os, re
from collections import defaultdict

MY_MIN = ${Y_MIN}
${MASS_POINTS_PY}

expected = {
    mx: [my for my in mys if my > MY_MIN]
    for mx, mys in mass_points.items()
}

existing = defaultdict(set)
pattern = re.compile(r"${REGEX}")

for d in os.listdir("${BASE_DIR}"):
    m = pattern.search(d)
    if m:
        mx = int(m.group(1))
        my = int(m.group(2))
        if my > MY_MIN:
            existing[mx].add(my)

missing = defaultdict(list)
for mx, mys in expected.items():
    for my in mys:
        if my not in existing.get(mx, set()):
            missing[mx].append(my)

total = 0
for mx in sorted(missing):
    if missing[mx]:
        print(f"MX={mx} missing Y={missing[mx]}")
        total += len(missing[mx])

print()
print("Total missing:", total)
EOF
}

########################################
# CAMPAIGNS
########################################

# ---- preEE (NMSSM-XtoYH-MX-*-MY-*) ----
# copy_nmssm \
#   "/eos/user/b/bsinghal/analysis/output/2022preEE/merged" \
#   "/eos/user/b/bartek/hhbbgg/" \
#   "MX-([0-9]+)-MY-([0-9]+)"

# check_missing \
#   "/eos/user/b/bsinghal/analysis/output/2022preEE/merged" \
#   "MX-([0-9]+)-MY-([0-9]+)"


# ---- postEE (NMSSM_X*_Y*) ----
# copy_nmssm \
#   "/eos/user/s/sraj/Work_/CUA_20--/Analysis/output_parquet/systematics_v3/2022_postEE/merged" \
#   "/eos/user/b/bartek/hhbbgg/" \
#   "X([0-9]+)_Y([0-9]+)"

# check_missing \
#   "/eos/user/s/sraj/Work_/CUA_20--/Analysis/output_parquet/systematics_v3/2022_postEE/merged" \
#   "X([0-9]+)_Y([0-9]+)"


# ---- postBPix (NMSSM_XtoYHto2B2G_MX-*_MY-*) ----
# copy_nmssm \
#   "/eos/user/b/bsahu/HiggsDNA_v3/HiggsDNA/output_23PostBPix/merged" \
#   "/eos/user/b/bartek/hhbbgg/" \
#   "MX-([0-9]+)_MY-([0-9]+)"

# check_missing \
#   "/eos/user/b/bsahu/HiggsDNA_v3/HiggsDNA/output_23PostBPix/merged" \
#   "MX-([0-9]+)_MY-([0-9]+)"


# ---- preBPix (NMSSM-XtoYH-MX-*-MY-*) ----
copy_nmssm \
  "/eos/user/b/bsinghal/analysis/output/2023preBPix/merged" \
  "/eos/user/b/bartek/hhbbgg/" \
  "MX-([0-9]+)-MY-([0-9]+)"

check_missing \
  "/eos/user/b/bsinghal/analysis/output/2023preBPix/merged" \
  "MX-([0-9]+)-MY-([0-9]+)"




# To run
# ./jsonhiggsdnaproduction/copy_nmssm_nominal.sh