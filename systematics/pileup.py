def pu_weights(events, mask):
    """
    flashgg prescription:
    w_var = w_nom * (puWeightVar / puWeight)
    """
    w_nom = events["weight_nominal"][mask]
    pu    = events["pileupWeight"][mask]

    w_up   = w_nom * events["pileupWeightUp"][mask]   / pu
    w_down = w_nom * events["pileupWeightDown"][mask] / pu

    return w_up, w_down
