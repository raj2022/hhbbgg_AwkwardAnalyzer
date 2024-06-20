import awkward as ak

# def get_mask_wmunu1b(cms_events):
#     mask_wmunu1b = ( (cms_events.mettrig ) &
#                     (cms_events.filters) &
#                     (cms_events.nEleLoose==0 ) &
#                     #(cms_events.npho==0) &
#                     (cms_events.metpt>100.) &
#                     (cms_events.ncleanpho==0) &
#                     (cms_events.ntau==0) &
#                     (cms_events.nMuLoose==1) &
#                     (cms_events.nMuTight==1) &
#                     (cms_events.delta_met_topmu < 0.5 ) &
#                     (cms_events.recoil_Wmunu0>250.) &
#                     (cms_events.min_dphi_jet_met > 0.5) &
#                     (cms_events.nJetLoose==1 ) &
#                     (cms_events.nJetTight==1 ) &
#                     (cms_events.nJetb ==1 ) &
#                     (cms_events.mt_Wmunu0 >=0 ) & (cms_events.mt_Wmunu0 < 160 )
#                  )

#     return mask_wmunu1b


def get_mask_preselection(cms_events):
    mask_preselection = ( (cms_events.dibjet_mass > 0) &
                    (cms_events.diphoton_mass > 0)
    )
    return mask_preselection

# Check https://btv-wiki.docs.cern.ch/ScaleFactors/Run3Summer22/ for the tagger point score 

def get_mask_selection(cms_events):
    mask_selection = (
        (cms_events.lead_pho_mvaID_WP90==1) &
        (cms_events.sublead_pho_mvaID_WP90==1) &
        (cms_events.lead_bjet_PNetB > 0.0499) &
        (cms_events.sublead_bjet_PNetB > 0.0499)
    )
    return mask_selection




