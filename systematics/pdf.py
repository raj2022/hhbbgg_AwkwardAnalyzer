import numpy as np

def pdf_variation(events, mask, vals, w_nom, bins):
    """
    flashgg:
      RMS of (pdfWeight / pdfWeight[0])
    """

    pdf_weights = events["LHEPdfWeight"][mask]
    w0 = pdf_weights[:, 0]

    variations = []
    for i in range(1, pdf_weights.shape[1]):
        variations.append(pdf_weights[:, i] / w0)

    variations = np.array(variations)
    rms = np.std(variations, axis=0)

    w_up   = w_nom * (1 + rms)
    w_down = w_nom * (1 - rms)

    h_up, _   = np.histogram(vals, bins=bins, weights=w_up)
    h_down, _ = np.histogram(vals, bins=bins, weights=w_down)

    return h_up, h_down
