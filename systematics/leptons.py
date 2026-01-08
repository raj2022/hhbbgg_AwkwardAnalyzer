def lepton_veto_lnN(events, mask):
    """
    Acceptance uncertainty due to lepton veto SFs
    """

    w_nom = events["weight_nominal"][mask]

    # Example combined lepton SF (electron + muon)
    sf     = events["leptonSF"][mask]
    sf_up  = events["leptonSFUp"][mask]
    sf_dn  = events["leptonSFDown"][mask]

    Y_nom = w_nom.sum()
    Y_up  = (w_nom * sf_up / sf).sum()
    Y_dn  = (w_nom * sf_dn / sf).sum()

    lnN = max(Y_up / Y_nom, Y_dn / Y_nom)

    return lnN
