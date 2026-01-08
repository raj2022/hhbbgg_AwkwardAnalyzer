def btag_lnN(events, mask):

    w = events["weight_nominal"][mask]

    sf    = events["btagSF"][mask]
    sf_up = events["btagSFUp"][mask]
    sf_dn = events["btagSFDown"][mask]

    Y_nom = w.sum()
    Y_up  = (w * sf_up / sf).sum()
    Y_dn  = (w * sf_dn / sf).sum()

    return max(Y_up/Y_nom, Y_dn/Y_nom)
