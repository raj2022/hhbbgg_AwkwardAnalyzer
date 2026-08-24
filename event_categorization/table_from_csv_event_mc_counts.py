import pandas as pd

df = pd.read_csv("/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/yields/signal_mc_counts_full_grid.csv")
df = df.sort_values(["mass_x", "mass_y", "category"]).reset_index(drop=True)

lines = []
lines.append(r"% Category-level MC yields per (m_X, m_Y) signal mass point.")
lines.append(r"% Auto-generated from category_yields.csv -- do not edit rows by hand,")
lines.append(r"% regenerate from the CSV if the underlying ntuples change.")
lines.append(r"\begin{center}")
lines.append(r"\footnotesize")
lines.append(r"\begin{longtable}{c c c r r}")
lines.append(r"\caption{Number of raw simulated events and weighted event yields per analysis")
lines.append(r"category, for each generated $(m_X, m_Y)$ signal mass point. Categories are")
lines.append(r"labeled by index in order of decreasing purity (Category 0 = most signal-like);")
lines.append(r"the total number of categories used at a given mass point can vary.}")
lines.append(r"\label{tab:category_yields_full}\\")
lines.append(r"\toprule")
lines.append(r"$m_X$ [GeV] & $m_Y$ [GeV] & Category & Raw MC events & Weighted yield \\")
lines.append(r"\midrule")
lines.append(r"\endfirsthead")
lines.append(r"")
lines.append(r"\multicolumn{5}{c}{\tablename\ \thetable\ -- continued from previous page}\\")
lines.append(r"\toprule")
lines.append(r"$m_X$ [GeV] & $m_Y$ [GeV] & Category & Raw MC events & Weighted yield \\")
lines.append(r"\midrule")
lines.append(r"\endhead")
lines.append(r"")
lines.append(r"\midrule")
lines.append(r"\multicolumn{5}{r}{\textit{Continued on next page}}\\")
lines.append(r"\endfoot")
lines.append(r"")
lines.append(r"\bottomrule")
lines.append(r"\endlastfoot")
lines.append(r"")

prev_key = None
for _, row in df.iterrows():
    key = (row["mass_x"], row["mass_y"])
    if prev_key is not None and key != prev_key:
        lines.append(r"\midrule")
    if key != prev_key:
        mx_cell = f"{int(row['mass_x'])}"
        my_cell = f"{int(row['mass_y'])}"
    else:
        mx_cell = ""
        my_cell = ""
    cat = int(row["category"])
    raw = int(row["raw_mc_events"])
    wyield = row["weighted_yield"]
    lines.append(f"{mx_cell} & {my_cell} & {cat} & {raw:,} & {wyield:,.2f} \\\\")
    prev_key = key

lines.append(r"\end{longtable}")
lines.append(r"\end{center}")

with open("/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/yields/category_yields_table.tex", "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"Wrote {len(df)} data rows across {df.groupby(['mass_x','mass_y']).ngroups} mass points.")