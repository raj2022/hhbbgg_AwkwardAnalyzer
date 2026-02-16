#!/usr/bin/env python3
import argparse
import os
import sys
import ROOT

ROOT.gROOT.SetBatch(True)

# Your 9 b-tag systematics
SYSTS = [
    "bTagSF_sys_hf",
    "bTagSF_sys_lf",
    "bTagSF_sys_hfstats1",
    "bTagSF_sys_hfstats2",
    "bTagSF_sys_lfstats1",
    "bTagSF_sys_lfstats2",
    "bTagSF_sys_cferr1",
    "bTagSF_sys_cferr2",
    "bTagSF_sys_jes",
]

# ---------------- CMS style ----------------
def set_cms_style():
    ROOT.gStyle.SetOptStat(0)
    ROOT.gStyle.SetPadTickX(1)
    ROOT.gStyle.SetPadTickY(1)
    ROOT.gStyle.SetFrameLineWidth(2)
    ROOT.gStyle.SetHistLineWidth(2)

def cms_label(pad, extra="Preliminary"):
    pad.cd()
    latex = ROOT.TLatex()
    latex.SetNDC(True)
    latex.SetTextFont(62)
    latex.SetTextSize(0.05)
    latex.DrawLatex(0.16, 0.92, "CMS")
    latex.SetTextFont(52)
    latex.SetTextSize(0.05)
    latex.DrawLatex(0.27, 0.92, extra)


    # ---------------- Helpers ----------------
def build_path(base, sel, weight_dir, hist):
    return f"{base}/{sel}/{weight_dir}/{hist}"

def get_hist(f, path):
    obj = f.Get(path)
    if not obj:
        raise RuntimeError(f"Missing: {path}")
    if not isinstance(obj, ROOT.TH1):
        raise RuntimeError(f"Not TH1: {path}")
    h = obj.Clone(path.replace("/", "_"))
    h.SetDirectory(0)
    h.Sumw2()
    return h

def make_ratio_hist(num, den, name):
    """
    Return a ratio hist num/den, but if den bin is 0 (or non-finite),
    force ratio = 1 and error = 0 (per your request).
    Also if both num and den are 0, ratio is set to 1.
    """
    r = num.Clone(name)
    r.Reset("ICES")  # reset contents/errors
    r.Sumw2()

    for b in range(1, den.GetNbinsX() + 1):
        d = den.GetBinContent(b)
        n = num.GetBinContent(b)
        #print("denum {} and num is {}".format(d,n))
        #if d == 0: 
        #    print("n/d is {}".format(rat))
        if d == 0 or (not ROOT.TMath.Finite(d)) or (not ROOT.TMath.Finite(n)):
            r.SetBinContent(b, 1.0)
            r.SetBinError(b, 0.0)
        else:
            r.SetBinContent(b, n / d)
            r.SetBinError(b, 0.0) 
        return r

def auto_ratio_range(hists, pad_frac=0.10, min_half_range=0.10, hard_min=0.0, hard_max=5.0):
    """
    Compute y-range from a list of ratio hists.
    pad_frac: fractional padding on min/max (10% default)
    min_half_range: enforce at least [1-min_half_range, 1+min_half_range]
    hard_min/max: safety clamp
    """
    vals = []
    for h in hists:
        for b in range(1, h.GetNbinsX() + 1):
            v = h.GetBinContent(b)
            if ROOT.TMath.Finite(v):
                vals.append(v)

    if not vals:
        return (1.0 - min_half_range, 1.0 + min_half_range)

    vmin = min(vals)
    vmax = max(vals)

    # Add padding
    span = max(1e-6, vmax - vmin)
    vmin -= pad_frac * span
    vmax += pad_frac * span

    # Ensure at least a symmetric range around 1
    vmin = min(vmin, 1.0 - min_half_range)
    vmax = max(vmax, 1.0 + min_half_range)

    # Clamp to hard bounds
    vmin = max(hard_min, vmin)
    vmax = min(hard_max, vmax)

    return (vmin, vmax)

def draw_cms_header(pad, year="2022postEE", lumi="26.67", energy="13.6",
                    extra="Work in Progress"):
    pad.cd()

    lm = pad.GetLeftMargin()
    rm = pad.GetRightMargin()
    tm = pad.GetTopMargin()

    # Place text in the TOP MARGIN (not inside the frame)
    y = 1.0 - tm/2.0

    # Left: CMS + extra
    cms = ROOT.TLatex()
    cms.SetNDC(True)
    cms.SetTextAlign(13)      # left, center vertically
    cms.SetTextFont(61)
    cms.SetTextSize(0.05)
    cms.DrawLatex(lm, y, "CMS")

    extra_t = ROOT.TLatex()
    extra_t.SetNDC(True)
    extra_t.SetTextAlign(13)
    extra_t.SetTextFont(52)
    extra_t.SetTextSize(0.035)
    extra_t.DrawLatex(lm + 0.079, y-0.009, extra)

    # Right: year + lumi + energy
    right = ROOT.TLatex()
    right.SetNDC(True)
    right.SetTextAlign(33)    # right, center vertically (top-right-ish)
    right.SetTextFont(42)
    right.SetTextSize(0.035)
    right.DrawLatex(1.0 - rm, y, f"{year} {lumi} fb^{{-1}} ({energy} TeV)")
    pad._cms_objects = [cms, extra_t, right]

# ---------------- Plot per systematic ----------------
#def draw_one_systematic(outdir, outbase, syst, h_nom, h_up, h_dn, cms_extra):
def draw_one_systematic(outdir, outbase, syst, h_nom, h_up, h_dn,
                        cms_extra, year, lumi, energy):
    c = ROOT.TCanvas(f"c_{syst}", syst, 1300, 1300)

    #pad1 = ROOT.TPad("pad1","pad1",0,0.30,1,1)
    pad1 = ROOT.TPad("pad1","pad1",0,0.25,1,1)
    pad1.SetFillColor(0)
    pad1.SetBorderMode(0)
    pad1.SetBorderSize(1)
    pad1.SetTickx(1)
    pad1.SetTicky(1)
    #pad1.SetGridx()
    pad1.SetLeftMargin(0.15) #0.15
    pad1.SetRightMargin(0.15) #0.1
    pad1.SetTopMargin(0.122)
    pad1.SetBottomMargin(0.025)
    pad1.SetFrameFillStyle(0)
    pad1.SetFrameLineStyle(0)
    pad1.SetFrameLineWidth(1)
    pad1.SetFrameBorderMode(0)
    pad1.SetFrameBorderSize(1)


    #pad2 = ROOT.TPad("pad2","pad2",0,0,1,0.30)
    pad2 = ROOT.TPad("pad2","pad2",0,0,1,0.25);
    pad2.SetTopMargin(0.02);
    pad2.SetBottomMargin(0.35);
    pad2.SetLeftMargin(0.15);
    pad2.SetRightMargin(0.15);
    pad2.SetTickx(1)
    pad2.SetTicky(1)
    pad2.SetFrameLineWidth(1)

    pad1.Draw()
    pad2.Draw()

    # =========================
    # PAD1 — DrawNormalized()
    # =========================
    pad1.cd()

    h_nom.SetLineColor(ROOT.kBlue)
    h_dn.SetLineColor(ROOT.kRed+1)
    h_up.SetLineColor(ROOT.kOrange+1)

    h_nom.SetLineWidth(3)
    h_up.SetLineWidth(3)
    h_dn.SetLineWidth(3)

    h_nom.SetTitle("")
    h_nom.GetYaxis().SetTitle("")
    h_nom.GetXaxis().SetLabelSize(0)

    xmin, xmax = 0, 200
    for h in [h_nom, h_up, h_dn]:
        h.GetXaxis().SetRangeUser(xmin, xmax)


    # Use DrawNormalized directly
    h_nom.DrawNormalized("HIST")
    h_up.DrawNormalized("HIST SAME")
    h_dn.DrawNormalized("HIST SAME")
    draw_cms_header(pad1,
                    year=year,
                    lumi=lumi,
                    energy=energy,
                    extra=cms_extra)    

    leg = ROOT.TLegend(0.2, 0.7, 0.5, 0.85)
    #leg = ROOT.TLegend(0.58,0.70,0.93,0.88)
    #leg = ROOT.TLegend(0.18, 0.62, 0.50, 0.80)
    #leg = ROOT.TLegend(0.60, 0.62, 0.92, 0.80)

    leg.SetBorderSize(0)
    leg.SetFillStyle(0)
    leg.AddEntry(h_nom,"Nominal","l")
    leg.AddEntry(h_up,f"{syst} Up","l")
    leg.AddEntry(h_dn,f"{syst} Down","l")
    leg.Draw("SAME")

    c._legend = leg
    #cms_label(pad1, cms_extra)
    """
    pretty = syst.replace("bTagSF_sys_", "bTagSF ")
    t = ROOT.TLatex()
    t.SetNDC(True)
    t.SetTextFont(42)
    t.SetTextSize(0.042)
    t.DrawLatex(0.16, 0.86, pretty)
    """

    # =========================
    # PAD2 — ratios
    # =========================
    pad2.cd()


    #r_nm = make_ratio_hist(h_nom, h_nom, "r_nm")  # will be exactly 1
    #r_up = make_ratio_hist(h_up,  h_nom, "r_up")  # up/nom, but denom=0 -> 1
    #r_dn = make_ratio_hist(h_dn,  h_nom, "r_dn")  # down/nom, denom=0 -> 1

    r_up = h_up.Clone("r_up")
    r_dn = h_dn.Clone("r_dn")
    r_nm = h_nom.Clone("r_nm")


    print(syst)
    print("before dividing: ")
    for b in range(1, h_nom.GetNbinsX()+1):
        print("bin {} and r_up getbin {}".format(b,r_up.GetBinContent(b)))
        print("r_nm getbin ",r_nm.GetBinContent(b))
        print("r_dn getbin ",r_dn.GetBinContent(b))
        
    # reset contents
    r_up.Reset("ICES")
    r_dn.Reset("ICES")
    r_nm.Reset("ICES")
    

    print("After divideing   ")
    for b in range(1, h_nom.GetNbinsX()+1):
        nom = h_nom.GetBinContent(b)
        up  = h_up.GetBinContent(b)
        dn  = h_dn.GetBinContent(b)
        
        # case 1: nominal bin empty → define ratio = 1
        if nom == 0:
            r_up.SetBinContent(b, 1.0)
            r_dn.SetBinContent(b, 1.0)
            r_nm.SetBinContent(b, 1.0)
            continue

        # normal ratio
        r_up.SetBinContent(b, up/nom)
        r_dn.SetBinContent(b, dn/nom)
        r_nm.SetBinContent(b, 1.0)
        print("bin {} and r_up getbin {} ".format(b,r_up.GetBinContent(b)))
        print("r_nm getbin ",r_nm.GetBinContent(b))
        print("r_dn getbin ",r_dn.GetBinContent(b))
    ymin, ymax = auto_ratio_range([r_up, r_dn], pad_frac=0.10, min_half_range=0.08)
    #r_nm.SetMinimum(0.5)
    #r_nm.SetMaximum(1.5)

    r_nm.SetMinimum(ymin)
    r_nm.SetMaximum(ymax)
    
    
    r_nm.SetTitle("")
    r_nm.GetYaxis().SetTitle("Ratio")


    r_nm.GetYaxis().SetTitleSize(0.11)
    r_nm.GetYaxis().SetLabelSize(0.07)
    r_nm.GetYaxis().SetTitleOffset(0.5)
    r_nm.GetYaxis().SetNdivisions(5)
    #r_nm.GetXaxis().SetTitle("bbgg mass [GeV]")
    #r_nm.GetXaxis().SetTitle("m_{#gamma#gamma} [GeV]")
    r_nm.GetXaxis().SetTitle("m_{dibjet} [GeV]")
    #r_nm.GetXaxis().SetTitle(h_nom.GetXaxis().GetTitle())
    r_nm.GetXaxis().SetTitleSize(0.13)
    r_nm.GetXaxis().SetLabelSize(0.11)
    r_nm.GetXaxis().SetTitleOffset(1.15)
    #r_nm.GetXaxis().SetRangeUser(110,150)
    r_nm.GetXaxis().SetRangeUser(xmin, xmax)
    #r_nm.SetMinimum(0.5)
    #r_nm.SetMaximum(1.5)

    # draw as lines (no bars)
    r_nm.SetLineColor(ROOT.kBlack)
    r_dn.SetLineColor(ROOT.kRed+1)
    r_up.SetLineColor(ROOT.kOrange+1)
    
    r_nm.Draw("HIST")
    r_up.Draw("HIST SAME")
    r_dn.Draw("HIST SAME")
    
    #line = ROOT.TLine(r_nm.GetXaxis().GetXmin(),1,
    #              r_nm.GetXaxis().GetXmax(),1)

    line = ROOT.TLine(xmin, 1.0, xmax, 1.0)
    line.SetLineStyle(2)
    line.Draw()

    c.Modified()
    c.Update()
    # save png
    os.makedirs(outdir, exist_ok=True)
    c.SaveAs(f"{outdir}/{outbase}__{syst}.png")

    return c


# ---------------- main ----------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i","--input", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--sel", required=True)
    parser.add_argument("--hist", required=True)
    parser.add_argument("--nom_weight", default="weight")
    parser.add_argument("-o","--out", default="syst_plots")
    parser.add_argument("--outdir", default="pngs")
    #parser.add_argument("--cms_extra", default="Preliminary")
    parser.add_argument("--pdfdir", default="pdfs")
    parser.add_argument("--year", default="2022postEE")
    parser.add_argument("--lumi", default="26.67")
    parser.add_argument("--energy", default="13.6")
    parser.add_argument("--cms_extra", default="Work in Progress")
    args = parser.parse_args()

    set_cms_style()

    f = ROOT.TFile.Open(args.input)

    # Nominal histogram
    nom_path = build_path(args.base,args.sel,args.nom_weight,args.hist)
    h_nom = get_hist(f, nom_path)

    
    os.makedirs(args.pdfdir, exist_ok=True)

    
    for syst in SYSTS:
        up_dir = f"weight_{syst}Up"
        dn_dir = f"weight_{syst}Down"

        try:
            h_up = get_hist(f, build_path(args.base,args.sel,up_dir,args.hist))
            h_dn = get_hist(f, build_path(args.base,args.sel,dn_dir,args.hist))
        except:
            print(f"Skipping {syst} (missing)")
            continue

        #c = draw_one_systematic(args.outdir,args.out,syst,h_nom,h_up,h_dn,args.cms_extra)

        c = draw_one_systematic(args.outdir, args.out, syst,
                        h_nom, h_up, h_dn,
                        args.cms_extra, args.year, args.lumi, args.energy)
        pdf_one = f"{args.pdfdir}/{args.out}__{syst}.pdf"
        
        c.SaveAs(pdf_one)

    print("All systematics plotted.")


if __name__ == "__main__":
    main()
