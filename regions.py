# regions.py
#
# Region (event category) mask definitions for the X->YH->bbgg analyzer.
# Each get_mask_<region>() function returns a boolean awkward array
# selecting events belonging to that region.
#
# --------------------------------------------------------------------------
# FIXED IN EARLIER PASSES (unchanged, kept for history)
# --------------------------------------------------------------------------
# 1. SENTINEL-VALUE PROTECTION -- (cms_events.dibjet_mass > 0) and
#    (cms_events.diphoton_mass > 0) already exclude the -9999.0
#    reconstruction-failure sentinel in every region, since -9999.0 < 0.
#
# 2. Dead code removed: get_mask_wmunu1b() (unrelated W+jets/muon-channel
#    mask from a different analysis).
#
# 3. THE PNetRegPtRawRes CUTS -- CONFIRMED BUG, FIXED. PNetRegPtRawRes is
#    an ONNX regression input feature (higgs_dna/tools/
#    HHbbgg_mbb_regression.py), never intended as a selection-cut
#    variable -- confirmed via full-codebase grep for
#    "PNetRegPtRawRes\s*[<>]" returning zero matches anywhere in
#    HiggsDNA. A ">0.2605" cut on it let through ~0.4%/3.5% of events
#    per jet (lead/sublead) even before combining, producing 0 surviving
#    events out of 7879 for NMSSM_X700_Y500 in the 'selection'-level
#    sample. Removed everywhere it appeared (srbbgg, srbbggMET,
#    crantibbgg, crantibbantigg, sideband -- purely redundant with each
#    region's own correctly-named PNetB cut) and, for crbbantigg
#    specifically, the real PNetB cut that had been commented out in
#    its place was restored, matching this region's own documented
#    intent ("pass medium Btag").
#
# --------------------------------------------------------------------------
# FIXED IN THIS PASS
# --------------------------------------------------------------------------
# 4. B-TAGGING WORKING POINT -- HARDCODED 0.2605 REPLACED WITH
#    ERA-DEPENDENT VALUES (tools/WPs_btagging_HHbbgg.json):
#
#        era_code  year/era        tagger  WP
#        0         2022preEE       PNet    0.2450
#        1         2022postEE      PNet    0.2605   <- the value that was hardcoded
#        2         2023preBPix     PNet    0.1917
#        3         2023postBPix    PNet    0.1919
#        4         2024            UParT   0.1272
#        5         2025            UParT   0.1272
#
# 5. B-TAGGING DISCRIMINANT -- NOW ALSO ERA-DEPENDENT, NOT JUST THE
#    THRESHOLD. HiggsDNA itself is not buggy here -- confirmed directly
#    against HHbbgg.py (~line 1085-1120): for nano_version >= 14
#    (2024/2025), BOTH branches are written to the output ntuple
#    ({AnType}_lead_bjet_btagPNetB always, {AnType}_lead_bjet_
#    btagUParTAK4B for nano_version >= 14 only, and equivalently for
#    sublead_). The bug was entirely on this side: every region below
#    read lead_bjet_PNetB / sublead_bjet_PNetB unconditionally, which
#    for 2024/2025 is simply the wrong branch -- the UParT-scored
#    branch (lead_bjet_PNetUParTAK4B / sublead_bjet_PNetUParTAK4B in
#    this ntuple's own naming, matching hhbbgg_analyzer_with_
#    systematics.py's cms_events field names exactly) was sitting right
#    there, unused, since HiggsDNA production onward.
#
#    era_code (int8, 0-5 per the table above) is stamped onto every
#    event by hhbbgg_analyzer_with_systematics.py's
#    era_code_from_year_era() -- see that file's own matching ERA_CODES
#    table; keep the two in sync if either changes. This file only ever
#    consumes the already-resolved integer via cms_events.era_code, and
#    never re-derives year/era from a filename itself.
#
#    Fixed by adding _btag_medium_wp() and _btag_score(cms_events, leg),
#    used together in every region that cuts on b-tagging: srbbgg,
#    srbbgg_EBEB, srbbgg_mixed, srbbgg_EEEE, srbbggMET, crantibbgg,
#    crbbantigg, crantibbantigg, sideband. preselection, selection,
#    idmva_presel, idmva_sideband have no b-tagging cut and are
#    unaffected.
#
# 6. srbbgg_EBEB / srbbgg_mixed / srbbgg_EEEE (both-barrel / one-barrel-
#    one-endcap / both-endcap photon splits) -- required by
#    hhbbgg_analyzer_with_systematics.py's own imports and keys_to_copy
#    list (confirmed directly: an ImportError for get_mask_srbbgg_EBEB
#    on a real run showed the analyzer already expects these). Restored
#    here now using the working, era-aware _btag_score()/
#    _btag_medium_wp() helpers above, rather than the old hardcoded
#    PNetB cut an earlier draft of this split used before those helpers
#    existed.
# --------------------------------------------------------------------------

import awkward as ak
import numpy as np

# Medium WP by era_code (tools/WPs_btagging_HHbbgg.json). Index i here
# corresponds exactly to era_code == i, matching
# hhbbgg_analyzer_with_systematics.py's ERA_CODES table. 2022/2023 (codes
# 0-3) use PNet; 2024/2025 (codes 4-5) use UParT -- see UPART_ERA_CODES
# and _btag_score() below for the matching discriminant.
BTAG_MEDIUM_WP = np.array([
    0.2450,  # 0: 2022preEE   (PNet)
    0.2605,  # 1: 2022postEE  (PNet)
    0.1917,  # 2: 2023preBPix (PNet)
    0.1919,  # 3: 2023postBPix (PNet)
    0.1272,  # 4: 2024        (UParT)
    0.1272,  # 5: 2025        (UParT)
])

# era_code values whose stored b-tag discriminant is UParT rather than
# PNet (HiggsDNA nano_version >= 14).
UPART_ERA_CODES = {4, 5}


def _validate_era_code(era_code_np):
    """Fail loudly on an era_code value outside the known 0-5 range,
    rather than let a silent indexing bug produce a wrong WP/discriminant
    for some events -- same fail-loud philosophy as
    era_code_from_year_era() in hhbbgg_analyzer_with_systematics.py."""
    bad = (era_code_np < 0) | (era_code_np >= len(BTAG_MEDIUM_WP))
    if np.any(bad):
        bad_values = sorted(set(era_code_np[bad].tolist()))
        raise ValueError(
            f"_btag_medium_wp/_btag_score: found era_code value(s) outside "
            f"the known 0-{len(BTAG_MEDIUM_WP) - 1} range: {bad_values}. "
            f"Check era_code_from_year_era()'s ERA_CODES table in "
            f"hhbbgg_analyzer_with_systematics.py for what's actually "
            f"being stamped onto events."
        )


def _btag_medium_wp(cms_events):
    """Per-event Medium b-tagging WP threshold, looked up by era_code."""
    era_code_np = ak.to_numpy(cms_events.era_code)
    _validate_era_code(era_code_np)
    return BTAG_MEDIUM_WP[era_code_np]


def _btag_score(cms_events, leg):
    """Per-event b-tag discriminant for 'lead' or 'sublead', matching the
    tagger actually used for that event's era:
      - era_code 0-3 (2022/2023) -> {leg}_bjet_PNetB          (PNet)
      - era_code 4-5 (2024/2025) -> {leg}_bjet_PNetUParTAK4B  (UParT)

    Field names match hhbbgg_analyzer_with_systematics.py's cms_events
    zip exactly (that file's own naming, not renamed here).
    """
    era_code_np = ak.to_numpy(cms_events.era_code)
    _validate_era_code(era_code_np)
    pnet = getattr(cms_events, f"{leg}_bjet_PNetB")
    upart = getattr(cms_events, f"{leg}_bjet_PNetUParTAK4B")
    use_upart = np.isin(era_code_np, list(UPART_ERA_CODES))
    return ak.where(use_upart, upart, pnet)


def get_mask_preselection(cms_events):
    mask_preselection = (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
    return mask_preselection

#------------------------

def get_mask_selection(cms_events):
    mask_selection = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        & (cms_events.lead_isScEtaEB == 1)
        & (cms_events.sublead_isScEtaEB == 1)
    )
    return mask_selection


#-----------------
# Check https://btv-wiki.docs.cern.ch/ScaleFactors/Run3Summer22/ for the tagger point score
# Medium WP and discriminant are both era-dependent -- see
# BTAG_MEDIUM_WP / _btag_medium_wp() / _btag_score() above.


def get_mask_srbbgg(cms_events):    # Pass medium Btag and pass tight photonID
    wp = _btag_medium_wp(cms_events)
    lead_btag = _btag_score(cms_events, "lead")
    sublead_btag = _btag_score(cms_events, "sublead")
    mask_srbbgg = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        & (cms_events.lead_pho_mvaID_WP80 == 1)  # tight cut mvaID80
        & (cms_events.sublead_pho_mvaID_WP80 == 1)
        & (lead_btag > wp)
        & (sublead_btag > wp)
        & (cms_events.lead_isScEtaEB == 1)
        & (cms_events.sublead_isScEtaEB == 1)
    #    & (
    #        (
    #            (cms_events.signal == 0)
    #            & (
    #                ((cms_events.diphoton_mass > 130) | (cms_events.diphoton_mass < 90))
    #                & ((cms_events.dibjet_mass > 130) | (cms_events.dibjet_mass < 90))
    #            )
    #        )
    #        | (
    #            (cms_events.signal == 1)
    #            & (cms_events.diphoton_mass > 0)
    #            & (cms_events.dibjet_mass > 0)
    #        )
    #    )
    )
    return mask_srbbgg


def get_mask_srbbgg_EBEB(cms_events):    # both photons barrel
    wp = _btag_medium_wp(cms_events)
    lead_btag = _btag_score(cms_events, "lead")
    sublead_btag = _btag_score(cms_events, "sublead")
    mask_srbbgg_EBEB = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        & (cms_events.lead_pho_mvaID_WP80 == 1)
        & (cms_events.sublead_pho_mvaID_WP80 == 1)
        & (lead_btag > wp)
        & (sublead_btag > wp)
        & (cms_events.lead_isScEtaEB == 1)
        & (cms_events.sublead_isScEtaEB == 1)
    )
    return mask_srbbgg_EBEB


def get_mask_srbbgg_mixed(cms_events):   # exactly one photon in EE
    wp = _btag_medium_wp(cms_events)
    lead_btag = _btag_score(cms_events, "lead")
    sublead_btag = _btag_score(cms_events, "sublead")
    both_barrel = (cms_events.lead_isScEtaEB == 1) & (cms_events.sublead_isScEtaEB == 1)
    both_endcap = (cms_events.lead_isScEtaEE == 1) & (cms_events.sublead_isScEtaEE == 1)
    mask_srbbgg_mixed = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        & (cms_events.lead_pho_mvaID_WP80 == 1)
        & (cms_events.sublead_pho_mvaID_WP80 == 1)
        & (lead_btag > wp)
        & (sublead_btag > wp)
        & ~both_barrel & ~both_endcap
    )
    return mask_srbbgg_mixed


def get_mask_srbbgg_EEEE(cms_events):    # both photons endcap
    wp = _btag_medium_wp(cms_events)
    lead_btag = _btag_score(cms_events, "lead")
    sublead_btag = _btag_score(cms_events, "sublead")
    mask_srbbgg_EEEE = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        & (cms_events.lead_pho_mvaID_WP80 == 1)
        & (cms_events.sublead_pho_mvaID_WP80 == 1)
        & (lead_btag > wp)
        & (sublead_btag > wp)
        & (cms_events.lead_isScEtaEE == 1)
        & (cms_events.sublead_isScEtaEE == 1)
    )
    return mask_srbbgg_EEEE


def get_mask_srbbggMET(cms_events):
    wp = _btag_medium_wp(cms_events)
    lead_btag = _btag_score(cms_events, "lead")
    sublead_btag = _btag_score(cms_events, "sublead")
    mask_srbbggMET = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        & (cms_events.lead_pho_mvaID_WP80 == 1) # Tight working point(80% efficiency)
        & (cms_events.sublead_pho_mvaID_WP80 == 1)
        & (lead_btag > wp)
        & (sublead_btag > wp)
        & (cms_events.lead_isScEtaEB == 1)     # photon in the barrel region 
        & (cms_events.sublead_isScEtaEB == 1)  # photon in the barrel region 
        & (
            (
                (cms_events.signal == 0)
                & (
                    ((cms_events.diphoton_mass > 130) | (cms_events.diphoton_mass < 90))
                    & ((cms_events.dibjet_mass > 130) | (cms_events.dibjet_mass < 90))
                )
            )
            | (
                (cms_events.signal == 1)
                & (cms_events.diphoton_mass > 0)
                & (cms_events.dibjet_mass > 0)
            )
        )
    )
    return mask_srbbggMET



def get_mask_crantibbgg(cms_events):   # Fail medium Btag and pass tight photonID
    wp = _btag_medium_wp(cms_events)
    lead_btag = _btag_score(cms_events, "lead")
    sublead_btag = _btag_score(cms_events, "sublead")
    mask_crantibbgg = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        #(cms_events.lead_pho_mvaID_WP90 == 1)
        #& (cms_events.sublead_pho_mvaID_WP90 == 1)
        & (cms_events.lead_pho_mvaID_WP80 == 1)
        & (cms_events.sublead_pho_mvaID_WP80 == 1)
        & (lead_btag < wp)
        & (sublead_btag < wp)
        & (cms_events.lead_isScEtaEB == 1)
        & (cms_events.sublead_isScEtaEB == 1)
    )
    return mask_crantibbgg


def get_mask_crbbantigg(cms_events):    # pass medium Btag, pass loose photonID, and fail tight photonID
    wp = _btag_medium_wp(cms_events)
    lead_btag = _btag_score(cms_events, "lead")
    sublead_btag = _btag_score(cms_events, "sublead")
    mask_crbbantigg = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        & (cms_events.lead_pho_mvaID_WP80 == 0)
        & (cms_events.sublead_pho_mvaID_WP80 == 0)
        & (cms_events.lead_pho_mvaID_WP90 == 1)
        & (cms_events.sublead_pho_mvaID_WP90 == 1)
        # Restored per the earlier fix pass (see module docstring item 3);
        # threshold + discriminant are now both era-dependent per items 4/5.
        & (lead_btag > wp)
        & (sublead_btag > wp)
        & (cms_events.lead_isScEtaEB == 1)
        & (cms_events.sublead_isScEtaEB == 1)
    )
    return mask_crbbantigg

# Defining another control region
def get_mask_crantibbantigg(cms_events):
    wp = _btag_medium_wp(cms_events)
    lead_btag = _btag_score(cms_events, "lead")
    sublead_btag = _btag_score(cms_events, "sublead")
    mask_crantibbantigg = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        & (cms_events.lead_pho_mvaID_WP80 == 0)
        & (cms_events.sublead_pho_mvaID_WP80 == 0)
        & (cms_events.lead_pho_mvaID_WP90 == 1)
        & (cms_events.sublead_pho_mvaID_WP90 == 1)
        & (lead_btag < wp)
        & (sublead_btag < wp)
        & (cms_events.lead_isScEtaEB == 1)
        & (cms_events.sublead_isScEtaEB == 1)
    )
    return mask_crantibbantigg

## Side band inclusion based on HIG-2019_186

def get_mask_sideband(cms_events):   # low PhotonID
    wp = _btag_medium_wp(cms_events)
    lead_btag = _btag_score(cms_events, "lead")
    sublead_btag = _btag_score(cms_events, "sublead")
    mask_sideband = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        # Require both photons to fail WP80 but pass WP90 (i.e., "loose ID")
        & (cms_events.lead_pho_mvaID_WP80 == 0)
        & (cms_events.sublead_pho_mvaID_WP80 == 0)
        & (cms_events.lead_pho_mvaID_WP90 == 1)
        & (cms_events.sublead_pho_mvaID_WP90 == 1)

        # Select events that pass the other standard criteria for photons
        & (cms_events.lead_isScEtaEB == 1)
        & (cms_events.sublead_isScEtaEB == 1)

        # Keep b-tagging open here, or adjust based on what you want to study
        & (lead_btag > wp)
        & (sublead_btag > wp)
    )
    return mask_sideband


# Traingular ABCD 
# Raw Photon MVA ID Regions (numerical cut-based)

def get_mask_idmva_presel(cms_events):
    """
    Events with both photons having raw MVA > -0.7 (tight region)
    """
    mask_idmva_presel = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        & (cms_events.lead_pho_mvaID > -0.7)
        & (cms_events.sublead_pho_mvaID > -0.7)
        & (cms_events.lead_isScEtaEB == 1)
        & (cms_events.sublead_isScEtaEB == 1)
    )
    return mask_idmva_presel


def get_mask_idmva_sideband(cms_events):
    """
    Events with both photons > -0.9, but at least one fails > -0.7 (loose region)
    """
    mask_idmva_sideband =  (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        & (cms_events.lead_pho_mvaID > -0.9)
        & (cms_events.sublead_pho_mvaID > -0.9)
        & ((cms_events.lead_pho_mvaID < -0.7) | (cms_events.sublead_pho_mvaID < -0.7))
        & (cms_events.lead_isScEtaEB == 1)
        & (cms_events.sublead_isScEtaEB == 1)
    )
    return mask_idmva_sideband