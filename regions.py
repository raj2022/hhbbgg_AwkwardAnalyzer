# regions.py
#
# Region (event category) mask definitions for the X->YH->bbgg analyzer.
# Each get_mask_<region>() function returns a boolean awkward array
# selecting events belonging to that region.
#
# --------------------------------------------------------------------------
# FIXED IN THIS PASS
# --------------------------------------------------------------------------
# 1. SENTINEL-VALUE PROTECTION added explicitly to every region below
#    (not just preselection) -- see the earlier pass's notes; unchanged
#    here. -9999.00 (dibjet_mass/diphoton_mass reconstruction-failure
#    sentinel) is now excluded in every region.
#
# 2. Dead code removed: get_mask_wmunu1b() (unrelated W+jets/muon-channel
#    mask from a different analysis).
#
# 3. THE PNetRegPtRawRes CUTS -- CONFIRMED BUG, NOW FIXED.
#    Previously flagged as suspicious, now definitively confirmed against
#    the actual HiggsDNA production source (higgs_dna/tools/
#    HHbbgg_mbb_regression.py): PNetRegPtRawRes is listed explicitly as
#    an INPUT FEATURE to an ONNX neural-network regression model that
#    computes the corrected dijet mass. It is never, anywhere in the
#    ~136-file HiggsDNA codebase, compared against a threshold -- a
#    direct grep for "PNetRegPtRawRes\s*[<>]" across the entire framework
#    returns zero matches. It was never intended to be a selection-cut
#    variable at all.
#
#    Direct evidence this specific analysis's use of it as a cut is a
#    genuine bug, not a deliberate design choice: on real production
#    data, PNetRegPtRawRes's observed (non-sentinel) values only reach
#    max~=0.50 (lead) / max~=0.65 (sublead) -- so a ">0.2605" cut only
#    lets through 0.4% / 3.5% of events respectively even before
#    combining both jets, which combined with the other cuts in srbbgg
#    produced exactly 0 surviving events out of 7879 in the 'selection'-
#    level sample for one real mass point (NMSSM_X700_Y500) -- not
#    "restrictive", effectively impossible to pass. The variable name
#    sits immediately adjacent to btagPNetB (the real b-tag discriminant)
#    in HiggsDNA's own jet-property lists, consistent with a copy-paste
#    substitution.
#
#    Fix applied per-region, based on what each region's OWN correctly-
#    named PNetB cut already does:
#      - srbbgg, srbbggMET, crantibbgg, crantibbantigg, sideband: each
#        already has its own correctly-named PNetB cut alongside the
#        erroneous PNetRegPtRawRes lines -- the PNetRegPtRawRes lines
#        were purely redundant/erroneous and are simply REMOVED; the
#        real b-tagging requirement was already present via PNetB.
#      - crbbantigg: DIFFERENT case -- here the real PNetB cut
#        (`PNetB > 0.2605`, matching this region's own docstring
#        "pass medium Btag") was commented OUT, with PNetRegPtRawRes
#        left as the only active (and effectively impossible) b-tag-like
#        requirement. Fixed by RESTORING the commented-out PNetB > 0.2605
#        cuts rather than just deleting -- removing the erroneous line
#        alone would have left this region with NO b-tagging requirement
#        at all, contradicting its own documented intent.
#
#    Sentinel note: PNetRegPtRawRes's own default/failure value in
#    HiggsDNA is -999.0 (confirmed: `choose_jet(..., -999.0)` in
#    HHbbgg.py) -- a DIFFERENT sentinel convention than the -9999.0 used
#    for dibjet_mass/diphoton_mass. Not otherwise acted on here since
#    PNetRegPtRawRes is no longer used as a cut variable in any region
#    below; relevant if it's ever read downstream for another purpose.
# --------------------------------------------------------------------------

import awkward as ak


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


def get_mask_srbbgg(cms_events):    # Pass medium Btag and pass tight photonID
    mask_srbbgg = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        & (cms_events.lead_pho_mvaID_WP80 == 1)  # tight cut mvaID80
        & (cms_events.sublead_pho_mvaID_WP80 == 1)
        & (cms_events.lead_bjet_PNetB > 0.2605)
        & (cms_events.sublead_bjet_PNetB > 0.2605)
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
    mask_srbbggMET = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        & (cms_events.lead_pho_mvaID_WP80 == 1) # Tight working point(80% efficiency)
        & (cms_events.sublead_pho_mvaID_WP80 == 1)
        & (cms_events.lead_bjet_PNetB > 0.2605)
        & (cms_events.sublead_bjet_PNetB > 0.2605)
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
    mask_crantibbgg = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        #(cms_events.lead_pho_mvaID_WP90 == 1)
        #& (cms_events.sublead_pho_mvaID_WP90 == 1)
        & (cms_events.lead_pho_mvaID_WP80 == 1)
        & (cms_events.sublead_pho_mvaID_WP80 == 1)
        & (cms_events.lead_bjet_PNetB < 0.2605)
        & (cms_events.sublead_bjet_PNetB < 0.2605)
        & (cms_events.lead_isScEtaEB == 1)
        & (cms_events.sublead_isScEtaEB == 1)
    )
    return mask_crantibbgg


def get_mask_crbbantigg(cms_events):    # pass medium Btag, pass loose photonID, and fail tight photonID
    mask_crbbantigg = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        & (cms_events.lead_pho_mvaID_WP80 == 0)
        & (cms_events.sublead_pho_mvaID_WP80 == 0)
        & (cms_events.lead_pho_mvaID_WP90 == 1)
        & (cms_events.sublead_pho_mvaID_WP90 == 1)
        # FIXED: the real PNetB cuts below were previously commented out,
        # with the erroneous PNetRegPtRawRes substituted in as the only
        # active (effectively-impossible) requirement -- see module
        # docstring. Restored to match this region's own documented
        # intent ("pass medium Btag").
        & (cms_events.lead_bjet_PNetB > 0.2605)
        & (cms_events.sublead_bjet_PNetB > 0.2605)
        & (cms_events.lead_isScEtaEB == 1)
        & (cms_events.sublead_isScEtaEB == 1)
    )
    return mask_crbbantigg

# Defining another control region
def get_mask_crantibbantigg(cms_events):
    mask_crantibbantigg = (
        (cms_events.dibjet_mass > 0) & (cms_events.diphoton_mass > 0)
        & (cms_events.lead_pho_mvaID_WP80 == 0)
        & (cms_events.sublead_pho_mvaID_WP80 == 0)
        & (cms_events.lead_pho_mvaID_WP90 == 1)
        & (cms_events.sublead_pho_mvaID_WP90 == 1)
        & (cms_events.lead_bjet_PNetB < 0.2605)
        & (cms_events.sublead_bjet_PNetB < 0.2605)
        & (cms_events.lead_isScEtaEB == 1)
        & (cms_events.sublead_isScEtaEB == 1)
    )
    return mask_crantibbantigg

## Side band inclusion based on HIG-2019_186

def get_mask_sideband(cms_events):   # low PhotonID
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
        & (cms_events.lead_bjet_PNetB > 0.2605)
        & (cms_events.sublead_bjet_PNetB > 0.2605)
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