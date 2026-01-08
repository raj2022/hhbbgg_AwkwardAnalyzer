import numpy as np

def photon_scale_hists(events, mask, bins):
    """
    Shape-only systematic:
    use shifted diphoton mass
    """

    w = events["weight_nominal"][mask]

    mgg_nom  = events["diphoton_mass"][mask]
    mgg_up   = events["diphoton_mass_PhotonScaleUp"][mask]
    mgg_down = events["diphoton_mass_PhotonScaleDown"][mask]

    h_nom, _  = np.histogram(mgg_nom,  bins=bins, weights=w)
    h_up, _   = np.histogram(mgg_up,   bins=bins, weights=w)
    h_down, _ = np.histogram(mgg_down, bins=bins, weights=w)

    return h_nom, h_up, h_down


def photon_resolution_hists(events, mask, bins):

    w = events["weight_nominal"][mask]

    mgg_nom  = events["diphoton_mass"][mask]
    mgg_up   = events["diphoton_mass_PhotonSmearUp"][mask]
    mgg_down = events["diphoton_mass_PhotonSmearDown"][mask]

    h_nom, _  = np.histogram(mgg_nom,  bins=bins, weights=w)
    h_up, _   = np.histogram(mgg_up,   bins=bins, weights=w)
    h_down, _ = np.histogram(mgg_down, bins=bins, weights=w)

    return h_nom, h_up, h_down


def photon_id_lnN(events, mask):

    w = events["weight_nominal"][mask]

    sf    = events["photonIDSF"][mask]
    sf_up = events["photonIDSFUp"][mask]
    sf_dn = events["photonIDSFDown"][mask]

    Y_nom = w.sum()
    Y_up  = (w * sf_up / sf).sum()
    Y_dn  = (w * sf_dn / sf).sum()

    return max(Y_up/Y_nom, Y_dn/Y_nom)
