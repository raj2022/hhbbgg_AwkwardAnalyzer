# regions.py
#
# Region (event category) mask definitions for the X->YH->bbgg analyzer.
# Each get_mask_<region>() function returns a boolean awkward array
# selecting events belonging to that region.
#
# --------------------------------------------------------------------------
# FIXED IN EARLIER PASSES (unchanged, see full history below)
# --------------------------------------------------------------------------
# 1. SENTINEL-VALUE PROTECTION -- (cms_events.dibjet_mass > 0) and
#    (cms_events.diphoton_mass > 0) already exclude the -9999.0
#    reconstruction-failure sentinel in every region, since -9999.0 < 0.
#    No additional explicit sentinel check was needed on top of these.
#
# 2. Dead code removed: get_mask_wmunu1b() (unrelated W+jets/muon-channel
#    mask from a different analysis).
#
# 3. THE PNetRegPtRawRes CUTS -- CONFIRMED BUG, FIXED.
#    PNetRegPtRawRes is an ONNX regression input feature
#    (higgs_dna/tools/HHbbgg_mbb_regression.py), never intended as a
#    selection-cut variable -- confirmed via full-codebase grep for
#    "PNetRegPtRawRes\s*[<>]" returning zero matches anywhere in
#    HiggsDNA. A ">0.2605" cut on it let through ~0.4%/3.5% of events
#    per jet (lead/sublead) even before combining, producing 0 surviving
#    events out of 7879 for NMSSM_X700_Y500 in the 'selection'-level
#    sample. Fixed per-region:
#      - srbbgg, srbbggMET, crantibbgg, crantibbantigg, sideband: the
#        erroneous PNetRegPtRawRes lines were purely redundant with each
#        region's own correctly-named PNetB cut and were removed.
#      - crbbantigg: the real PNetB cut had been commented out, leaving
#        PNetRegPtRawRes as the only (effectively impossible) b-tag-like
#        requirement. Fixed by restoring the PNetB cut rather than just
#        deleting the bug, since this region's docstring documents
#        "pass medium Btag" as its intent.
#
# --------------------------------------------------------------------------
# FIXED IN THIS PASS
# --------------------------------------------------------------------------
# 4. B-TAGGING WORKING POINT -- HARDCODED 0.2605 REPLACED WITH
#    YEAR-DEPENDENT VALUES (see tools/WPs_btagging_HHbbgg.json):
#
#        2022preEE     PNet   0.2450
#        2022postEE    PNet   0.2605   <- the value that was hardcoded
#        2023preBPix   PNet   0.1917
#        2023postBPix  PNet   0.1919
#        2024          UParT  0.1272
#        2025          UParT  0.1272
#
# 5. B-TAGGING DISCRIMINANT -- NOW ALSO YEAR-DEPENDENT, NOT JUST THE
#    THRESHOLD.
#    CORRECTION to a note in an earlier pass of this file: it was
#    previously believed that HiggsDNA's HHbbgg.py hardcoded the stored
#    per-jet b-tag branch to PNet for every year, with no UParT
#    equivalent stored for 2024/2025. That was WRONG -- checked directly
#    against HHbbgg.py (~line 1085-1120): for nano_version >= 14
#    (2024/2025), BOTH branches are written to the output ntuple:
#        {AnType}_lead_bjet_btagPNetB        (always)
#        {AnType}_lead_bjet_btagUParTAK4B    (nano_version >= 14 only)
#    and equivalently for sublead_. HiggsDNA itself is not buggy here.
#
#    The actual bug was entirely on this side: every region below read
#    lead_bjet_PNetB / sublead_bjet_PNetB unconditionally, which for
#    2024/2025 is simply the wrong branch -- the UParT-scored branch
#    (renamed here to lead_bjet_UParTAK4B / sublead_bjet_UParTAK4B by
#    our postprocessing, matching the lead_bjet_PNetB naming pattern)
#    was sitting right there, unused.
#
#    Fixed by adding _btag_score(cms_events, leg), which selects the
#    PNet branch for 2022/2023 and the UParT branch for 2024/2025 per
#    event, used together with _btag_medium_wp() (item 4) in every
#    region that cuts on b-tagging: srbbgg, srbbggMET, crantibbgg,
#    crbbantigg, crantibbantigg, sideband.
#
#    TODO: `cms_events.year` below is a placeholder for whatever field
#    actually carries the per-event year/era string in this ntuple --
#    confirm and adjust before running.
#    TODO: confirm `lead_bjet_UParTAK4B` / `sublead_bjet_UParTAK4B` are
#    the exact column names produced by our postprocessing/merge step
#    for the `{AnType}_lead_bjet_btagUParTAK4B` HiggsDNA branch -- adjust
#    _btag_score() below if the naming convention differs.
# --------------------------------------------------------------------------

import awkward as ak
import numpy as np

# Medium WP by year (tools/WPs_btagging_HHbbgg.json). 2022/2023 use PNet;
# 2024/2025 use UParT -- see _btag_score() for the matching discriminant.
BTAG_MEDIUM_WP = {
    "2022preEE": 0.2450,
    "2022postEE": 0.2605,
    "2023preBPix": 0.1917,
    "2023postBPix": 0.1919,
    "2024": 0.1272,
    "2025": 0.1272,
}

# Years whose stored b-tag discriminant is UParT rather than PNet
# (HiggsDNA nano_version >= 14).
UPART_YEARS = {"2024", "2025"}


def _btag_medium_wp(cms_events):
    """
    Per-event Medium b-tagging WP threshold, looked up by year.

    TODO: `cms_events.year` is a placeholder -- replace with whatever
    field actually holds the per-event year/era string (or map an
    integer era code to the BTAG_MEDIUM_WP keys) in this ntuple.
    """
    years = ak.to_numpy(cms_events.year)
    wp = np.array([BTAG_MEDIUM_WP[y] for y in years])
    return wp


def _btag_score(cms_events, leg):
    """
    Per-event b-tag discriminant for 'lead' or 'sublead', matching the
    tagger actually used for that event's year:
      - 2022/2023 -> {leg}_bjet_PNetB       (PNet)
      - 2024/2025 -> {leg}_bjet_UParTAK4B   (UParT)

    TODO: confirm cms_events.year field name (see _btag_medium_wp) and
    confirm the UParT branch's post-merge column name matches
    f"{leg}_bjet_UParTAK4B" below.
    """
    years = ak.to_numpy(cms_events.year)
    pnet = getattr(cms_events, f"{leg}_bjet_PNetB")
    upart = getattr(cms_events, f"{leg}_bjet_UParTAK4B")
    use_upart = np.isin(years, list(UPART_YEARS))
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
# Medium WP and discriminant are both year-dependent -- see
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
        # threshold + discriminant are now both year-dependent per items 4/5.
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