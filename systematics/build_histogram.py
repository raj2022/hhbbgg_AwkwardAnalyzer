import numpy as np
import uproot
from systematics.pileup import pu_weights
from systematics.pdf import pdf_variation
from systematics.scale import scale_variation

def fill_hist(values, weights, bins):
    hist, _ = np.histogram(values, bins=bins, weights=weights)
    return hist

def build_all_histograms(events, config, output_root):
    """
    events: awkward or pandas table from Parquet
    config: binning, observable, category masks
    """

    bins = config["bins"]
    obs  = config["observable"]

    with uproot.recreate(output_root) as fout:
        for cat, mask in config["categories"].items():

            vals = events[obs][mask]
            w_nom = events["weight_nominal"][mask]

            # ---------- Nominal ----------
            h_nom = fill_hist(vals, w_nom, bins)
            fout[f"{cat}/mgg"] = h_nom

            # ---------- Pileup ----------
            w_pu_up, w_pu_down = pu_weights(events, mask)
            fout[f"{cat}/mgg_puUp"]   = fill_hist(vals, w_pu_up, bins)
            fout[f"{cat}/mgg_puDown"] = fill_hist(vals, w_pu_down, bins)

            # ---------- PDF ----------
            h_pdf_up, h_pdf_down = pdf_variation(events, mask, vals, w_nom, bins)
            fout[f"{cat}/mgg_pdfUp"]   = h_pdf_up
            fout[f"{cat}/mgg_pdfDown"] = h_pdf_down

            # ---------- Scale ----------
            h_sc_up, h_sc_down = scale_variation(events, mask, vals, w_nom, bins)
            fout[f"{cat}/mgg_scaleUp"]   = h_sc_up
            fout[f"{cat}/mgg_scaleDown"] = h_sc_down
