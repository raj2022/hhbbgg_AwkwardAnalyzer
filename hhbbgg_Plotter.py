# # %%
# import os
# #os.environ['MPLCONFIGDIR'] = '/uscms_data/d1/sraj/matplotlib_tmp' #Disk quota error fix for shivam on lpc
# import matplotlib

# matplotlib.use("Agg")
# import uproot
# from hist import Hist, Stack
# import numpy as np
# import matplotlib.pyplot as plt
# import mplhep as hep
# from normalisation import getLumi
# from cycler import cycler

# # Load CMS style including color-scheme
# hep.style.use("CMS")
# plt.rcParams["axes.prop_cycle"] = cycler(
#     color=[
#         "#3f90da",
#         "#ffa90e",
#         "#bd1f01",
#         "#94a4a2",
#         "#832db6",
#         "#a96b59",
#         "#e76300",
#         "#b9ac70",
#         "#717581",
#         "#92dadd",
#     ]
# )


# # Function to read histograms
# def get_histogram(file_name, hist_name, hist_label=None):
#     histogram = Hist(file_name[hist_name])
#     if hist_label is not None:
#         histogram.name = hist_label
#     return histogram


# # Function to read and sum histograms
# def sum_histograms(histograms):
#     return sum(histograms)


# # Function to blind data
# def blind_data(hist, blind, start_blind=122, stop_blind=128):
#     if blind:
#         blinded_hist = hist.copy()
#         for bin in range(blinded_hist.axes[0].size):
#             bin_center = blinded_hist.axes[0].centers[bin]
#             if bin_center >= start_blind and bin_center <= stop_blind:
#                 blinded_hist[bin] = 0.0
#         return blinded_hist
#     else:
#         return hist


# # Function to return histogram ratio
# def get_ratio(hist_a, hist_b):
#     # Extract the bin edges and contents
#     edges_a = hist_a.axes.edges[0]
#     edges_b = hist_b.axes.edges[0]
#     if not np.array_equal(edges_a, edges_b):
#         raise ValueError("Histograms have different binning")

#     # Extract the counts
#     counts_a = np.where(hist_a.values() < 0.0, 0.0, hist_a.values())
#     counts_b = np.where(hist_b.values() < 0.0, 0.0, hist_b.values())

#     # Compute the errors for each histogram
#     errors_a = np.sqrt(counts_a)  # Assuming Poisson statistics
#     errors_b = np.sqrt(counts_b)  # Assuming Poisson statistics

#     # Compute the ratio with handling of division by zero
#     ratio_counts = np.divide(
#         counts_a,
#         counts_b,
#         out=np.zeros_like(counts_a, dtype=float),
#         where=counts_b != 0,
#     )
#     ratio_hist = Hist(hist_a.axes[0])
#     ratio_hist[...] = ratio_counts

#     # Compute the relative errors
#     with np.errstate(divide="ignore", invalid="ignore"):
#         relative_errors_a = np.divide(
#             errors_a,
#             counts_a,
#             out=np.zeros_like(errors_a, dtype=float),
#             where=counts_a != 0,
#         )
#         relative_errors_b = np.divide(
#             errors_b,
#             counts_b,
#             out=np.zeros_like(errors_b, dtype=float),
#             where=counts_b != 0,
#         )
#     # Propagate the errors for the ratio
#     ratio_errors = ratio_counts * np.sqrt(relative_errors_a**2 + relative_errors_b**2)

#     return ratio_hist, ratio_errors


# # List of new variables to blind
# blind_vars = [
#     "dibjet_mass",
#     "diphoton_mass",
# ]


# def stack1d_histograms(
#     uproot_loaded_filename,
#     data_samples,
#     mc_samples,
#     signal_samples,
#     histogram_names,
#     legend_dict,
#     xtitle_dict,
#     output_directory,
#     blind=True,
# ):
#     for hist_name in histogram_names:
#         # Determine size based on number of MC samples or histogram width
#         dynamic_width = max(11, len(mc_samples) * 1.5)  # Adjust width based on MC samples
#         dynamic_height = 12  # Default height
#         fig, (ax, ax_ratio) = plt.subplots(
#             2, 1,
#             figsize=(dynamic_width, dynamic_height),
#             gridspec_kw={"height_ratios": [3, 1]},
#             sharex=True
#         )
#         #fig, (ax, ax_ratio) = plt.subplots(
#         #    2, 1, gridspec_kw={"height_ratios": [3, 1]}, sharex=True
#         #)
#         fig.subplots_adjust(
#             hspace=0.05
#         )  # Adjust space between main plot and ratio plot

#         # Plot data histogram
#         data_histogram = sum_histograms(
#             [
#                 get_histogram(uproot_loaded_filename, f"{data_sample}/{hist_name}")
#                 for data_sample in data_samples
#             ]
#         )
#         if any(keyword in hist_name for keyword in blind_vars):
#             blinded_data_histogram = blind_data(
#                 data_histogram, blind, start_blind=110, stop_blind=130
#             )
#             yerrors = np.sqrt(blinded_data_histogram.to_numpy()[0])
#             blinded_data_histogram.plot(
#                 ax=ax,
#                 stack=False,
#                 histtype="errorbar",
#                 yerr=yerrors,
#                 xerr=True,
#                 color="black",
#                 label="Data",
#                 flow="sum",
#             )
#         else:
#             data_histogram.plot(
#                 ax=ax,
#                 stack=False,
#                 histtype="errorbar",
#                 yerr=True,
#                 xerr=True,
#                 color="black",
#                 label="Data",
#                 flow="sum",
#             )

#         # Plot MC histograms as stack
#         mc_stack = Stack(
#             *[
#                 get_histogram(
#                     uproot_loaded_filename,
#                     f"{mc_sample}/{hist_name}",
#                     legend_dict[mc_sample],
#                 )
#                 for mc_sample in mc_samples
#             ]
#         )
#         mc_stack.plot(ax=ax, stack=True, histtype="fill", flow="sum", sort="yield")

#         # Plot signal histograms
#         #        if "srbbgg" in hist_name or "srbbggMET" in hist_name:
#         #            for signal_sample in signal_samples:
#         #                signal_histogram = get_histogram(
#         #                    uproot_loaded_filename, f"{signal_sample}/{hist_name}"
#         #                )
#         #                signal_histogram.plot(
#         #                    ax=ax,
#         #                    histtype="step",
#         #                    yerr=True,
#         #                    xerr=True,
#         #                    label=legend_dict[signal_sample],
#         #                    color="red",
#         #                )
#         #
#         #            region_name = r'sr: $b\bar{b}\gamma\gamma$' if "srbbgg" in hist_name else r'sr: $b\bar{b}\gamma\gamma$(MET)'
#         #
#         #            ax.text(
#         #            x=ax.get_xlim()[0] + 0.05 * (ax.get_xlim()[1] - ax.get_xlim()[0]),
#         #            # y=ax.get_ylim()[1] - 0.05 * (ax.get_ylim()[1] - ax.get_ylim()[0]),
#         #            y = 1e8*0.20,
#         #            s=region_name,
#         #            fontsize=25,
#         #            ha='left',
#         #            va='top',
#         #            bbox=dict(facecolor='white', alpha=1)
#         #             )
#         #
#         #        # for control regions
#         #        if "crantibbgg" in hist_name or "crbbantigg" in hist_name:
#         #            region_name = r'cr: anti$b\bar{b}\gamma\gamma$' if "crantibbgg" in hist_name else r'cr: $b\bar{b}anti\gamma\gamma$'
#         #
#         #            ax.text(
#         #            x=ax.get_xlim()[0] + 0.05 * (ax.get_xlim()[1] - ax.get_xlim()[0]),
#         #            # y=ax.get_ylim()[1] - 0.05 * (ax.get_ylim()[1] - ax.get_ylim()[0]),
#         #            y = 1e8*0.20,
#         #            s=region_name,
#         #            fontsize=20,
#         #            ha='left',
#         #            va='top',
#         #            bbox=dict(facecolor='white', alpha=1)
#         #             )
#         #

#         text_srbbgg = "Pass medium Btag\nPass tight photonID "
#         text_srbbggMET = "Pass medium Btag\nPass tight photonID"
#         text_crantibbgg = "Fail Medium Btag\nPass tight photonID"
#         text_crbbantigg = "Pass Medium Btag\nPass loose photonID\nfail tight photonID "
#         text_crantibbantigg = "Fail Medium Btag\nFail loose photonID\nfail tight photonID " 
#         text_sideband = "Fail Medium Btag\nFail loose photonID\nfail tight photonID " 
        
        
#         if "srbbgg" in hist_name:
#             region_name = r"sr: $b\bar{b}\gamma\gamma$"
#             additional_text = text_srbbgg
#         elif "srbbggMET" in hist_name:
#             region_name = r"sr: $b\bar{b}\gamma\gamma$+MET"
#             additional_text = text_srbbggMET
#         elif "crantibbgg" in hist_name:
#             region_name = r"cr: anti$b\bar{b}\gamma\gamma$"
#             additional_text = text_crantibbgg
#         elif "crbbantigg" in hist_name:
#             region_name = r"cr: $b\bar{b}anti\gamma\gamma$"
#             additional_text = text_crbbantigg
#         elif "crantibbantigg" in hist_name:
#             region_name = r"cr: anti$b\bar{b}anti\gamma\gamma$"
#             additional_text = text_crantibbantigg
#         elif "sideband" in hist_name:
#             region_name = r"cr: anti$b\bar{b}anti\gamma\gamma$"
#             additional_text = text_sideband
#         else:
#             region_name = None
#             additional_text = None

#         if region_name and additional_text:
#             combined_text = f"{region_name}\n{additional_text}"
#             ax.text(
#                 x=ax.get_xlim()[0] + 0.02 * (ax.get_xlim()[1] - ax.get_xlim()[0]),
#                 y=1e8 * 0.20,
#                 s=combined_text,
#                 fontsize=15,
#                 ha="left",
#                 va="top",
#                 bbox=dict(facecolor="white", alpha=1, edgecolor="none"),
#             )

#         # plot signal histogram
#         if "srbbgg" in hist_name or "srbbggMET" in hist_name:
#             for signal_sample in signal_samples:
#                 signal_histogram = get_histogram(
#                     uproot_loaded_filename, f"{signal_sample}/{hist_name}"
#                 )
#                 signal_histogram.plot(
#                     ax=ax,
#                     histtype="step",
#                     yerr=True,
#                     xerr=True,
#                     label=legend_dict[signal_sample],
#                     color="red",
#                 )

#         # Plot ratio plot
#         ratio, error = get_ratio(data_histogram, sum_histograms(mc_stack))
#         if "dibjet_mass" in hist_name or "diphoton_mass" in hist_name:
#             blinded_ratio = blind_data(ratio, blind, start_blind=110, stop_blind=130)
#             blinded_ratio.plot(
#                 ax=ax_ratio,
#                 histtype="errorbar",
#                 yerr=error,
#                 xerr=True,
#                 color="black",
#                 flow="sum",
#             )
#         else:
#             ratio.plot(
#                 ax=ax_ratio,
#                 histtype="errorbar",
#                 yerr=error,
#                 xerr=True,
#                 color="black",
#                 flow="sum",
#             )
#         ax_ratio.axhline(1, linestyle="--", color="gray")
#         ax_ratio.set_ylim(0, 3)
#         ax_ratio.set_ylabel("Data / MC")

#         # Style
#         # x_axis_bining = data_histogram.axes.edges[0]
#         # ax.set_xlim(min(x_axis_bining), max(x_axis_bining))
#         ax.set_yscale("log")
#         ax.set_ylim(0.1, 1e8)
#         ax.set_xlabel("")
#         ax.set_ylabel("Events")
#         hep.cms.label(
#             "",
#             ax=ax,
#             lumi="{0:.2f}".format(getLumi()),
#             loc=0,
#             llabel="Work in progress",
#             com=13.6,
#         )
#         ax.legend(ncol=2, loc="upper right", fontsize=18)
#         ax_ratio.set_xlabel(xtitle_dict[hist_name.split("-")[-1]])
#         ax_ratio.set_ylabel("Data/MC")

#         # Save plots
#         plot_reg_name = hist_name.split("-")[0]
#         # check and create plot directory
#         if not os.path.exists(f"{output_directory}/{plot_reg_name}"):
#             os.makedirs(f"{output_directory}/{plot_reg_name}")
#         plot_var_name = hist_name.split("-")[-1]
#         plt.tight_layout()     # Adding to ensure everything is well-spaced
#         plt.savefig(
#             f"{output_directory}/{plot_reg_name}/{plot_var_name}.pdf",
#             bbox_inches="tight",
#         )
#         plt.savefig(
#             f"{output_directory}/{plot_reg_name}/{plot_var_name}.png",
#             bbox_inches="tight",
#         )
#         plt.close()
#         print(f"{hist_name} has been plotted")


# def main():
#     # Open the ROOT file
#     file_path = "outputfiles/merged/CombinedAll/hhbbgg_analyzer-v2-histograms.root"
#     uproot_loaded_filename = uproot.open(file_path)

#     # List of data histograms
#     data_samples = ["Data_EraE", "Data_EraF", "Data_EraG"]

#     # List of MC processes
#     mc_samples = [
#         "GGJets",
#         "GJetPt20To40",
#         "GJetPt40",
#         "GluGluHToGG",
#         "VBFHToGG",
#         "VHToGG",
#         "ttHToGG",
#         # "QCD_PT-30to40",
#         # "QCD_PT-30toInf",
#         # "QCD_PT-40toInf",
#         "DDQCDGJET",
#     ]

#     # List of signal processes
#     signal_samples = [
#         #"GluGluToHH",
#         "NMSSM_X400_Y100",
#         "NMSSM_X400_Y125",
#         "NMSSM_X400_Y150",
#         "NMSSM_X500_Y100",
#         "NMSSM_X500_Y125",
#         "NMSSM_X500_Y150",
#      ]

#     #signal_samples = [
#     #    "GluGluToHH",
#     #    "NMSSM_X300_Y60",
#     #    "NMSSM_X300_Y70",
#     #    "NMSSM_X300_Y80",
#     #    "NMSSM_X300_Y90",
#     #    "NMSSM_X300_Y95",
#     #    "NMSSM_X300_Y100",
#     #    "NMSSM_X300_Y125",
#     #    "NMSSM_X400_Y60",
#     #    "NMSSM_X400_Y70",
#     #    "NMSSM_X400_Y80",
#     #    "NMSSM_X400_Y90",
#     #    "NMSSM_X400_Y95",
#     #    "NMSSM_X400_Y100",
#     #    "NMSSM_X400_Y125",
#     #    "NMSSM_X500_Y60",
#     #    "NMSSM_X500_Y70",
#     #    "NMSSM_X500_Y80",
#     #    "NMSSM_X500_Y90",
#     #    "NMSSM_X500_Y95",
#     #    "NMSSM_X500_Y100",
#     #    "NMSSM_X500_Y125",
#     #    "NMSSM_X550_Y60",
#     #    "NMSSM_X550_Y70",
#     #    "NMSSM_X550_Y80",
#     #    "NMSSM_X550_Y90",
#     #    "NMSSM_X550_Y95",
#     #    "NMSSM_X550_Y100",
#     #    "NMSSM_X550_Y125",
#     #    "NMSSM_X600_Y60",
#     #    "NMSSM_X600_Y70",
#     #    "NMSSM_X600_Y80",
#     #    "NMSSM_X600_Y90",
#     #    "NMSSM_X600_Y95",
#     #    "NMSSM_X600_Y100",
#     #    "NMSSM_X600_Y125",
#     #    "NMSSM_X650_Y60",
#     #    "NMSSM_X650_Y70",
#     #    "NMSSM_X650_Y80",
#     #    "NMSSM_X650_Y90",
#     #    "NMSSM_X650_Y95",
#     #    "NMSSM_X650_Y100",
#     #    "NMSSM_X650_Y125",
#     #    "NMSSM_X700_Y60",
#     #    "NMSSM_X700_Y70",
#     #    "NMSSM_X700_Y80",
#     #    "NMSSM_X700_Y90",
#     #    "NMSSM_X700_Y95",
#     #    "NMSSM_X700_Y100",
#     #    "NMSSM_X700_Y125"
#     #]

#     # Dictionary for legends
#     legend_dict = {
#         "GGJets": r"$\gamma\gamma$+jets",
#         "GJetPt20To40": r"$\gamma$+jets ($20< p_T < 40$)",
#         "GJetPt40": r"$\gamma$+jets ($p_T > 40$)",
#         "GluGluHToGG": r"$gg\rightarrow\,H\rightarrow\gamma\gamma$",
#         "VBFHToGG": r"$VBF\:H\rightarrow\gamma\gamma$",
#         "VHToGG": r"$V\:H\rightarrow\gamma\gamma$",
#         "ttHToGG": r"$t\bar{t}H\rightarrow\gamma\gamma$",
#         #"GluGluToHH": r"$gg\rightarrow\,HH$ \times 10",
#         "NMSSM_X400_Y100": r"$NMSSM\_X_{400}\_Y_{100} \times 10$",
#         "NMSSM_X400_Y125": r"$NMSSM\_X_{400}\_Y_{125} \times 10$",
#         "NMSSM_X400_Y150": r"$NMSSM\_X_{400}\_Y_{150} \times 10$",
#         "NMSSM_X500_Y100": r"$NMSSM\_X_{500}\_Y_{100} \times 10$",
#         "NMSSM_X500_Y125": r"$NMSSM\_X_{500}\_Y_{125} \times 10$",
#         "NMSSM_X500_Y150": r"$NMSSM\_X_{500}\_Y_{150} \times 10$",
#         # QCD sample legends
#         # "QCD_PT-30to40": r"$QCD+P_T(30to40)$",
#         # "QCD_PT-30toInf": r"$QCD+P_T(30toInf)$",
#         # "QCD_PT-40toInf": r"$QCD+P_T(40toInf)$",
#         "DDQCDGJET": r"DD QCD",
#         # NMSSM samples legends
#         #"NMSSM_X300_Y60": r"$NMSSM\_X300\_Y60$",
#         #"NMSSM_X300_Y70": r"$NMSSM\_X300\_Y70$",
#         #"NMSSM_X300_Y80": r"$NMSSM\_X300\_Y80$",
#         #"NMSSM_X300_Y90": r"$NMSSM\_X300\_Y90$",
#         #"NMSSM_X300_Y95": r"$NMSSM\_X300\_Y95$",
#         #"NMSSM_X300_Y100": r"$NMSSM\_X300\_Y100$",
#         #"NMSSM_X300_Y125": r"$NMSSM\_X300\_Y125$",
#         #"NMSSM_X400_Y60": r"$NMSSM\_X400\_Y60$",
#         #"NMSSM_X400_Y70": r"$NMSSM\_X400\_Y70$",
#         #"NMSSM_X400_Y80": r"$NMSSM\_X400\_Y80$",
#         #"NMSSM_X400_Y90": r"$NMSSM\_X400\_Y90$",
#         #"NMSSM_X400_Y95": r"$NMSSM\_X400\_Y95$",
#         #"NMSSM_X400_Y100": r"$NMSSM\_X400\_Y100$",
#         #"NMSSM_X400_Y125": r"$NMSSM\_X400\_Y125$",
#         #"NMSSM_X500_Y60": r"$NMSSM\_X500\_Y60$",
#         #"NMSSM_X500_Y70": r"$NMSSM\_X500\_Y70$",
#         #"NMSSM_X500_Y80": r"$NMSSM\_X500\_Y80$",
#         #"NMSSM_X500_Y90": r"$NMSSM\_X500\_Y90$",
#         #"NMSSM_X500_Y95": r"$NMSSM\_X500\_Y95$",
#         #"NMSSM_X500_Y100": r"$NMSSM\_X500\_Y100$",
#         #"NMSSM_X500_Y125": r"$NMSSM\_X500\_Y125$",
#         #"NMSSM_X550_Y60": r"$NMSSM\_X550\_Y60$",
#         #"NMSSM_X550_Y70": r"$NMSSM\_X550\_Y70$",
#         #"NMSSM_X550_Y80": r"$NMSSM\_X550\_Y80$",
#         #"NMSSM_X550_Y90": r"$NMSSM\_X550\_Y90$",
#         #"NMSSM_X550_Y95": r"$NMSSM\_X550\_Y95$",
#         #"NMSSM_X550_Y100": r"$NMSSM\_X550\_Y100$",
#         #"NMSSM_X550_Y125": r"$NMSSM\_X550\_Y125$",
#         #"NMSSM_X600_Y60": r"$NMSSM\_X600\_Y60$",
#         #"NMSSM_X600_Y70": r"$NMSSM\_X600\_Y70$",
#         #"NMSSM_X600_Y80": r"$NMSSM\_X600\_Y80$",
#         #"NMSSM_X600_Y90": r"$NMSSM\_X600\_Y90$",
#         #"NMSSM_X600_Y95": r"$NMSSM\_X600\_Y95$",
#         #"NMSSM_X600_Y100": r"$NMSSM\_X600\_Y100$",
#         #"NMSSM_X600_Y125": r"$NMSSM\_X600\_Y125$",
#         #"NMSSM_X650_Y60": r"$NMSSM\_X650\_Y60$",
#         #"NMSSM_X650_Y70": r"$NMSSM\_X650\_Y70$",
#         #"NMSSM_X650_Y80": r"$NMSSM\_X650\_Y80$",
#         #"NMSSM_X650_Y90": r"$NMSSM\_X650\_Y90$",
#         #"NMSSM_X650_Y95": r"$NMSSM\_X650\_Y95$",
#         #"NMSSM_X650_Y100": r"$NMSSM\_X650\_Y100$",
#         #"NMSSM_X650_Y125": r"$NMSSM\_X650\_Y125$",
#         #"NMSSM_X700_Y60": r"$NMSSM\_X700\_Y60$",
#         #"NMSSM_X700_Y70": r"$NMSSM\_X700\_Y70$",
#         #"NMSSM_X700_Y80": r"$NMSSM\_X700\_Y80$",
#         #"NMSSM_X700_Y90": r"$NMSSM\_X700\_Y90$",
#         #"NMSSM_X700_Y95": r"$NMSSM\_X700\_Y95$",
#         #"NMSSM_X700_Y100": r"$NMSSM\_X700\_Y100$",
#         #"NMSSM_X700_Y125": r"$NMSSM\_X700\_Y125$",
#     }

#     # List of regions names
#     regions = [
#         "preselection",
#         "selection",
#         "srbbgg",
#         "srbbggMET",
#         "crantibbgg",
#         "crbbantigg",
#         "crantibbantigg",
#         "sideband",
#         "idmva_sideband",
#         "idmva_presel",
#     ]
#     # List of variable names
#     variable_names = [
#         "dibjet_mass",
#         "diphoton_mass",
#         "bbgg_mass",
#         "dibjet_pt",
#         "diphoton_pt",
#         "bbgg_pt",
#         "bbgg_eta",
#         "bbgg_phi",
#         "lead_pho_pt",
#         "sublead_pho_pt",
#         "dibjet_pt",
#         "lead_pho_eta",
#         "lead_pho_phi",
#         "sublead_pho_eta",
#         "sublead_pho_phi",
#         "dibjet_eta",
#         "dibjet_phi",
#         "diphoton_eta",
#         "diphoton_phi",
#         "lead_bjet_pt",
#         "sublead_bjet_pt",
#         "lead_bjet_eta",
#         "sublead_bjet_eta",
#         "lead_bjet_phi",
#         "sublead_bjet_phi",
#         "sublead_bjet_PNetB",
#         "lead_bjet_PNetB",
#         "CosThetaStar_gg",
#         "CosThetaStar_CS",
#         "CosThetaStar_jj",
#         "DeltaR_jg_min",
#         "pholead_PtOverM",
#         "phosublead_PtOverM",
#         "FirstJet_PtOverM",
#         "SecondJet_PtOverM",
#         "lead_pt_over_diphoton_mass",
#         "sublead_pt_over_diphoton_mass",
#         "lead_pt_over_dibjet_mass",
#         "sublead_pt_over_dibjet_mass",
#         "diphoton_bbgg_mass",
#         "dibjet_bbgg_mass",
#         "lead_pho_mvaID_WP90",
#         "lead_pho_mvaID_WP80",
#         "sublead_pho_mvaID_WP90",
#         "sublead_pho_mvaID_WP80",
#         "lead_pho_mvaID",
#         "sublead_pho_mvaID",
#     ]

#     specific_variable_names = [
#         "puppiMET_pt",
#         "puppiMET_phi",
#         "puppiMET_phiJERDown", "puppiMET_phiJERUp", "puppiMET_phiJESDown",
#         "puppiMET_phiJESUp", "puppiMET_phiUnclusteredDown",
#         "puppiMET_phiUnclusteredUp", "puppiMET_ptJERDown",
#         "puppiMET_ptJERUp", "puppiMET_ptJESDown",
#         "puppiMET_ptJESUp", "puppiMET_ptUnclusteredDown",
#         "puppiMET_ptUnclusteredUp", "puppiMET_sumEt"
#     ]

#     specific_regions = ["preselection","srbbggMET"]

#     histogram_names = [
#         f"{region}-{variable_name}"
#         for region in regions
#         for variable_name in variable_names
#     ]

#     specific_histogram_names = [
#         f"{specific_region}-{specific_variable_name}"
#         for specific_region in specific_regions
#         for specific_variable_name in specific_variable_names
#     ]

#     histogram_names = histogram_names + specific_histogram_names

#     # Dictionary for x-axis titles
#     xaxis_titles = {
#         "dibjet_mass": r"$m_{b\bar{b}}$ [GeV]",
#         "diphoton_mass": r"$m_{\gamma\gamma}$ [GeV]",
#         "bbgg_mass": r"$m_{b\bar{b}\gamma\gamma}$ [GeV]",
#         "lead_pho_pt": r"lead $p_T^{\gamma}$ [GeV]",
#         "sublead_pho_pt": r"sublead $p_T^{\gamma}$ [GeV]",
#         "dibjet_pt": r"$p_T^{b\bar{b}}$ [GeV]",
#         "diphoton_pt": r"$p_{T}^{\gamma\gamma}$ [GeV]",
#         "bbgg_pt": r"$p_T^{b\bar{b}\gamma\gamma}$ [GeV]",
#         "bbgg_eta": r"$\eta^{b\bar{b}\gamma\gamma}$",
#         "bbgg_phi": r"$\phi^{b\bar{b}\gamma\gamma}$",
#         "lead_pho_eta": r"lead $\eta^{\gamma}$",
#         "lead_pho_phi": r"lead $\phi^{\gamma}$",
#         "sublead_pho_eta": r"sublead $\eta^{\gamma}$",
#         "sublead_pho_phi": r"sublead $\phi^{\gamma}$",
#         "dibjet_eta": r"$\eta^{b\bar{b}}$",
#         "dibjet_phi": r"$\phi^{b\bar{b}}$",
#         "diphoton_eta": r"$\eta^{\gamma\gamma}$",
#         "diphoton_phi": r"$\phi^{\gamma\gamma}$",
#         "lead_bjet_pt": r"lead $p_T^{b}$ [GeV]",
#         "sublead_bjet_pt": r"sublead $p_T^{b}$ [GeV]",
#         "lead_bjet_eta": r"lead $\eta^{b}$",
#         "lead_bjet_phi": r"lead $\phi^{b}$",
#         "sublead_bjet_eta": r"sublead $\eta^{b}$",
#         "sublead_bjet_phi": r"sublead $\phi^{b}$",
#         "sublead_bjet_PNetB": r"sublead b PNetScore",
#         "lead_bjet_PNetB": r"lead b PNetScore",
#         "CosThetaStar_gg": r"$|Cos(\theta^{CS}_{gg})|$",
#         "CosThetaStar_jj": r"$|Cos(\theta^{CS}_{jj})|$",
#         "CosThetaStar_CS": r"$|Cos(\theta^{CS}_{HH})|$",
#         "DeltaR_jg_min": r"min($\Delta$R($\gamma$,jets))",
#         "pholead_PtOverM": r"lead $p_T^{\gamma1}/M_{\gamma\gamma}$",
#         "FirstJet_PtOverM": r"$p_T^{j1}/M_{jj}$",
#         "SecondJet_PtOverM": r"$p_T^{j2}/M_{jj})$",
#         "phosublead_PtOverM": r"sublead $p_T^{\gamma1}/M_{\gamma\gamma}$",
#         "lead_pt_over_diphoton_mass": r"lead $p_T^{\gamma}/M_{\gamma\gamma}$",
#         "sublead_pt_over_diphoton_mass": r"sublead $p_T^{\gamma}/M_{\gamma\gamma}$",
#         "lead_pt_over_dibjet_mass": r"lead $p_T^{j}/M_{b\bar{b}}$",
#         "sublead_pt_over_dibjet_mass": r"sublead $p_T(j)/M_{b\bar{b}}$",
#         "diphoton_bbgg_mass": r"$p_T^{\gamma\gamma}/M_{b\bar{b}\gamma\gamma}$",
#         "dibjet_bbgg_mass": r"$p_T^{b\bar{b}}/m_{b\bar{b}\gamma\gamma}$",
#         "puppiMET_pt": r"puppi $p_T^{miss}$ [GeV]",
#         "puppiMET_phi": r"puppi $\phi^{miss}$",
#         "puppiMET_phiJERDown": r"puppi $\phi^{JERDown}$",
#         "puppiMET_phiJERUp": r"puppi $\phi^{JERUp}$",
#         "puppiMET_phiJESDown": r"puppi $\phi^{JESDown}$",
#         "puppiMET_phiUnclusteredDown": r"puppi $\phi^{UnclusterDown}$",
#         "puppiMET_phiUnclusteredUp": r"puppi $\phi^{UnclusterUp}$",
#         "puppiMET_ptJERDown": r"puppi $p_T^{JERDown}$ [GeV]",
#         "puppiMET_ptJERUp": r"puppi $p_T^{JERUp}$ [GeV]",
#         "puppiMET_ptJESDown": r"puppi $p_T^{JESDown}$ [GeV]",
#         "puppiMET_ptJESUp": r"puppi $p_T^{JESUp}$ [GeV]",
#         "lead_pho_mvaID_WP90": r"lead_PhoMVAID90",
#         "sublead_pho_mvaID_WP90": r"sublead_PhoMVAID90",
#         "lead_pho_mvaID_WP80": r"lead_PhoMVAID80",
#         "sublead_pho_mvaID_WP80": r"sublead_PhoMVAID80",
#         "lead_pho_mvaID": r"lead_PhoMVAID",
#         "sublead_pho_mvaID": r"sublead_PhoMVAID",
#     }

#     # create the tdirectory to save plots
#     output_directory = "stack_plots"
#     if not os.path.exists(output_directory):
#         os.makedirs(output_directory)

# # plotting  the histograms
#     stack1d_histograms(
#         uproot_loaded_filename,
#         data_samples,
#         mc_samples,
#         signal_samples,
#         histogram_names,
#         legend_dict,
#         xaxis_titles,
#         output_directory,
#         blind=False,
#     )


# if __name__ == "__main__":
#     main()

# # %%

# %
# plot_stacks.py
import os, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import argparse

import uproot
from hist import Hist, Stack
import boost_histogram as bh
import matplotlib.pyplot as plt
import mplhep as hep
from cycler import cycler
from normalisation import getLumi

# --- import the SAME maps your analyzer used ---
from variables import vardict, regions as REGION_LIST, variables_common  # <- key change

# If you have a year/era-aware getLumi, replace this label.
def lumi_label():
    return "61.9"

# ------------------- Styling -------------------
hep.style.use("CMS")
plt.rcParams["axes.prop_cycle"] = cycler(
    color=[
        "#3f90da", "#ffa90e", "#bd1f01", "#94a4a2", "#832db6",
        "#a96b59", "#e76300", "#b9ac70", "#717581", "#92dadd",
    ]
)

# ------------------- Safe hist ops -------------------
def ensure_weight_hist(h_in: Hist) -> Hist:
    axes = []
    for ax in h_in.axes:
        edges = getattr(ax, "edges", None)
        if edges is not None:
            axes.append(bh.axis.Variable(edges))
        else:
            axes.append(bh.axis.Regular(ax.size, ax.edges[0], ax.edges[-1]))
    h_out = Hist(*axes, storage=bh.storage.Weight())
    vals = np.asarray(h_in.values(), dtype="f8")
    vars_ = h_in.variances()
    vars_ = np.zeros_like(vals, dtype="f8") if vars_ is None else np.asarray(vars_, dtype="f8")
    view = h_out.view()
    view.value[...] = vals
    view.variance[...] = vars_
    return h_out

def add_hist_safe(a: Hist | None, b: Hist) -> Hist:
    b = ensure_weight_hist(b)
    if a is None:
        return b
    a = ensure_weight_hist(a)
    a += b
    return a

# ------------------- ROOT helpers -------------------
def list_top_dirs(upfile):
    out = []
    for key in upfile.keys():
        name = key.split(";")[0]
        try:
            obj = upfile[name]
            if hasattr(obj, "keys"):
                out.append(name)
        except KeyError:
            continue
    return out

def dir_to_base(name: str) -> str | None:
    n = name
    if n.startswith("Data_") or n.startswith("_Data"):
        return "Data"

    # drop era tokens & year hints if present
    n = re.sub(r"^_(preEE|postEE|preBPix|postBPix)_", "", n, flags=re.IGNORECASE)
    n = re.sub(r"(2022|2023)(PreEE|PostEE|preBPix|postBPix)", "", n, flags=re.IGNORECASE)

    # DD templates
    if n.startswith("DDQCDGJET") or re.match(r"GGJets_(high|low)_Rescaled", n, re.IGNORECASE):
        return "DDQCDGJET"

    # Common MC bases
    mc_bases = {
        "GGJets",
        # "GJetPt20To40",
        # "GJetPt40",
        "GluGluHToGG",
        "VBFHToGG",
        "VHToGG",
        "ttHToGG",
        "TTGG",
        "TTG",
    }
    for base in mc_bases:
        if n.lower() == base.lower():
            return base

    # capitalization variants occasionally appear
    aliases = {
        "glugluhtogg": "GluGluHToGG",
        "tthtogg": "ttHToGG",
        "vbfhtogg": "VBFHToGG",
        "vhtogg": "VHToGG",
        # "gjetpt20to40": "GJetPt20To40",
        # "gjetpt40": "GJetPt40",
        "gjetpt40toinf": "GJetPt40",
        "ttgg":"TTGG",
        "ttg":"TTG"
    }
    if n.lower() in aliases:
        return aliases[n.lower()]

    # keep each NMSSM as-is
    if n.startswith("NMSSM_"):
        return n

    return None

def group_by_base(upfile):
    groups = {}
    for d in list_top_dirs(upfile):
        base = dir_to_base(d)
        if base is None:
            continue
        groups.setdefault(base, []).append(d)
    return {k: sorted(v) for k, v in groups.items()}

# ------------------- Read hist -------------------
def get_histogram(upfile, path: str, label=None) -> Hist:
    # path: Sample/Region/<vardict[var]>
    h = Hist(upfile[path])
    if label is not None:
        h.name = label
    return h

def sum_hist_list(hlist):
    out = None
    for h in hlist:
        out = add_hist_safe(out, h)
    return out

# ------------------- Blinding & ratio -------------------
def blind_data(hist, blind, start_blind=122, stop_blind=128):
    if not blind:
        return hist
    blinded = hist.copy()
    for b in range(blinded.axes[0].size):
        c = blinded.axes[0].centers[b]
        if start_blind <= c <= stop_blind:
            blinded[b] = 0.0
    return blinded

def get_ratio(hist_a, hist_b):
    edges_a = hist_a.axes.edges[0]
    edges_b = hist_b.axes.edges[0]
    if not np.array_equal(edges_a, edges_b):
        raise ValueError("Histograms have different binning")
    a = np.where(hist_a.values() < 0, 0.0, hist_a.values())
    b = np.where(hist_b.values() < 0, 0.0, hist_b.values())
    ea = np.sqrt(a)
    eb = np.sqrt(b)
    ratio = np.divide(a, b, out=np.zeros_like(a, dtype=float), where=b != 0)
    ratio_hist = Hist(hist_a.axes[0], storage=bh.storage.Double())
    ratio_hist[...] = ratio
    with np.errstate(divide="ignore", invalid="ignore"):
        ra = np.divide(ea, a, out=np.zeros_like(ea, dtype=float), where=a != 0)
        rb = np.divide(eb, b, out=np.zeros_like(eb, dtype=float), where=b != 0)
    ratio_err = ratio * np.sqrt(ra**2 + rb**2)
    return ratio_hist, ratio_err

# ------------------- Config -------------------
blind_vars = ["dibjet_mass", "diphoton_mass"]

legend = {
    "Data": "Data",
    "GGJets": r"$\gamma\gamma$+jets",
    # "GJetPt20To40": r"$\gamma$+jets ($20< p_T < 40$)",
    # "GJetPt40": r"$\gamma$+jets ($p_T > 40$)",
    "GluGluHToGG": r"$gg\to H\to\gamma\gamma$",
    "VBFHToGG": r"$VBF\,H\to\gamma\gamma$",
    "VHToGG": r"$V\,H\to\gamma\gamma$",
    "ttHToGG": r"$t\bar t H\to\gamma\gamma$",
    "DDQCDGJET": r"DDQCDGJET",
    "TTGG": r"$t\bar t \to \gamma\gamma$",
    "TTG": r"$t\bar t \to \gamma",
    # signals
    "NMSSM_X400_Y100": r"$NMSSM\_X_{400}\_Y_{100}\times 10$",
    "NMSSM_X400_Y125": r"$NMSSM\_X_{400}\_Y_{125}\times 10$",
    "NMSSM_X400_Y150": r"$NMSSM\_X_{400}\_Y_{150}\times 10$",
    "NMSSM_X500_Y100": r"$NMSSM\_X_{500}\_Y_{100}\times 10$",
    "NMSSM_X500_Y125": r"$NMSSM\_X_{500}\_Y_{125}\times 10$",
    "NMSSM_X500_Y150": r"$NMSSM\_X_{500}\_Y_{150}\times 10$",
}

# Optional pretty x-axis names (fallback to raw var if missing)
xaxis_titles = {
    "dibjet_mass": r"$m_{b\bar{b}}$ [GeV]",
    "diphoton_mass": r"$m_{\gamma\gamma}$ [GeV]",
    "bbgg_mass": r"$m_{b\bar{b}\gamma\gamma}$ [GeV]",
    "dibjet_pt": r"$p_T^{b\bar{b}}$ [GeV]",
    "diphoton_pt": r"$p_T^{\gamma\gamma}$ [GeV]",
    "bbgg_pt": r"$p_T^{b\bar{b}\gamma\gamma}$ [GeV]",
    # ... add more if you want
}

# ------------------- Plotter -------------------
def stack1d_histograms(up, output_dir, blind=True):
    groups = group_by_base(up)  # base -> [concrete dirs]

    data_base = "Data"
    mc_bases = ["GGJets",
                "GJetPt20To40",
                "GJetPt40",
                "GluGluHToGG","VBFHToGG","VHToGG","ttHToGG","DDQCDGJET","TTGG", "TTG"]
    signal_bases = [
                    # "NMSSM_X400_Y100",
                    # "NMSSM_X400_Y125",
                    # "NMSSM_X400_Y150",
                    # "NMSSM_X500_Y100",
                    # "NMSSM_X500_Y125",
                    "NMSSM_X500_Y150"
                    ]

    # Build jobs from the analyzer's truth: region -> list of variables
    jobs = [(reg, var) for reg in REGION_LIST for var in variables_common[reg]]

    for region, var in jobs:
        hname = vardict[var]  # <—— the key fix: use vardict[var] on disk
        # --- data
        data_hist = None
        for d in groups.get(data_base, []):
            path = f"{d}/{region}/{hname}"
            if path in up:
                data_hist = add_hist_safe(data_hist, get_histogram(up, path, legend["Data"]))
        if data_hist is None:
            # nothing to draw in this region/var
            continue

        # --- MC (sum eras per base)
        mc_merged = []
        for base in mc_bases:
            hsum = None
            for d in groups.get(base, []):
                path = f"{d}/{region}/{hname}"
                if path in up:
                    hsum = add_hist_safe(hsum, get_histogram(up, path, legend.get(base, base)))
            if hsum is not None:
                hsum.name = legend.get(base, base)
                mc_merged.append(hsum)
        if not mc_merged:
            continue

        # --- signals (only in SRs)
        signal_hists = []
        if region in ("srbbgg","srbbggMET", "preselection", "selection"):
            for base in signal_bases:
                hsum = None
                for d in groups.get(base, []):
                    path = f"{d}/{region}/{hname}"
                    if path in up:
                        hsum = add_hist_safe(hsum, get_histogram(up, path, legend.get(base, base)))
                if hsum is not None:
                    hsum.name = legend.get(base, base)
                    signal_hists.append(hsum)

        # --- figure
        dyn_w = max(11, int(1.5*len(mc_merged)))
        fig, (ax, ax_ratio) = plt.subplots(
            2, 1, figsize=(dyn_w, 12),
            gridspec_kw={"height_ratios":[3,1]}, sharex=True
        )
        fig.subplots_adjust(hspace=0.05)

        # data (blind if requested)
        do_blind = blind and (var in blind_vars)
        data_plot = blind_data(data_hist, do_blind, start_blind=110, stop_blind=130)
        data_plot.plot(ax=ax, stack=False, histtype="errorbar",
                       yerr=True, xerr=True, color="black", label="Data", flow="sum")

        # MC stack
        Stack(*mc_merged).plot(ax=ax, stack=True, histtype="fill", flow="sum", sort="yield")

        # signal overlays
        for s in signal_hists:
            s.plot(ax=ax, histtype="step", yerr=False, xerr=False, label=s.name, color="red")

        # ratio
        mc_sum = sum_hist_list(mc_merged)
        ratio, rerr = get_ratio(data_hist, mc_sum)
        ratio_plot = blind_data(ratio, do_blind, start_blind=110, stop_blind=130)
        ratio_plot.plot(ax=ax_ratio, histtype="errorbar", yerr=rerr, xerr=True, color="black", flow="sum")
        ax_ratio.axhline(1, linestyle="--", color="gray")
        ax_ratio.set_ylim(0, 3)
        ax_ratio.set_ylabel("Data / MC")
        ax_ratio.set_xlabel(xaxis_titles.get(var, var.replace("_"," ")))

        # style
        ax.set_yscale("log")
        ax.set_ylim(0.1, 1e8)
        ax.set_ylabel("Events")
        hep.cms.label("", ax=ax, lumi=lumi_label(), loc=0, llabel="Work in progress", com=13.6)
        ax.legend(ncol=2, loc="upper right", fontsize=16)
        ax.set_xlabel("")

        # save
        outdir = os.path.join(output_dir, region)
        os.makedirs(outdir, exist_ok=True)
        plt.tight_layout()
        plt.savefig(os.path.join(outdir, f"{var}.pdf"), bbox_inches="tight")
        plt.savefig(os.path.join(outdir, f"{var}.png"), bbox_inches="tight")
        plt.close()
        print(f"[OK] {region}/{var}")

def main():
    root_path = "outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-histograms.root"
    up = uproot.open(root_path)
    out = "stack_plots"
    os.makedirs(out, exist_ok=True)
    stack1d_histograms(up, out, blind=False)

if __name__ == "__main__":
    main()

