# abcd_estimator.py
# Estimator for the ABCD 

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))) # Reading files from the given folder.)

import awkward as ak
import numpy as np

# from regions import (
#     get_mask_srbbgg,
#     get_mask_crantibbgg,
#     get_mask_crbbantigg,
#     get_mask_crantibbantigg,
#     get_mask_sideband
# )

# def compute_abcd_yields(cms_events, use_signal_mask=False):
#     """
#     Computes ABCD background estimation from input events.
    
#     Parameters:
#         cms_events: awkward array of events
#         use_signal_mask (bool): if True, applies signal==0 condition (background-only)

#     Returns:
#         dict with yields, estimated A, and uncertainties
#     """

#     # Apply region masks
#     mask_A = get_mask_srbbgg(cms_events)
#     mask_B = get_mask_crantibbgg(cms_events)
#     mask_C = get_mask_crbbantigg(cms_events)
#     mask_D = get_mask_crantibbantigg(cms_events)
#     mask_E = get_mask_sideband(cms_events)

#     if use_signal_mask:
#         signal_mask = (cms_events.signal == 0)
#         mask_A = mask_A & signal_mask
#         mask_B = mask_B & signal_mask
#         mask_C = mask_C & signal_mask
#         mask_D = mask_D & signal_mask
#         mask_E = mask_E & signal_mask

#     # Event counts
#     n_A = ak.sum(mask_A)
#     n_B = ak.sum(mask_B)
#     n_C = ak.sum(mask_C)
#     n_D = ak.sum(mask_D)
#     n_E = ak.sum(mask_E)

#     # ABCD Estimate
#     if n_D != 0:
#         n_A_est = (n_B * n_C) / n_D
#         err_A_est = n_A_est * np.sqrt(1/n_B + 1/n_C + 1/n_D)
#     else:
#         n_A_est = 0
#         err_A_est = 0

#     return {
#         "N_A_obs": int(n_A),
#         "N_B": int(n_B),
#         "N_C": int(n_C),
#         "N_D": int(n_D),
#         "N_A_est": float(n_A_est),
#         "N_A_est_err": float(err_A_est),
#     }

from regions import (
    get_mask_idmva_presel,
    get_mask_idmva_sideband,
    get_mask_srbbgg,
    get_mask_crantibbgg,
    get_mask_crbbantigg,
    get_mask_crantibbantigg,
)
import awkward as ak

def compute_abcd_yields(cms_events, use_signal_mask=False, photon_id_mode=False):
    if photon_id_mode:
        # Using raw Photon ID MVA score regions
        mask_A = get_mask_idmva_presel(cms_events)
        mask_B = get_mask_idmva_sideband(cms_events)

        # Optionally define empty C/D if needed
        mask_C = ak.zeros_like(mask_A, dtype=bool)
        mask_D = ak.zeros_like(mask_A, dtype=bool)
    else:
        # Using WP80/WP90 region definitions
        mask_A = get_mask_srbbgg(cms_events)
        mask_B = get_mask_crantibbgg(cms_events)
        mask_C = get_mask_crbbantigg(cms_events)
        mask_D = get_mask_crantibbantigg(cms_events)

    # Now compute yields (counts) for each region
    yield_A = ak.sum(mask_A)
    yield_B = ak.sum(mask_B)
    yield_C = ak.sum(mask_C)
    yield_D = ak.sum(mask_D)

    return {
        "A": yield_A,
        "B": yield_B,
        "C": yield_C,
        "D": yield_D
    }
