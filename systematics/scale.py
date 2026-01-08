import numpy as np

VALID_INDICES = [0, 1, 2, 3, 5, 6, 7, 8]  # CMS prescription

def scale_variation(events, mask, vals, w_nom, bins):

    scale_weights = events["LHEScaleWeight"][mask]
    w0 = scale_weights[:, 0]

    ratios = []
    for i in VALID_INDICES:
        ratios.append(scale_weights[:, i] / w0)

    ratios = np.array(ratios)

    up   = np.max(ratios, axis=0)
    down = np.min(ratios, axis=0)

    w_up   = w_nom * up
    w_down = w_nom * down

    h_up, _   = np.histogram(vals, bins=bins, weights=w_up)
    h_down, _ = np.histogram(vals, bins=bins, weights=w_down)

    return h_up, h_down
