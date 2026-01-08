import numpy as np

def jet_JES_hists(events, bins, category_masks):
    """
    Build mjj histograms with JES variations
    """

    hists = {}

    for cat, mask in category_masks.items():

        w = events["weight_nominal"][mask]

        mjj_nom  = events["mjj"][mask]
        mjj_up   = events["mjj_JESUp"][mask]
        mjj_down = events["mjj_JESDown"][mask]

        hists[(cat, "nom")]  = np.histogram(mjj_nom,  bins=bins, weights=w)[0]
        hists[(cat, "up")]   = np.histogram(mjj_up,   bins=bins, weights=w)[0]
        hists[(cat, "down")] = np.histogram(mjj_down, bins=bins, weights=w)[0]

    return hists
