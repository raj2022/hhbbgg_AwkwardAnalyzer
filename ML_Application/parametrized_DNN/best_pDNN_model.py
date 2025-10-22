# # ================================================================
# # Parameterized DNN (PDNN) with group-safe splits, diagnostics,
# # OOM-safe batched eval, small-normal init, and consistency gate.
# # Now using the *Res_* variables everywhere (no nonRes_* left).
# # ================================================================
# import os, hashlib, warnings
# import numpy as np
# import pandas as pd
# import matplotlib.pyplot as plt

# import torch
# import torch.nn as nn
# from torch.utils.data import Dataset, DataLoader
# from torch.optim import Adam, lr_scheduler

# from sklearn.model_selection import GroupShuffleSplit
# from sklearn.preprocessing import StandardScaler
# from sklearn.metrics import roc_auc_score, accuracy_score, roc_curve, auc
# from sklearn.linear_model import LogisticRegression
# from sklearn.tree import DecisionTreeClassifier
# from sklearn.ensemble import GradientBoostingClassifier

# warnings.filterwarnings("ignore", category=UserWarning)


# # ---- CMS-like plotting style & palette ----
# from matplotlib.colors import LinearSegmentedColormap
# from cycler import cycler

# plt.rcParams.update({
#     "figure.figsize": (7.5, 5.5),
#     "figure.dpi": 110,
#     "axes.grid": True,
#     "grid.alpha": 0.30,
#     "axes.titlesize": 14,
#     "axes.labelsize": 12,
#     "legend.fontsize": 10,
#     "xtick.labelsize": 10,
#     "ytick.labelsize": 10,
#     "lines.linewidth": 2.0,
# })

# # colors (picked to match the slide vibe)
# CMS_BLUE     = "#2368B5"   # main blue
# CMS_RED      = "#C0392B"   # strong red
# CMS_ORANGE   = "#E67E22"
# CMS_GREEN    = "#2E8B57"
# CMS_PURPLE   = "#6C5CE7"
# CMS_GRAY     = "#4D4D4D"

# # sequence for multi-lines (per-sample ROC)
# plt.rcParams["axes.prop_cycle"] = cycler(color=[
#     CMS_BLUE, CMS_RED, CMS_ORANGE, CMS_GREEN, CMS_PURPLE, "#1ABC9C", "#8E44AD",
#     "#16A085", "#D35400", "#2C3E50"
# ])

# # diverging colormap (blue ↔ white ↔ red) for correlation
# cms_div = LinearSegmentedColormap.from_list(
#     "cms_div", ["#1f77b4", "#f7f7f7", "#d62728"], N=256
# )


# # -----------------------------
# # Config
# # -----------------------------
# SEED = 42
# np.random.seed(SEED)
# torch.manual_seed(SEED)
# torch.cuda.manual_seed_all(SEED)
# torch.backends.cudnn.deterministic = True
# torch.backends.cudnn.benchmark = False

# # data handling
# BACKGROUND_FRAC     = 1.0    # 1.0 = keep all background
# BALANCE_PER_GROUP   = True   # balance S=B inside each (mass,y) *after* split

# # model/training
# USE_BATCHNORM       = False  # BN off for stability
# BATCH_SIZE_TRAIN    = 128
# LR                  = 1e-3
# WEIGHT_CLIP         = 10.0
# PATIENCE            = 20
# MAX_EPOCHS          = 100
# WEIGHT_DECAY        = 1e-4
# SAVE_MODEL_PATH     = "optimized_best_pdnn.pt"

# # eval (OOM safety)
# EVAL_BATCH          = 32768
# USE_AMP_EVAL        = True
# CPU_FALLBACK_ON_OOM = True

# # debug toggles
# DEBUG_ONE_BATCH             = False  # train only one minibatch per epoch
# DEBUG_SHUFFLE_TRAIN_LABELS  = False  # train with shuffled labels → Val AUC ≈ 0.5

# # optional ablation: drop features by name (before arrays are built)
# DROP_FEATURES = []  # e.g., ['Res_sublead_bjet_pt','Res_lead_bjet_pt','Res_pholead_PtOverM','Res_DeltaR_jg_min']

# # mass/y grid
# mass_points = [300, 400, 500, 550, 600, 650, 700, 800, 900, 1000]
# y_values    = [60, 70, 80, 90, 95, 100, 125, 150, 200]

# # -----------------------------
# # Inputs
# # -----------------------------
# # SIGNAL parquet pattern (per mass,y set)
# SIG_TPL = "../../../output_parquet/final_production_Syst/merged/NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet"

# # BACKGROUND is parquet
# background_files = [
#     "../../../output_root/v3_production/samples/postEE/GGJets.parquet",
#     "../../../output_root/v3_production/samples/postEE/GJetPt20To40.parquet",
#     "../../../output_root/v3_production/samples/postEE/GJetPt40.parquet",
# ]

# # ============================
# # Features (Res_* version)
# # ============================
# WEIGHT_COL = "weight_central"

# FEATURES_CORE = [
#     # photons & diphoton (diphoton candidate uses global 'eta','phi' in your parquet)
#     "lead_eta","lead_phi","sublead_eta","sublead_phi",
#     "eta","phi",

#     # jets, dijet, HH (Res)
#     "Res_lead_bjet_eta","Res_lead_bjet_phi",
#     "Res_sublead_bjet_eta","Res_sublead_bjet_phi",
#     "Res_dijet_eta","Res_dijet_phi",
#     "Res_HHbbggCandidate_eta","Res_HHbbggCandidate_phi",

#     # scaled pT (Res)
#     # "Res_pholead_PtOverM","Res_phosublead_PtOverM",
#     # "Res_FirstJet_PtOverM","Res_SecondJet_PtOverM",

#     # angular distances (Res)
#     "Res_DeltaR_j1g1","Res_DeltaR_j1g2",
#     "Res_DeltaR_j2g1","Res_DeltaR_j2g2",
#     "Res_DeltaR_jg_min",

#     # helicity / Collins–Soper (Res)
#     "Res_CosThetaStar_gg","Res_CosThetaStar_jj","Res_CosThetaStar_CS",

#     # photon ID + b-tag (Res jets)
#     "lead_mvaID_run3","sublead_mvaID_run3",
#     # "Res_lead_bjet_btagPNetB","Res_sublead_bjet_btagPNetB",

#     # counts & MET
#     "n_leptons","n_jets","puppiMET_pt","puppiMET_phi",

#     # χ² terms (Res)
#     "Res_chi_t0","Res_chi_t1",

#     # raw kinematics needed for engineered ratios (Res)
#     # "Res_dijet_pt",
#     "Res_HHbbggCandidate_pt",
#     # "Res_HHbbggCandidate_mass",
# ]

# # --- engineered features (from Res_* kinematics) ---
# def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
#     mHH = df.get("Res_HHbbggCandidate_mass", pd.Series(index=df.index, dtype="float32"))
#     mHH = mHH.replace(0, np.nan)

#     if "Res_dijet_pt" in df.columns:
#         df["ptjj_over_mHH"] = df["Res_dijet_pt"] / mHH
#     else:
#         df["ptjj_over_mHH"] = 0.0

#     if "Res_HHbbggCandidate_pt" in df.columns:
#         df["ptHH_over_mHH"] = df["Res_HHbbggCandidate_pt"] / mHH
#     else:
#         df["ptHH_over_mHH"] = 0.0

#     # ΔR(γγ) from photon kinematics
#     if all(c in df.columns for c in ["lead_phi","sublead_phi","lead_eta","sublead_eta"]):
#         dphi = np.abs(df["lead_phi"] - df["sublead_phi"])
#         dphi = np.where(dphi > np.pi, 2*np.pi - dphi, dphi)
#         deta = df["lead_eta"] - df["sublead_eta"]
#         df["DeltaR_gg"] = np.sqrt(deta**2 + dphi**2)
#     else:
#         df["DeltaR_gg"] = 0.0

#     # absolute cos* (if you want |cosθ*|)
#     for c in ["Res_CosThetaStar_gg","Res_CosThetaStar_jj","Res_CosThetaStar_CS"]:
#         if c in df.columns:
#             df[c] = df[c].abs()

#     for c in ["ptjj_over_mHH","ptHH_over_mHH","DeltaR_gg"]:
#         df[c] = df[c].fillna(0)

#     return df

# # photon ID fallback (if only *_mvaID_nano exists)
# def ensure_photon_mva_columns(df: pd.DataFrame) -> pd.DataFrame:
#     pairs = [("lead_mvaID_run3","lead_mvaID_nano"),
#              ("sublead_mvaID_run3","sublead_mvaID_nano")]
#     for want, alt in pairs:
#         if want not in df.columns and alt in df.columns:
#             df[want] = df[alt]
#     return df

# # include engineered names in features
# FEATURES_CORE = FEATURES_CORE + [
#                                 # "ptjj_over_mHH",
#                                 "ptHH_over_mHH",
#                                 #  "DeltaR_gg"
#                                  ]
# FEATURES_FINAL = FEATURES_CORE + ["mass", "y_value"]

# # -----------------------------
# # Helpers
# # -----------------------------
# def downcast_float_cols(df: pd.DataFrame) -> pd.DataFrame:
#     for c in df.select_dtypes(include=['float64']).columns:
#         df[c] = df[c].astype('float32')
#     return df

# def ensure_weight(df: pd.DataFrame, weight_col=WEIGHT_COL) -> pd.DataFrame:
#     if weight_col not in df.columns:
#         df[weight_col] = 1.0
#     return df

# def df_to_arrays(df: pd.DataFrame, feature_list):
#     Xdf = df[feature_list].copy()
#     Xdf = Xdf.fillna(Xdf.mean(numeric_only=True))
#     Xdf = downcast_float_cols(Xdf)
#     X = Xdf.values
#     y = df['label'].astype(np.int8).values
#     w = df[WEIGHT_COL].astype('float32').values
#     return X, y, w

# def balance_per_group(df, seed=SEED, min_per_class=1):
#     key = df['mass'].astype(int).astype(str) + "_" + df['y_value'].astype(int).astype(str)
#     parts = []; dropped = 0
#     for _, sub in df.groupby(key, sort=False):
#         vc = sub['label'].value_counts()
#         if len(vc) < 2: dropped += 1; continue
#         n_min = vc.min()
#         if n_min < min_per_class: dropped += 1; continue
#         s = sub[sub['label']==1]; b = sub[sub['label']==0]
#         s_keep = s.sample(n=n_min, random_state=seed) if len(s)>n_min else s
#         b_keep = b.sample(n=n_min, random_state=seed) if len(b)>n_min else b
#         parts.append(pd.concat([s_keep, b_keep], ignore_index=True))
#     if not parts:
#         raise RuntimeError("Per-group balancing removed all groups; relax constraints or inspect data.")
#     out = pd.concat(parts, ignore_index=True).sample(frac=1.0, random_state=seed).reset_index(drop=True)
#     if dropped: print(f"[INFO] balance_per_group: dropped {dropped} tiny/pure groups in this split.")
#     return out

# def check_groups(df, name):
#     groups = df['mass'].astype(int).astype(str) + "_" + df['y_value'].astype(int).astype(str)
#     bad = [(k, int(g['label'].iloc[0]), len(g)) for k,g in df.groupby(groups) if g['label'].nunique()<2]
#     if bad:
#         print(f"[WARN] {name}: {len(bad)} pure (mass,y) groups remain. Examples: {bad[:5]}")
#     assert df['label'].nunique()==2, f"{name} has only one class!"

# def split_summary(df, name):
#     key = df['mass'].astype(int).astype(str) + "_" + df['y_value'].astype(int).astype(str)
#     print(f"{name}: N={len(df):,}  counts={df['label'].value_counts().to_dict()}  groups={key.nunique()}")

# @torch.no_grad()
# def predict_batched(model, X_tensor, device, batch=32768, use_amp=True):
#     model.eval()
#     N = X_tensor.shape[0]
#     out = np.empty(N, dtype=np.float32)
#     amp_ctx = torch.amp.autocast(device_type=device.type, enabled=(use_amp and device.type=="cuda"))
#     with amp_ctx:
#         for i in range(0, N, batch):
#             xb = X_tensor[i:i+batch].to(device, non_blocking=True)
#             logits = model(xb).view(-1)
#             out[i:i+batch] = torch.sigmoid(logits).detach().cpu().numpy()
#     return out

# def safe_eval_probs(model, X_tensor, device):
#     try:
#         return predict_batched(model, X_tensor, device, batch=EVAL_BATCH, use_amp=USE_AMP_EVAL)
#     except RuntimeError as e:
#         if CPU_FALLBACK_ON_OOM and "CUDA out of memory" in str(e):
#             print("[WARN] CUDA OOM during eval → falling back to CPU (batched).")
#             cpu_model = model.to(torch.device("cpu"))
#             X_cpu = X_tensor.to(torch.device("cpu"))
#             return predict_batched(cpu_model, X_cpu, torch.device("cpu"), batch=max(8192, EVAL_BATCH), use_amp=False)
#         raise

# # -----------------------------
# # 1) Load SIGNAL (Parquet, per mass/y) — compute engineered features first
# # -----------------------------
# signal_rows = []
# for mass in mass_points:
#     for y in y_values:
#         fp = SIG_TPL.format(m=mass, y=y)
#         if not os.path.exists(fp): 
#             continue
#         try:
#             try:
#                 cols = pd.read_parquet(fp, columns=None).columns
#                 need_raw = [
#                     "lead_eta","lead_phi","sublead_eta","sublead_phi","eta","phi",
#                     "Res_lead_bjet_eta","Res_lead_bjet_phi",
#                     "Res_sublead_bjet_eta","Res_sublead_bjet_phi",
#                     "Res_dijet_eta","Res_dijet_phi",
#                     "Res_HHbbggCandidate_eta","Res_HHbbggCandidate_phi",
#                     "Res_pholead_PtOverM","Res_phosublead_PtOverM",
#                     "Res_FirstJet_PtOverM","Res_SecondJet_PtOverM",
#                     "Res_DeltaR_j1g1","Res_DeltaR_j1g2",
#                     "Res_DeltaR_j2g1","Res_DeltaR_j2g2","Res_DeltaR_jg_min",
#                     "Res_CosThetaStar_gg","Res_CosThetaStar_jj","Res_CosThetaStar_CS",
#                     "lead_mvaID_run3","sublead_mvaID_run3",
#                     "lead_mvaID_nano","sublead_mvaID_nano",  # fallback source
#                     "Res_lead_bjet_btagPNetB","Res_sublead_bjet_btagPNetB",
#                     "n_leptons","n_jets","puppiMET_pt","puppiMET_phi",
#                     "Res_chi_t0","Res_chi_t1",
#                     "Res_dijet_pt","Res_HHbbggCandidate_pt","Res_HHbbggCandidate_mass",
#                 ]
#                 subset = [c for c in (set(need_raw) | {WEIGHT_COL}) if c in cols]
#                 df = pd.read_parquet(fp, columns=subset)
#             except Exception:
#                 df = pd.read_parquet(fp)

#             df = ensure_photon_mva_columns(df)
#             df = add_engineered_features(df)

#             keep = [c for c in FEATURES_CORE if c in df.columns]
#             extras = [WEIGHT_COL] if WEIGHT_COL in df.columns else []
#             df = df[keep + extras].copy()
#             df['mass']=mass; df['y_value']=y; df['label']=1
#             df = ensure_weight(df); df = downcast_float_cols(df)
#             signal_rows.append(df)
#         except Exception as e:
#             print(f"[WARN] read fail {fp}: {e}")
# signal_df = pd.concat(signal_rows, ignore_index=True) if signal_rows else pd.DataFrame()

# # -----------------------------
# # 2) Load BACKGROUND (Parquet) — compute engineered features first
# # -----------------------------
# bkg_parts = []
# for file_path in background_files:
#     if not os.path.exists(file_path):
#         print(f"[WARN] Missing {file_path}")
#         continue
#     try:
#         try:
#             cols = pd.read_parquet(file_path, columns=None).columns
#             need_raw = [
#                 "lead_eta","lead_phi","sublead_eta","sublead_phi","eta","phi",
#                 "Res_lead_bjet_eta","Res_lead_bjet_phi",
#                 "Res_sublead_bjet_eta","Res_sublead_bjet_phi",
#                 "Res_dijet_eta","Res_dijet_phi",
#                 "Res_HHbbggCandidate_eta","Res_HHbbggCandidate_phi",
#                 "Res_pholead_PtOverM","Res_phosublead_PtOverM",
#                 "Res_FirstJet_PtOverM","Res_SecondJet_PtOverM",
#                 "Res_DeltaR_j1g1","Res_DeltaR_j1g2",
#                 "Res_DeltaR_j2g1","Res_DeltaR_j2g2","Res_DeltaR_jg_min",
#                 "Res_CosThetaStar_gg","Res_CosThetaStar_jj","Res_CosThetaStar_CS",
#                 "lead_mvaID_run3","sublead_mvaID_run3",
#                 "lead_mvaID_nano","sublead_mvaID_nano",
#                 "Res_lead_bjet_btagPNetB","Res_sublead_bjet_btagPNetB",
#                 "n_leptons","n_jets","puppiMET_pt","puppiMET_phi",
#                 "Res_chi_t0","Res_chi_t1",
#                 "Res_dijet_pt","Res_HHbbggCandidate_pt","Res_HHbbggCandidate_mass",
#             ]
#             subset = [c for c in (set(need_raw) | {WEIGHT_COL}) if c in cols]
#             dfb = pd.read_parquet(file_path, columns=subset)
#         except Exception:
#             dfb = pd.read_parquet(file_path)

#         dfb = ensure_photon_mva_columns(dfb)
#         dfb = add_engineered_features(dfb)

#         keep = [c for c in FEATURES_CORE if c in dfb.columns]
#         extras = [WEIGHT_COL] if WEIGHT_COL in dfb.columns else []
#         dfb = dfb[keep + extras].copy()
#         dfb = ensure_weight(dfb)
#         dfb['label'] = 0
#         dfb = downcast_float_cols(dfb)
#         bkg_parts.append(dfb)
#     except Exception as e:
#         print(f"[WARN] read fail {file_path}: {e}")
# df_background = pd.concat(bkg_parts, ignore_index=True) if bkg_parts else pd.DataFrame()
# if BACKGROUND_FRAC < 1.0 and not df_background.empty:
#     df_background = df_background.sample(frac=BACKGROUND_FRAC, random_state=SEED).reset_index(drop=True)

# if signal_df.empty or df_background.empty:
#     raise RuntimeError(f"Empty data: signal={signal_df.empty}, background={df_background.empty}")

# # -----------------------------
# # 3) Assign (mass,y) to BACKGROUND ~ signal mix, ensure coverage
# # -----------------------------
# sig_my = signal_df[['mass','y_value']]
# mix = sig_my.value_counts(normalize=True).reset_index()
# mix.columns = ['mass','y_value','weight']
# sampled = mix.sample(n=len(df_background), replace=True, weights='weight', random_state=SEED).reset_index(drop=True)
# df_background['mass']    = sampled['mass'].values
# df_background['y_value'] = sampled['y_value'].values

# need = set(map(tuple, sig_my.drop_duplicates().values.tolist()))
# have = set(map(tuple, df_background[['mass','y_value']].drop_duplicates().values.tolist()))
# missing_keys = list(need - have)
# if missing_keys:
#     K = min(len(missing_keys), len(df_background))
#     for i,(m,y) in enumerate(missing_keys[:K]):
#         df_background.loc[i,'mass']=m
#         df_background.loc[i,'y_value']=y

# # -----------------------------
# # 4) Combine, drop pure (mass,y) groups globally
# # -----------------------------
# df_all = pd.concat([signal_df, df_background], ignore_index=True)
# key_all = df_all['mass'].astype(int).astype(str) + "_" + df_all['y_value'].astype(int).astype(str)
# grp_nuniq = df_all.groupby(key_all)['label'].nunique()
# good_keys = set(grp_nuniq[grp_nuniq==2].index)
# mask_good = key_all.isin(good_keys)
# dropped = int((~mask_good).sum())
# if dropped: print(f"[INFO] Dropping {dropped} rows from pure (mass,y) groups before split.")
# df_all = df_all.loc[mask_good].reset_index(drop=True)

# # -----------------------------
# # 5) Feature list (final) + optional ablation
# # -----------------------------
# FEATURES_FINAL = FEATURES_CORE + ['mass','y_value']
# if DROP_FEATURES:
#     removed = [f for f in DROP_FEATURES if f in FEATURES_FINAL]
#     if removed:
#         print(f"[Ablation] Dropping features: {removed}")
#         FEATURES_FINAL = [f for f in FEATURES_FINAL if f not in removed]

# available_features = [c for c in FEATURES_FINAL if c in df_all.columns]
# missing = sorted(set(FEATURES_FINAL) - set(available_features))
# if missing: print(f"[Note] Missing features ignored: {missing}")

# # -----------------------------
# # 6) Group splits by (mass,y)
# # -----------------------------
# groups_all = df_all['mass'].astype(int).astype(str) + "_" + df_all['y_value'].astype(int).astype(str)
# gss_outer = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=SEED)
# idx_trval, idx_te = next(gss_outer.split(df_all, df_all['label'], groups_all))
# df_trval = df_all.iloc[idx_trval].reset_index(drop=True)
# df_te    = df_all.iloc[idx_te].reset_index(drop=True)

# gss_inner = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=SEED)
# groups_trval = df_trval['mass'].astype(int).astype(str) + "_" + df_trval['y_value'].astype(int).astype(str)
# idx_tr, idx_va = next(gss_inner.split(df_trval, df_trval['label'], groups_trval))
# df_tr = df_trval.iloc[idx_tr].reset_index(drop=True)
# df_va = df_trval.iloc[idx_va].reset_index(drop=True)

# if BALANCE_PER_GROUP:
#     df_tr = balance_per_group(df_tr)
#     df_va = balance_per_group(df_va)
#     df_te = balance_per_group(df_te)

# split_summary(df_tr, "TRAIN")
# split_summary(df_va, "VAL")
# split_summary(df_te, "TEST")
# check_groups(df_tr, "TRAIN"); check_groups(df_va, "VAL"); check_groups(df_te, "TEST")

# set_tr = set((df_tr['mass'].astype(int).astype(str)+"_"+df_tr['y_value'].astype(int).astype(str)).unique())
# set_va = set((df_va['mass'].astype(int).astype(str)+"_"+df_va['y_value'].astype(int).astype(str)).unique())
# set_te = set((df_te['mass'].astype(int).astype(str)+"_"+df_te['y_value'].astype(int).astype(str)).unique())
# print("Overlap Train∩Val:", len(set_tr & set_va))
# print("Overlap Train∩Test:", len(set_tr & set_te))
# print("Overlap Val∩Test:", len(set_va & set_te))

# # -----------------------------
# # 7) Arrays + scaling (fit on TRAIN only)
# # -----------------------------
# X_tr_raw, y_tr, w_tr = df_to_arrays(df_tr, available_features)
# X_va_raw, y_va, w_va = df_to_arrays(df_va, available_features)
# X_te_raw, y_te, w_te = df_to_arrays(df_te, available_features)

# if DEBUG_SHUFFLE_TRAIN_LABELS:
#     rng = np.random.default_rng(SEED+7)
#     y_tr = rng.permutation(y_tr.copy())
#     print("[DEBUG] Shuffled TRAIN labels. Val AUC should ≈ 0.5.")

# scaler = StandardScaler()
# X_tr = scaler.fit_transform(X_tr_raw)
# X_va = scaler.transform(X_va_raw)
# X_te = scaler.transform(X_te_raw)

# # -----------------------------
# # 8) Leakage audit on VAL
# # -----------------------------
# print("\n[Leakage audit on VAL] per-feature AUC:")
# for i, f in enumerate(available_features):
#     auc_f = roc_auc_score(y_va, X_va[:, i])
#     flag = " <-- suspicious" if (auc_f > 0.95 or auc_f < 0.05) else ""
#     print(f"{f:24s} AUC={auc_f:.4f}{flag}")
# i_mass = available_features.index('mass'); i_y = available_features.index('y_value')
# print(f"AUC using only (mass,y) on VAL: {roc_auc_score(y_va, 0.5*X_va[:, i_mass] + 0.5*X_va[:, i_y]):.4f}")

# # -----------------------------
# # 9) Hard sanity checks (before training)
# # -----------------------------
# X_va_t_cpu = torch.tensor(X_va, dtype=torch.float32)
# mae = float(np.mean(np.abs(X_va_t_cpu.numpy() - X_va)))
# mx  = float(np.max(np.abs(X_va_t_cpu.numpy() - X_va)))
# print(f"[Sanity-0] X_va tensor vs numpy: mean|diff|={mae:.3e}, max|diff|={mx:.3e} (expect ~0)")

# p_const = np.full_like(y_va, 0.5, dtype=np.float32)
# print(f"[Sanity-1] Constant 0.5 predictor AUC: {roc_auc_score(y_va, p_const):.4f} (expect 0.5)")

# class IdentityNet(nn.Module):
#     def __init__(self, d): 
#         super().__init__(); 
#         self.fc = nn.Linear(d, 1)
#     def forward(self, x): 
#         return self.fc(x)

# lin_model = IdentityNet(X_tr.shape[1]).cpu()
# nn.init.kaiming_uniform_(lin_model.fc.weight, a=0.0, nonlinearity='linear')
# nn.init.constant_(lin_model.fc.bias, 0.0)
# with torch.no_grad():
#     z_lin = lin_model(X_va_t_cpu).view(-1); p_lin = torch.sigmoid(z_lin).numpy()
# print(f"[Sanity-2] Linear head only AUC: {roc_auc_score(y_va, p_lin):.4f} (should be ~0.5)")

# # -----------------------------
# # 10) Model + small-normal init + untrained diagnostics
# # -----------------------------
# def maybe_bn(n): 
#     return nn.BatchNorm1d(n) if USE_BATCHNORM else nn.Identity()

# class ParameterizedDNN(nn.Module):
#     def __init__(self, d):
#         super().__init__()
#         self.net = nn.Sequential(
#             nn.Linear(d, 128), maybe_bn(128), nn.ReLU(), nn.Dropout(0.3),
#             nn.Linear(128,64), maybe_bn(64), nn.ReLU(), nn.Dropout(0.3),
#             nn.Linear(64,32), maybe_bn(32), nn.ReLU(), nn.Dropout(0.2),
#             nn.Linear(32, 1)  # logits only
#         )
#     def forward(self, x): 
#         return self.net(x)

# def small_normal_zero_bias_(m):
#     if isinstance(m, nn.Linear):
#         nn.init.normal_(m.weight, mean=0.0, std=1e-2)
#         if m.bias is not None:
#             nn.init.constant_(m.bias, 0.0)

# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# print(f"[INFO] Using device: {device}")

# # Build on CPU, init, diagnostics, then move to device
# model = ParameterizedDNN(X_tr.shape[1]).cpu()
# model.apply(small_normal_zero_bias_)
# with torch.no_grad():
#     z0 = model(X_va_t_cpu).view(-1); p0 = torch.sigmoid(z0).numpy()
# auc0 = roc_auc_score(y_va, p0)
# print(f"[Diag] Untrained model Val AUC (expect ~0.5): {auc0:.4f}")
# print(f"[Diag] p0 stats: min={float(p0.min()):.6f} max={float(p0.max()):.6f} mean={float(p0.mean()):.6f} std={float(p0.std()):.6f}")

# # Baselines (VAL)
# lr = LogisticRegression(max_iter=300); lr.fit(X_tr, y_tr)
# auc_lr = roc_auc_score(y_va, lr.predict_proba(X_va)[:,1])
# print(f"[Diag] Logistic regression Val AUC: {auc_lr:.4f}")
# dt = DecisionTreeClassifier(max_depth=3, random_state=SEED); dt.fit(X_tr, y_tr)
# auc_dt = roc_auc_score(y_va, dt.predict_proba(X_va)[:,1])
# print(f"[Diag] DecisionTree(max_depth=3) Val AUC: {auc_dt:.4f}")
# gb = GradientBoostingClassifier(random_state=SEED); gb.fit(X_tr, y_tr)
# auc_gb = roc_auc_score(y_va, gb.predict_proba(X_va)[:,1])
# print(f"[Diag] GradientBoosting Val AUC: {auc_gb:.4f}")

# BASELINE_MAX = max(auc_lr, auc_dt, auc_gb)
# if BASELINE_MAX <= 0.55:
#     print(f"[Gate] Baselines are weak (max={BASELINE_MAX:.3f}). If DNN ValAUC exceeds 0.98, we'll abort and dump diagnostics.")
#     enable_consistency_gate = True
# else:
#     enable_consistency_gate = False

# # Move model to device for training
# model = model.to(device)

# # -----------------------------
# # 11) Tensors & DataLoader
# # -----------------------------
# class ArrayDataset(Dataset):
#     def __init__(self, X, y, w): 
#         self.X=X; self.y=y; self.w=w
#     def __len__(self): 
#         return len(self.X)
#     def __getitem__(self, i):
#         return (torch.tensor(self.X[i], dtype=torch.float32),
#                 torch.tensor(self.y[i], dtype=torch.float32),
#                 torch.tensor(self.w[i], dtype=torch.float32))

# train_loader = DataLoader(ArrayDataset(X_tr, y_tr, w_tr),
#                           batch_size=BATCH_SIZE_TRAIN, shuffle=True,
#                           pin_memory=(device.type=="cuda"),
#                           num_workers=2 if os.name!="nt" else 0)

# X_va_t = torch.tensor(X_va, dtype=torch.float32).to(device)
# X_te_t = torch.tensor(X_te, dtype=torch.float32).to(device)

# # -----------------------------
# # 12) Loss/opt + AMP scaler
# # -----------------------------
# criterion = nn.BCEWithLogitsLoss(reduction='none')
# optimizer = Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
# scheduler = lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=5)
# use_amp = (device.type == "cuda")
# scaler_amp = torch.amp.GradScaler("cuda", enabled=use_amp) if use_amp else torch.amp.GradScaler(enabled=False)

# # -----------------------------
# # 13) Train (early stop on Val AUC)
# # -----------------------------
# history = {"train_loss": [], "val_auc": [], "val_acc": []}
# best_auc = -np.inf; epochs_since_best = 0

# for epoch in range(MAX_EPOCHS):
#     model.train()
#     tot_loss, nseen = 0.0, 0
#     for bi, (xb, yb, wb) in enumerate(train_loader):
#         xb = xb.to(device, non_blocking=True)
#         yb = yb.to(device, non_blocking=True)
#         wb = wb.to(device, non_blocking=True)
#         wb = torch.clamp(wb / (wb.mean() + 1e-8), max=WEIGHT_CLIP)

#         optimizer.zero_grad(set_to_none=True)
#         with torch.amp.autocast(device_type=device.type, enabled=use_amp):
#             logits = model(xb).view(-1)
#             per_loss = criterion(logits, yb)
#             loss = (per_loss * wb).mean()
#         scaler_amp.scale(loss).backward()
#         scaler_amp.step(optimizer)
#         scaler_amp.update()

#         bs = xb.size(0); tot_loss += float(loss.item()) * bs; nseen += bs
#         if DEBUG_ONE_BATCH: break

#     train_loss = tot_loss / max(nseen,1)

#     # Validation
#     val_probs = safe_eval_probs(model, X_va_t, device)
#     val_auc = roc_auc_score(y_va, val_probs)
#     val_acc = accuracy_score(y_va, (val_probs > 0.5).astype(int))

#     history["train_loss"].append(train_loss)
#     history["val_auc"].append(val_auc)
#     history["val_acc"].append(val_acc)

#     print(f"Epoch {epoch+1:02d} | TrainLoss: {train_loss:.4f} | ValAUC: {val_auc:.4f} | ValAcc: {val_acc:.4f}")
#     scheduler.step(val_auc)

#     # Consistency gate
#     if enable_consistency_gate and val_auc >= 0.98:
#         print("[Gate] DNN ValAUC is suspiciously high while baselines are ~0.5. Aborting for safety.")
#         from scipy.stats import spearmanr
#         ranks = []
#         for i, f in enumerate(available_features):
#             try:
#                 r = spearmanr(X_va[:, i], val_probs).statistic
#             except Exception:
#                 r = np.nan
#             ranks.append((f, r))
#         ranks = sorted(ranks, key=lambda t: -abs(t[1]))[:10]
#         print("[Gate] Top |Spearman| feature ↔ score on VAL:")
#         for f, r in ranks:
#             print(f"  {f:24s}  r={r:+.4f}")
#         torch.save(model.state_dict(), SAVE_MODEL_PATH)
#         with open("GATE_ABORTED", "w") as f: f.write("1\n")
#         break

#     # Early stopping
#     if val_auc > best_auc + 1e-4:
#         best_auc = val_auc; epochs_since_best = 0
#         torch.save(model.state_dict(), SAVE_MODEL_PATH)
#         print(f"[INFO] New best ValAUC: {best_auc:.4f} — model saved")
#     else:
#         epochs_since_best += 1
#         if epochs_since_best >= PATIENCE:
#             print(f"[INFO] Early stopping at epoch {epoch+1}."); break

# # -----------------------------
# # 14) Test + separation plots
# # -----------------------------
# if os.path.exists("GATE_ABORTED"):
#     print("[INFO] Consistency gate aborted training early; proceeding with saved snapshot.")

# if os.path.exists(SAVE_MODEL_PATH):
#     try:
#         state = torch.load(SAVE_MODEL_PATH, map_location=device, weights_only=True)
#     except TypeError:
#         state = torch.load(SAVE_MODEL_PATH, map_location=device)
#     model.load_state_dict(state)
# else:
#     print("[WARN] No saved model found; using current in-memory weights.")

# test_probs = safe_eval_probs(model, X_te_t, device)
# fpr, tpr, _ = roc_curve(y_te, test_probs)
# test_auc = auc(fpr, tpr)
# print(f"\nTest AUC: {test_auc:.6f}")

# i_mass = available_features.index('mass'); i_y = available_features.index('y_value')
# print(f"AUC using only (mass,y) on TEST: {roc_auc_score(y_te, 0.5*X_te[:, i_mass] + 0.5*X_te[:, i_y]):.4f}")

# sig_mask = (y_te == 1); bkg_mask = (y_te == 0)
# w_sig = w_te[sig_mask] if w_te is not None else None
# w_bkg = w_te[bkg_mask] if w_te is not None else None
# print(f"\n[Separation diagnostics — TEST]")
# print(f"Unweighted counts:   S={int(sig_mask.sum()):,}  B={int(bkg_mask.sum()):,}")
# if w_sig is not None:
#     print(f"Total test weights:  S={float(np.sum(w_sig)):.3e}  B={float(np.sum(w_bkg)):.3e}")

# bins = np.linspace(0.0, 1.0, 51)
# plt.figure()
# plt.hist(test_probs[sig_mask], bins=bins, histtype='step', linewidth=1.6, label="Signal")
# plt.hist(test_probs[bkg_mask], bins=bins, histtype='step', linewidth=1.6, label="Background")
# plt.xlabel("DNN output (probability)"); plt.ylabel("Events")
# plt.title("Signal vs Background — Test (UNWEIGHTED)")
# plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout(); plt.show()

# plt.figure()
# plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, histtype='step', linewidth=1.6, label="Signal")
# plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, histtype='step', linewidth=1.6, label="Background")
# plt.yscale('log'); plt.xlabel("DNN output (probability)"); plt.ylabel("Weighted events")
# plt.title("Signal vs Background — Test (WEIGHTED, log y)")
# plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout(); plt.show()

# plt.figure()
# plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, density=True, histtype='step', linewidth=1.6, label="Signal")
# plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, density=True, histtype='step', linewidth=1.6, label="Background")
# plt.xlabel("DNN output (probability)"); plt.ylabel("Density")
# plt.title("Signal vs Background — Test (WEIGHTED, SHAPE-NORMALIZED)")
# plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout(); plt.show()

# plt.figure()
# plt.plot(fpr, tpr, label=f"AUC = {test_auc:.4f}")
# plt.plot([0,1],[0,1],'k--',lw=1)
# plt.xlabel("False Positive Rate"); plt.ylabel("True Positive Rate")
# plt.title("ROC — Test (group-disjoint)"); plt.legend(); plt.grid(True, alpha=0.3)
# plt.tight_layout(); plt.show()

# plt.figure(); plt.plot(history["train_loss"], marker='o')
# plt.title("Training Loss"); plt.xlabel("Epoch"); plt.ylabel("Loss")
# plt.grid(True, alpha=0.3); plt.tight_layout(); plt.show()

# plt.figure(); plt.plot(history["val_auc"], marker='o', label="Val AUC")
# plt.title("Validation AUC (group-disjoint)"); plt.xlabel("Epoch"); plt.ylabel("AUC")
# plt.grid(True, alpha=0.3); plt.legend(); plt.tight_layout(); plt.show()


# # -----------------------------
# # 14) Test + diagnostics & plots (with CMS palette)
# # -----------------------------
# if os.path.exists("GATE_ABORTED"):
#     print("[INFO] Consistency gate aborted training early; proceeding with saved snapshot.")

# if os.path.exists(SAVE_MODEL_PATH):
#     try:
#         state = torch.load(SAVE_MODEL_PATH, map_location=device, weights_only=True)
#     except TypeError:
#         state = torch.load(SAVE_MODEL_PATH, map_location=device)
#     model.load_state_dict(state)
# else:
#     print("[WARN] No saved model found; using current in-memory weights.")

# test_probs = safe_eval_probs(model, X_te_t, device)

# # --- Overall ROC ---
# fpr_all, tpr_all, thr_all = roc_curve(y_te, test_probs, sample_weight=w_te)
# test_auc = auc(fpr_all, tpr_all)
# print(f"\nTest AUC (overall): {test_auc:.6f}")

# # quick check: (mass,y) only
# i_mass = available_features.index('mass'); i_y = available_features.index('y_value')
# print(f"AUC using only (mass,y) on TEST: {roc_auc_score(y_te, 0.5*X_te[:, i_mass] + 0.5*X_te[:, i_y]):.4f}")

# # masks & counts
# sig_mask = (y_te == 1); bkg_mask = (y_te == 0)
# w_sig = w_te[sig_mask] if w_te is not None else None
# w_bkg = w_te[bkg_mask] if w_te is not None else None
# print(f"\n[Separation diagnostics — TEST]")
# print(f"Unweighted counts:   S={int(sig_mask.sum()):,}  B={int(bkg_mask.sum()):,}")
# if w_sig is not None:
#     print(f"Total test weights:  S={float(np.sum(w_sig)):.3e}  B={float(np.sum(w_bkg)):.3e}")

# # ---------- Separation histograms (CMS colors) ----------
# bins = np.linspace(0.0, 1.0, 51)

# plt.figure()
# plt.hist(test_probs[sig_mask], bins=bins, histtype='step', linewidth=2.0,
#          label="Signal", color=CMS_BLUE)
# plt.hist(test_probs[bkg_mask], bins=bins, histtype='step', linewidth=2.0,
#          label="Background", color=CMS_RED)
# plt.xlabel("DNN output (probability)"); plt.ylabel("Events")
# plt.title("Signal vs Background — Test (unweighted)")
# plt.legend()
# plt.tight_layout(); plt.show()

# plt.figure()
# plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, histtype='step', linewidth=2.0,
#          label="Signal", color=CMS_BLUE)
# plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, histtype='step', linewidth=2.0,
#          label="Background", color=CMS_RED)
# plt.yscale('log'); plt.xlabel("DNN output (probability)"); plt.ylabel("Weighted events")
# plt.title("Signal vs Background — Test (weighted)")
# plt.legend()
# plt.tight_layout(); plt.show()

# plt.figure()
# plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, density=True, histtype='step', linewidth=2.0,
#          label="Signal (shape)", color=CMS_BLUE)
# plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, density=True, histtype='step', linewidth=2.0,
#          label="Background (shape)", color=CMS_RED)
# plt.xlabel("DNN output (probability)"); plt.ylabel("Density")
# plt.title("Signal vs Background — Test (weighted, shape-normalized)")
# plt.legend()
# plt.tight_layout(); plt.show()

# # ---------- ROC: overall + per-(mass,y) ----------
# # overall first
# plt.figure()
# plt.plot(fpr_all, tpr_all, label=f"All (AUC = {test_auc:.3f})", color=CMS_BLUE, lw=2.4)
# plt.plot([0,1],[0,1], linestyle='--', color=CMS_GRAY, lw=1)
# plt.xlabel("Background efficiency"); plt.ylabel("Signal efficiency")
# plt.title("ROC — Test (group-disjoint)")

# # per (mass, y): overlay thin translucent lines
# group_key = (df_te['mass'].astype(int).astype(str) + "_" +
#              df_te['y_value'].astype(int).astype(str)).values
# scores = test_probs
# labels = y_te
# weights = w_te

# # sort groups for stable legend
# uniq_groups = np.unique(group_key)
# legend_handles = []
# for g in uniq_groups:
#     idx = (group_key == g)
#     if np.unique(labels[idx]).size < 2:
#         continue
#     fpr_g, tpr_g, _ = roc_curve(labels[idx], scores[idx],
#                                 sample_weight=(weights[idx] if weights is not None else None))
#     auc_g = auc(fpr_g, tpr_g)
#     h, = plt.plot(fpr_g, tpr_g, alpha=0.35, lw=1.6, label=f"{g} (AUC {auc_g:.3f})")
#     legend_handles.append((auc_g, h))

# # only keep top ~10 groups in legend to avoid clutter
# legend_handles.sort(key=lambda t: t[0], reverse=True)
# handles_to_show = [h for _,h in legend_handles[:10]]
# labels_to_show  = [h.get_label() for h in handles_to_show]
# leg1 = plt.legend(handles_to_show, labels_to_show, title="Top groups", loc="lower right",
#                   frameon=True, fontsize=8)
# plt.gca().add_artist(leg1)
# plt.tight_layout(); plt.show()

# # ---------- Correlation heatmap (Test, unweighted) ----------
# # Build a DataFrame of the features used on TEST
# Xte_df = pd.DataFrame(X_te_raw, columns=available_features)
# # We want correlation in the original (unstandardized) scale, so use X_te_raw not X_te
# corr = Xte_df[ [c for c in available_features if c not in ("mass","y_value")] ].corr(method="pearson")
# fig, ax = plt.subplots(figsize=(8.5, 7.0), dpi=110)
# im = ax.imshow(corr.values, cmap=cms_div, vmin=-1.0, vmax=1.0, interpolation="nearest", aspect="auto")
# ax.set_xticks(np.arange(corr.shape[1]))
# ax.set_yticks(np.arange(corr.shape[0]))
# ax.set_xticklabels(corr.columns, rotation=90)
# ax.set_yticklabels(corr.index)
# ax.set_title("Pearson correlation (test, unweighted)")
# cbar = plt.colorbar(im, ax=ax)
# cbar.set_label("Correlation")
# plt.tight_layout(); plt.show()

# # ---------- Training curves ----------
# plt.figure(); plt.plot(history["train_loss"], marker='o', color=CMS_BLUE)
# plt.title("Training Loss"); plt.xlabel("Epoch"); plt.ylabel("Loss")
# plt.tight_layout(); plt.show()

# plt.figure(); 
# plt.plot(history["val_auc"], marker='o', label="Val AUC", color=CMS_RED)
# plt.title("Validation AUC (group-disjoint)"); plt.xlabel("Epoch"); plt.ylabel("AUC")
# plt.legend(); plt.tight_layout(); plt.show()




# # -----------------------------
# # 14) Test + diagnostics & plots (with CMS palette)
# # -----------------------------
# if os.path.exists("GATE_ABORTED"):
#     print("[INFO] Consistency gate aborted training early; proceeding with saved snapshot.")

# if os.path.exists(SAVE_MODEL_PATH):
#     try:
#         state = torch.load(SAVE_MODEL_PATH, map_location=device, weights_only=True)
#     except TypeError:
#         state = torch.load(SAVE_MODEL_PATH, map_location=device)
#     model.load_state_dict(state)
# else:
#     print("[WARN] No saved model found; using current in-memory weights.")

# test_probs = safe_eval_probs(model, X_te_t, device)

# # --- Overall ROC ---
# fpr_all, tpr_all, thr_all = roc_curve(y_te, test_probs, sample_weight=w_te)
# test_auc = auc(fpr_all, tpr_all)
# print(f"\nTest AUC (overall): {test_auc:.6f}")

# # quick check: (mass,y) only
# i_mass = available_features.index('mass'); i_y = available_features.index('y_value')
# print(f"AUC using only (mass,y) on TEST: {roc_auc_score(y_te, 0.5*X_te[:, i_mass] + 0.5*X_te[:, i_y]):.4f}")

# # masks & counts
# sig_mask = (y_te == 1); bkg_mask = (y_te == 0)
# w_sig = w_te[sig_mask] if w_te is not None else None
# w_bkg = w_te[bkg_mask] if w_te is not None else None
# print(f"\n[Separation diagnostics — TEST]")
# print(f"Unweighted counts:   S={int(sig_mask.sum()):,}  B={int(bkg_mask.sum()):,}")
# if w_sig is not None:
#     print(f"Total test weights:  S={float(np.sum(w_sig)):.3e}  B={float(np.sum(w_bkg)):.3e}")

# # ---------- Separation histograms (CMS colors) ----------
# bins = np.linspace(0.0, 1.0, 51)

# plt.figure()
# plt.hist(test_probs[sig_mask], bins=bins, histtype='step', linewidth=2.0,
#          label="Signal", color=CMS_BLUE)
# plt.hist(test_probs[bkg_mask], bins=bins, histtype='step', linewidth=2.0,
#          label="Background", color=CMS_RED)
# plt.xlabel("DNN output (probability)"); plt.ylabel("Events")
# plt.title("Signal vs Background — Test (unweighted)")
# plt.legend()
# plt.tight_layout(); plt.show()

# plt.figure()
# plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, histtype='step', linewidth=2.0,
#          label="Signal", color=CMS_BLUE)
# plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, histtype='step', linewidth=2.0,
#          label="Background", color=CMS_RED)
# plt.yscale('log'); plt.xlabel("DNN output (probability)"); plt.ylabel("Weighted events")
# plt.title("Signal vs Background — Test (weighted)")
# plt.legend()
# plt.tight_layout(); plt.show()

# plt.figure()
# plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, density=True, histtype='step', linewidth=2.0,
#          label="Signal (shape)", color=CMS_BLUE)
# plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, density=True, histtype='step', linewidth=2.0,
#          label="Background (shape)", color=CMS_RED)
# plt.xlabel("DNN output (probability)"); plt.ylabel("Density")
# plt.title("Signal vs Background — Test (weighted, shape-normalized)")
# plt.legend()
# plt.tight_layout(); plt.show()

# # ---------- ROC: overall + per-(mass,y) ----------
# # overall first
# plt.figure()
# plt.plot(fpr_all, tpr_all, label=f"All (AUC = {test_auc:.3f})", color=CMS_BLUE, lw=2.4)
# plt.plot([0,1],[0,1], linestyle='--', color=CMS_GRAY, lw=1)
# plt.xlabel("Background efficiency"); plt.ylabel("Signal efficiency")
# plt.title("ROC — Test (group-disjoint)")

# # per (mass, y): overlay thin translucent lines
# group_key = (df_te['mass'].astype(int).astype(str) + "_" +
#              df_te['y_value'].astype(int).astype(str)).values
# scores = test_probs
# labels = y_te
# weights = w_te

# # sort groups for stable legend
# uniq_groups = np.unique(group_key)
# legend_handles = []
# for g in uniq_groups:
#     idx = (group_key == g)
#     if np.unique(labels[idx]).size < 2:
#         continue
#     fpr_g, tpr_g, _ = roc_curve(labels[idx], scores[idx],
#                                 sample_weight=(weights[idx] if weights is not None else None))
#     auc_g = auc(fpr_g, tpr_g)
#     label = f"NMSSM_X{m}_Y{yv} (AUC {auc_g:.3f})"
#     h, = plt.plot(fpr_g, tpr_g, alpha=0.35, lw=1.6, label=label)
#     legend_handles.append((auc_g, h))

# # only keep top ~10 groups in legend to avoid clutter
# legend_handles.sort(key=lambda t: t[0], reverse=True)
# handles_to_show = [h for _,h in legend_handles[:10]]
# labels_to_show  = [h.get_label() for h in handles_to_show]
# leg1 = plt.legend(handles_to_show, labels_to_show, title="Top groups", loc="lower right",
#                   frameon=True, fontsize=8)
# plt.gca().add_artist(leg1)
# plt.tight_layout(); plt.show()

# # ---------- Correlation heatmap (Test, unweighted) ----------
# # Build a DataFrame of the features used on TEST
# Xte_df = pd.DataFrame(X_te_raw, columns=available_features)
# # We want correlation in the original (unstandardized) scale, so use X_te_raw not X_te
# corr = Xte_df[ [c for c in available_features if c not in ("mass","y_value")] ].corr(method="pearson")
# fig, ax = plt.subplots(figsize=(8.5, 7.0), dpi=110)
# im = ax.imshow(corr.values, cmap=cms_div, vmin=-1.0, vmax=1.0, interpolation="nearest", aspect="auto")
# ax.set_xticks(np.arange(corr.shape[1]))
# ax.set_yticks(np.arange(corr.shape[0]))
# ax.set_xticklabels(corr.columns, rotation=90)
# ax.set_yticklabels(corr.index)
# ax.set_title("Pearson correlation (test, unweighted)")
# cbar = plt.colorbar(im, ax=ax)
# cbar.set_label("Correlation")
# plt.tight_layout(); plt.show()

# # ---------- Training curves ----------
# plt.figure(); plt.plot(history["train_loss"], marker='o', color=CMS_BLUE)
# plt.title("Training Loss"); plt.xlabel("Epoch"); plt.ylabel("Loss")
# plt.tight_layout(); plt.show()

# plt.figure(); 
# plt.plot(history["val_auc"], marker='o', label="Val AUC", color=CMS_RED)
# plt.title("Validation AUC (group-disjoint)"); plt.xlabel("Epoch"); plt.ylabel("AUC")
# plt.legend(); plt.tight_layout(); plt.show()




#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete PDNN training pipeline w/ group-safe splits, grid search CV,
OOM-safe eval, diagnostics, and feature importance (permutation + gradients).

- Rewritten as a single, cohesive script.
- Uses (mass,y) group disjointness throughout.
- Includes per-group balancing option.
- Early stopping on fold-VAL AUC; ReduceLROnPlateau.
- Grid search over architecture + optimization.
- Retrains best config on TR+VAL; evaluates on TEST; saves artifacts.

Author: (you)
"""

# =============================
# Imports
# =============================
import os
import json
import time
import warnings
import itertools
from copy import deepcopy
from dataclasses import dataclass
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import Adam, lr_scheduler

from sklearn.model_selection import GroupShuffleSplit, GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, accuracy_score, roc_curve, auc
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import GradientBoostingClassifier

warnings.filterwarnings("ignore", category=UserWarning)

# =============================
# Matplotlib style & CMS palette
# =============================
from matplotlib.colors import LinearSegmentedColormap
from cycler import cycler

plt.rcParams.update({
    "figure.figsize": (7.5, 5.5),
    "figure.dpi": 110,
    "axes.grid": True,
    "grid.alpha": 0.30,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "lines.linewidth": 2.0,
})

CMS_BLUE   = "#2368B5"
CMS_RED    = "#C0392B"
CMS_ORANGE = "#E67E22"
CMS_GREEN  = "#2E8B57"
CMS_PURPLE = "#6C5CE7"
CMS_GRAY   = "#4D4D4D"

plt.rcParams["axes.prop_cycle"] = cycler(color=[
    CMS_BLUE, CMS_RED, CMS_ORANGE, CMS_GREEN, CMS_PURPLE, "#1ABC9C", "#8E44AD",
    "#16A085", "#D35400", "#2C3E50"
])

cms_div = LinearSegmentedColormap.from_list(
    "cms_div", ["#1f77b4", "#f7f7f7", "#d62728"], N=256
)

# =============================
# Config
# =============================
SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False

# Data handling
BACKGROUND_FRAC     = 1.0
BALANCE_PER_GROUP   = True

# Model/training defaults (can be overridden by grid)
USE_BATCHNORM       = False
BATCH_SIZE_TRAIN    = 128
LR                  = 1e-3
WEIGHT_CLIP         = 10.0
PATIENCE            = 20
MAX_EPOCHS          = 200
WEIGHT_DECAY        = 1e-4
SAVE_MODEL_PATH     = "best_pdnn.pt"  # used by plotting/diagnostics section

# Eval (OOM safety)
EVAL_BATCH          = 32768
USE_AMP_EVAL        = True
CPU_FALLBACK_ON_OOM = True

# Debug toggles
DEBUG_ONE_BATCH             = False
DEBUG_SHUFFLE_TRAIN_LABELS  = False

# Output directory for plots/artifacts
OUTDIR = "/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN"
os.makedirs(OUTDIR, exist_ok=True)

# Optional ablation
DROP_FEATURES: List[str] = []

# Mass/Y grid
mass_points = [300, 400, 500, 550, 600, 650, 700, 800, 900, 1000]
y_values    = [60, 70, 80, 90, 95, 100, 125, 150, 200]

# =============================
# Inputs
# =============================
SIG_TPL = "../../../output_parquet/final_production_Syst/merged/NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet"
background_files = [
    "../../../output_root/v3_production/samples/postEE/GGJets.parquet",
    "../../../output_root/v3_production/samples/postEE/GJetPt20To40.parquet",
    "../../../output_root/v3_production/samples/postEE/GJetPt40.parquet",
]

# =============================
# Features
# =============================
WEIGHT_COL = "weight_central"
FEATURES_CORE = [
    # photons & diphoton
    "lead_eta","lead_phi","sublead_eta","sublead_phi","eta","phi",
    # jets, dijet, HH (Res)
    "Res_lead_bjet_eta","Res_lead_bjet_phi",
    "Res_sublead_bjet_eta","Res_sublead_bjet_phi",
    "Res_dijet_eta","Res_dijet_phi",
    "Res_HHbbggCandidate_eta","Res_HHbbggCandidate_phi",
    # angular distances (Res)
    "Res_DeltaR_j1g1","Res_DeltaR_j1g2","Res_DeltaR_j2g1","Res_DeltaR_j2g2","Res_DeltaR_jg_min",
    # helicity / Collins–Soper (abs)
    "Res_CosThetaStar_gg","Res_CosThetaStar_jj","Res_CosThetaStar_CS",
    # photon ID + b-tag
    "lead_mvaID_run3","sublead_mvaID_run3",
    "Res_lead_bjet_btagPNetB","Res_sublead_bjet_btagPNetB",
    # counts & MET
    "n_leptons","n_jets","puppiMET_pt","puppiMET_phi",
    # Δφ(jet,MET)
    "Res_DeltaPhi_j1MET","Res_DeltaPhi_j2MET",
    # χ² terms
    "Res_chi_t0","Res_chi_t1",
    # raw kinematics and masses
    "Res_dijet_pt","Res_dijet_mass",
    "Res_HHbbggCandidate_pt","Res_HHbbggCandidate_mass",
    # scaled pT’s
    "Res_pholead_PtOverM","Res_phosublead_PtOverM",
    "Res_FirstJet_PtOverM","Res_SecondJet_PtOverM",
]

# Engineered features will be appended inside add_engineered_features

# =============================
# Helpers
# =============================
def downcast_float_cols(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.select_dtypes(include=['float64']).columns:
        df[c] = df[c].astype('float32')
    return df

def ensure_weight(df: pd.DataFrame, weight_col=WEIGHT_COL) -> pd.DataFrame:
    if weight_col not in df.columns:
        df[weight_col] = 1.0
    return df

def ensure_photon_mva_columns(df: pd.DataFrame) -> pd.DataFrame:
    pairs = [("lead_mvaID_run3","lead_mvaID_nano"),
             ("sublead_mvaID_run3","sublead_mvaID_nano")]
    for want, alt in pairs:
        if want not in df.columns and alt in df.columns:
            df[want] = df[alt]
    return df

def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    mHH = df.get("Res_HHbbggCandidate_mass", pd.Series(index=df.index, dtype="float32"))
    mHH = mHH.replace(0, np.nan)

    if "Res_dijet_pt" in df.columns:
        df["ptjj_over_mHH"] = df["Res_dijet_pt"] / mHH
    else:
        df["ptjj_over_mHH"] = 0.0

    if "Res_HHbbggCandidate_pt" in df.columns:
        df["ptHH_over_mHH"] = df["Res_HHbbggCandidate_pt"] / mHH
    else:
        df["ptHH_over_mHH"] = 0.0

    # ΔR(γγ)
    if all(c in df.columns for c in ["lead_phi","sublead_phi","lead_eta","sublead_eta"]):
        dphi = np.abs(df["lead_phi"] - df["sublead_phi"])
        dphi = np.where(dphi > np.pi, 2*np.pi - dphi, dphi)
        deta = df["lead_eta"] - df["sublead_eta"]
        df["DeltaR_gg"] = np.sqrt(deta**2 + dphi**2)
    else:
        df["DeltaR_gg"] = 0.0

    # absolute cos*
    for c in ["Res_CosThetaStar_gg","Res_CosThetaStar_jj","Res_CosThetaStar_CS"]:
        if c in df.columns:
            df[c] = df[c].abs()

    for c in ["ptjj_over_mHH","ptHH_over_mHH","DeltaR_gg"]:
        df[c] = df[c].fillna(0)

    return df

# feature list including engineered ones
FEATURES_CORE = FEATURES_CORE + ["ptjj_over_mHH","ptHH_over_mHH"]  # keep DeltaR_gg for audit only if desired
FEATURES_FINAL = FEATURES_CORE + ["mass","y_value"]


def df_to_arrays(df: pd.DataFrame, feature_list: List[str]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    Xdf = df[feature_list].copy()
    Xdf = Xdf.fillna(Xdf.mean(numeric_only=True))
    Xdf = downcast_float_cols(Xdf)
    X = Xdf.values
    y = df['label'].astype(np.int8).values
    w = df[WEIGHT_COL].astype('float32').values
    return X, y, w


def balance_per_group(df: pd.DataFrame, seed: int = SEED, min_per_class: int = 1) -> pd.DataFrame:
    key = df['mass'].astype(int).astype(str) + "_" + df['y_value'].astype(int).astype(str)
    parts = []; dropped = 0
    for _, sub in df.groupby(key, sort=False):
        vc = sub['label'].value_counts()
        if len(vc) < 2: dropped += 1; continue
        n_min = vc.min()
        if n_min < min_per_class: dropped += 1; continue
        s = sub[sub['label']==1]; b = sub[sub['label']==0]
        s_keep = s.sample(n=n_min, random_state=seed) if len(s)>n_min else s
        b_keep = b.sample(n=n_min, random_state=seed) if len(b)>n_min else b
        parts.append(pd.concat([s_keep, b_keep], ignore_index=True))
    if not parts:
        raise RuntimeError("Per-group balancing removed all groups; relax constraints or inspect data.")
    out = pd.concat(parts, ignore_index=True).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    if dropped: print(f"[INFO] balance_per_group: dropped {dropped} tiny/pure groups in this split.")
    return out


def split_summary(df: pd.DataFrame, name: str) -> None:
    key = df['mass'].astype(int).astype(str) + "_" + df['y_value'].astype(int).astype(str)
    print(f"{name}: N={len(df):,}  counts={df['label'].value_counts().to_dict()}  groups={key.nunique()}")


def check_groups(df: pd.DataFrame, name: str) -> None:
    groups = df['mass'].astype(int).astype(str) + "_" + df['y_value'].astype(int).astype(str)
    bad = [(k, int(g['label'].iloc[0]), len(g)) for k,g in df.groupby(groups) if g['label'].nunique()<2]
    if bad:
        print(f"[WARN] {name}: {len(bad)} pure (mass,y) groups remain. Examples: {bad[:5]}")
    assert df['label'].nunique()==2, f"{name} has only one class!"

@torch.no_grad()
def predict_batched(model: nn.Module, X_tensor: torch.Tensor, device: torch.device, batch: int = 32768, use_amp: bool = True) -> np.ndarray:
    model.eval()
    N = X_tensor.shape[0]
    out = np.empty(N, dtype=np.float32)
    amp_ctx = torch.amp.autocast(device_type=device.type, enabled=(use_amp and device.type=="cuda"))
    with amp_ctx:
        for i in range(0, N, batch):
            xb = X_tensor[i:i+batch].to(device, non_blocking=True)
            logits = model(xb).view(-1)
            out[i:i+batch] = torch.sigmoid(logits).detach().cpu().numpy()
    return out


def safe_eval_probs(model: nn.Module, X_tensor: torch.Tensor, device: torch.device) -> np.ndarray:
    try:
        return predict_batched(model, X_tensor, device, batch=EVAL_BATCH, use_amp=USE_AMP_EVAL)
    except RuntimeError as e:
        if CPU_FALLBACK_ON_OOM and "CUDA out of memory" in str(e):
            print("[WARN] CUDA OOM during eval → falling back to CPU (batched).")
            cpu_model = model.to(torch.device("cpu"))
            X_cpu = X_tensor.to(torch.device("cpu"))
            return predict_batched(cpu_model, X_cpu, torch.device("cpu"), batch=max(8192, EVAL_BATCH), use_amp=False)
        raise

# =============================
# Data loading
# =============================
def load_signal() -> pd.DataFrame:
    rows = []
    for mass in mass_points:
        for y in y_values:
            fp = SIG_TPL.format(m=mass, y=y)
            if not os.path.exists(fp):
                continue
            try:
                try:
                    cols = pd.read_parquet(fp, columns=None).columns
                    need_raw = [
                        "lead_eta","lead_phi","sublead_eta","sublead_phi","eta","phi",
                        "Res_lead_bjet_eta","Res_lead_bjet_phi",
                        "Res_sublead_bjet_eta","Res_sublead_bjet_phi",
                        "Res_dijet_eta","Res_dijet_phi",
                        "Res_HHbbggCandidate_eta","Res_HHbbggCandidate_phi",
                        "Res_pholead_PtOverM","Res_phosublead_PtOverM",
                        "Res_FirstJet_PtOverM","Res_SecondJet_PtOverM",
                        "Res_DeltaR_j1g1","Res_DeltaR_j1g2","Res_DeltaR_j2g1","Res_DeltaR_j2g2","Res_DeltaR_jg_min",
                        "Res_CosThetaStar_gg","Res_CosThetaStar_jj","Res_CosThetaStar_CS",
                        "lead_mvaID_run3","sublead_mvaID_run3",
                        "lead_mvaID_nano","sublead_mvaID_nano",
                        "Res_lead_bjet_btagPNetB","Res_sublead_bjet_btagPNetB",
                        "n_leptons","n_jets","puppiMET_pt","puppiMET_phi",
                        "Res_chi_t0","Res_chi_t1",
                        "Res_dijet_pt","Res_HHbbggCandidate_pt","Res_HHbbggCandidate_mass",
                    ]
                    subset = [c for c in (set(need_raw) | {WEIGHT_COL}) if c in cols]
                    df = pd.read_parquet(fp, columns=subset)
                except Exception:
                    df = pd.read_parquet(fp)
                df = ensure_photon_mva_columns(df)
                df = add_engineered_features(df)
                keep = [c for c in FEATURES_CORE if c in df.columns]
                extras = [WEIGHT_COL] if WEIGHT_COL in df.columns else []
                df = df[keep + extras].copy()
                df['mass']=mass; df['y_value']=y; df['label']=1
                df = ensure_weight(df); df = downcast_float_cols(df)
                rows.append(df)
            except Exception as e:
                print(f"[WARN] read fail {fp}: {e}")
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def load_background() -> pd.DataFrame:
    parts = []
    for file_path in background_files:
        if not os.path.exists(file_path):
            print(f"[WARN] Missing {file_path}")
            continue
        try:
            try:
                cols = pd.read_parquet(file_path, columns=None).columns
                need_raw = [
                    "lead_eta","lead_phi","sublead_eta","sublead_phi","eta","phi",
                    "Res_lead_bjet_eta","Res_lead_bjet_phi",
                    "Res_sublead_bjet_eta","Res_sublead_bjet_phi",
                    "Res_dijet_eta","Res_dijet_phi",
                    "Res_HHbbggCandidate_eta","Res_HHbbggCandidate_phi",
                    "Res_pholead_PtOverM","Res_phosublead_PtOverM",
                    "Res_FirstJet_PtOverM","Res_SecondJet_PtOverM",
                    "Res_DeltaR_j1g1","Res_DeltaR_j1g2","Res_DeltaR_j2g1","Res_DeltaR_j2g2","Res_DeltaR_jg_min",
                    "Res_CosThetaStar_gg","Res_CosThetaStar_jj","Res_CosThetaStar_CS",
                    "lead_mvaID_run3","sublead_mvaID_run3",
                    "lead_mvaID_nano","sublead_mvaID_nano",
                    "Res_lead_bjet_btagPNetB","Res_sublead_bjet_btagPNetB",
                    "n_leptons","n_jets","puppiMET_pt","puppiMET_phi",
                    "Res_chi_t0","Res_chi_t1",
                    "Res_dijet_pt","Res_HHbbggCandidate_pt","Res_HHbbggCandidate_mass",
                ]
                subset = [c for c in (set(need_raw) | {WEIGHT_COL}) if c in cols]
                dfb = pd.read_parquet(file_path, columns=subset)
            except Exception:
                dfb = pd.read_parquet(file_path)
            dfb = ensure_photon_mva_columns(dfb)
            dfb = add_engineered_features(dfb)
            keep = [c for c in FEATURES_CORE if c in dfb.columns]
            extras = [WEIGHT_COL] if WEIGHT_COL in dfb.columns else []
            dfb = dfb[keep + extras].copy()
            dfb = ensure_weight(dfb)
            dfb['label'] = 0
            dfb = downcast_float_cols(dfb)
            parts.append(dfb)
        except Exception as e:
            print(f"[WARN] read fail {file_path}: {e}")
    df_background = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if BACKGROUND_FRAC < 1.0 and not df_background.empty:
        df_background = df_background.sample(frac=BACKGROUND_FRAC, random_state=SEED).reset_index(drop=True)
    return df_background

# =============================
# Model
# =============================
activation_map = {
    "ReLU": nn.ReLU,
    "LeakyReLU": lambda: nn.LeakyReLU(negative_slope=0.1),
    "GELU": nn.GELU,
}


def maybe_bn(n: int, use_bn: bool) -> nn.Module:
    return nn.BatchNorm1d(n) if use_bn else nn.Identity()


class PDNN(nn.Module):
    def __init__(self, d_in: int, hidden: List[int], dropout: float, act: str, use_bn: bool):
        super().__init__()
        layers = []
        prev = d_in
        Act = activation_map.get(act, nn.ReLU)
        for h in hidden:
            layers += [nn.Linear(prev, h), maybe_bn(h, use_bn), Act(), nn.Dropout(dropout)]
            prev = h
        layers += [nn.Linear(prev, 1)]  # logits
        self.net = nn.Sequential(*layers)
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def small_normal_zero_bias_(m: nn.Module) -> None:
    if isinstance(m, nn.Linear):
        nn.init.normal_(m.weight, mean=0.0, std=1e-2)
        if m.bias is not None:
            nn.init.constant_(m.bias, 0.0)

# =============================
# Training utilities
# =============================
@dataclass
class TrainConfig:
    layers: List[int]
    dropout: float
    activation: str
    batchnorm: bool
    lr: float
    weight_decay: float
    batch_size: int
    patience: int
    max_epochs: int


class ArrayDataset(Dataset):
    def __init__(self, X, y, w):
        self.X, self.y, self.w = X, y, w
    def __len__(self):
        return len(self.X)
    def __getitem__(self, i: int):
        return (torch.tensor(self.X[i], dtype=torch.float32),
                torch.tensor(self.y[i], dtype=torch.float32),
                torch.tensor(self.w[i], dtype=torch.float32))


@torch.no_grad()
def eval_auc(model: nn.Module, X: np.ndarray, y: np.ndarray, w: np.ndarray, device: torch.device) -> float:
    X_t = torch.tensor(X, dtype=torch.float32, device=device)
    probs = safe_eval_probs(model, X_t, device)
    return float(roc_auc_score(y, probs, sample_weight=(w if w is not None else None)))


def train_one_fold(X_tr, y_tr, w_tr, X_va, y_va, w_va, d_in: int, cfg: TrainConfig, device: torch.device):
    loader = DataLoader(ArrayDataset(X_tr, y_tr, w_tr), batch_size=cfg.batch_size,
                        shuffle=True, pin_memory=(device.type=="cuda"), num_workers=2 if os.name!="nt" else 0)
    model = PDNN(d_in, cfg.layers, cfg.dropout, cfg.activation, cfg.batchnorm).to(device)
    model.apply(small_normal_zero_bias_)

    criterion = nn.BCEWithLogitsLoss(reduction='none')
    optim = Adam(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    sched = lr_scheduler.ReduceLROnPlateau(optim, mode='max', factor=0.5, patience=max(3, cfg.patience//3))
    use_amp = (device.type == "cuda")
    scaler_amp = torch.amp.GradScaler("cuda", enabled=use_amp) if use_amp else torch.amp.GradScaler(enabled=False)

    best_auc, best_state, epochs_since = -np.inf, None, 0
    history = {"train_loss": [], "val_auc": [], "val_acc": []}

    for epoch in range(cfg.max_epochs):
        model.train()
        tot, nseen = 0.0, 0
        for xb, yb, wb in loader:
            xb = xb.to(device, non_blocking=True)
            yb = yb.to(device, non_blocking=True)
            wb = torch.clamp(wb.to(device, non_blocking=True) / (wb.mean() + 1e-8), max=WEIGHT_CLIP)

            optim.zero_grad(set_to_none=True)
            with torch.amp.autocast(device_type=device.type, enabled=use_amp):
                logits = model(xb).view(-1)
                per_loss = criterion(logits, yb)
                loss = (per_loss * wb).mean()
            scaler_amp.scale(loss).backward()
            scaler_amp.step(optim)
            scaler_amp.update()

            bs = xb.size(0); tot += float(loss.item()) * bs; nseen += bs
            if DEBUG_ONE_BATCH: break

        train_loss = tot / max(nseen, 1)
        va_auc = eval_auc(model, X_va, y_va, w_va, device)
        with torch.no_grad():
            Xv_t = torch.tensor(X_va, dtype=torch.float32, device=device)
            pv = safe_eval_probs(model, Xv_t, device)
            va_acc = float(accuracy_score(y_va, (pv > 0.5).astype(int)))

        history["train_loss"].append(train_loss)
        history["val_auc"].append(va_auc)
        history["val_acc"].append(va_acc)

        print(f"Epoch {epoch+1:02d} | TrainLoss: {train_loss:.4f} | ValAUC: {va_auc:.4f} | ValAcc: {va_acc:.4f}")
        sched.step(va_auc)

        if va_auc > best_auc + 1e-4:
            best_auc, best_state, epochs_since = va_auc, deepcopy(model.state_dict()), 0
        else:
            epochs_since += 1
            if epochs_since >= cfg.patience:
                print(f"[INFO] Early stopping at epoch {epoch+1}.")
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, best_auc, history

# =============================
# Grid search CV
# =============================
def run_grid_search(df_trval: pd.DataFrame, available_features: List[str], device: torch.device,
                    k_folds: int = 3, seed: int = SEED,
                    param_grid: Dict = None,
                    results_csv: str = "grid_results_pdnn.csv"):

    if param_grid is None:
        param_grid = {
            "layers":      [[256,128,64], [128,64,32], [256,128], [128,128,64]],
            "dropout":     [0.2, 0.3],
            "activation":  ["ReLU", "LeakyReLU"],
            "batchnorm":   [False],
            "lr":          [1e-3, 5e-4],
            "weight_decay":[1e-5, 1e-4, 5e-4],
            "batch_size":  [128, 256],
            "patience":    [15, 20],
            "max_epochs":  [150, 200],
        }

    keys = list(param_grid.keys())
    search_space = [dict(zip(keys, vals)) for vals in itertools.product(*[param_grid[k] for k in keys])]
    print(f"[Grid] Total configs: {len(search_space)}")

    gkf = GroupKFold(n_splits=k_folds)
    groups = df_trval['mass'].astype(int).astype(str) + "_" + df_trval['y_value'].astype(int).astype(str)

    # Results collector
    recs = []

    for ci, cfg_dict in enumerate(search_space, 1):
        cfg = TrainConfig(**cfg_dict)
        fold_aucs = []

        # Reproducibility
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)

        for fold, (tr_idx, va_idx) in enumerate(gkf.split(df_trval, df_trval['label'], groups), 1):
            dtr = df_trval.iloc[tr_idx].reset_index(drop=True)
            dva = df_trval.iloc[va_idx].reset_index(drop=True)

            if BALANCE_PER_GROUP:
                dtr = balance_per_group(dtr)
                dva = balance_per_group(dva)

            Xtr_raw, ytr, wtr = df_to_arrays(dtr, available_features)
            Xva_raw, yva, wva = df_to_arrays(dva, available_features)
            scaler = StandardScaler().fit(Xtr_raw)
            Xtr = scaler.transform(Xtr_raw)
            Xva = scaler.transform(Xva_raw)

            model_f, auc_f, _ = train_one_fold(Xtr, ytr, wtr, Xva, yva, wva, Xtr.shape[1], cfg, device)
            fold_aucs.append(auc_f)

        mean_auc = float(np.mean(fold_aucs))
        std_auc  = float(np.std(fold_aucs, ddof=1)) if len(fold_aucs) > 1 else 0.0
        rec = {**cfg_dict, "cv_auc_mean": mean_auc, "cv_auc_std": std_auc}
        recs.append(rec)
        print(f"[Grid {ci:>3}/{len(search_space)}] AUC={mean_auc:.4f}±{std_auc:.4f} | cfg={cfg_dict}")

    res_df = pd.DataFrame(recs).sort_values(["cv_auc_mean"], ascending=[False])
    res_df.to_csv(results_csv, index=False)
    print(f"[Saved] {results_csv}")
    best = res_df.iloc[0].to_dict()
    print("[Best @ CV]", {k: best[k] for k in ["cv_auc_mean","cv_auc_std"]})
    print("[Best cfg]", {k: best[k] for k in keys})
    return best, res_df

# =============================
# Diagnostics & plotting
# =============================
def leakage_audit(X_va: np.ndarray, y_va: np.ndarray, available_features: List[str]) -> None:
    print("\n[Leakage audit on VAL] per-feature AUC:")
    for i, f in enumerate(available_features):
        auc_f = roc_auc_score(y_va, X_va[:, i])
        flag = " <-- suspicious" if (auc_f > 0.95 or auc_f < 0.05) else ""
        print(f"{f:24s} AUC={auc_f:.4f}{flag}")
    i_mass = available_features.index('mass'); i_y = available_features.index('y_value')
    print(f"AUC using only (mass,y) on VAL: {roc_auc_score(y_va, 0.5*X_va[:, i_mass] + 0.5*X_va[:, i_y]):.4f}")


def separation_and_roc_plots(y_te, w_te, test_probs, df_te, X_te_raw, available_features, outdir: str = OUTDIR):
    fpr, tpr, _ = roc_curve(y_te, test_probs)
    test_auc = auc(fpr, tpr)
    print(f"\nTest AUC: {test_auc:.6f}")

    i_mass = available_features.index('mass'); i_y = available_features.index('y_value')
    X_te = StandardScaler().fit_transform(X_te_raw)  # quick scale for mass/y check magnitude
    print(f"AUC using only (mass,y) on TEST: {roc_auc_score(y_te, 0.5*X_te[:, i_mass] + 0.5*X_te[:, i_y]):.4f}")

    sig_mask = (y_te == 1); bkg_mask = (y_te == 0)
    w_sig = w_te[sig_mask] if w_te is not None else None
    w_bkg = w_te[bkg_mask] if w_te is not None else None
    print(f"\n[Separation diagnostics — TEST]")
    print(f"Unweighted counts:   S={int(sig_mask.sum()):,}  B={int(bkg_mask.sum()):,}")
    if w_sig is not None:
        print(f"Total test weights:  S={float(np.sum(w_sig)):.3e}  B={float(np.sum(w_bkg)):.3e}")

    bins = np.linspace(0.0, 1.0, 51)

    plt.figure()
    plt.hist(test_probs[sig_mask], bins=bins, histtype='step', linewidth=1.6, label="Signal")
    plt.hist(test_probs[bkg_mask], bins=bins, histtype='step', linewidth=1.6, label="Background")
    plt.xlabel("DNN output (probability)"); plt.ylabel("Events")
    plt.title("Signal vs Background — Test (UNWEIGHTED)")
    plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout()
    plt.savefig(os.path.join(outdir, "Signal_vs_Background—Test(UNWEIGHTED).png"), dpi=600)
    plt.savefig(os.path.join(outdir, "Signal_vs_Background—Test(UNWEIGHTED).pdf"))
    plt.show()

    plt.figure()
    plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, histtype='step', linewidth=1.6, label="Signal")
    plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, histtype='step', linewidth=1.6, label="Background")
    plt.yscale('log'); plt.xlabel("DNN output (probability)"); plt.ylabel("Weighted events")
    plt.title("Signal vs Background — Test (WEIGHTED, log y)")
    plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout()
    plt.savefig(os.path.join(outdir, "Signal_vs_Background—Test_log(WEIGHTED).png"), dpi=600)
    plt.savefig(os.path.join(outdir, "Signal_vs_Background—Test_log(WEIGHTED).pdf"))
    plt.show()

    plt.figure()
    plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, density=True, histtype='step', linewidth=1.6, label="Signal")
    plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, density=True, histtype='step', linewidth=1.6, label="Background")
    plt.xlabel("DNN output (probability)"); plt.ylabel("Density")
    plt.title("Signal vs Background — Test (WEIGHTED, SHAPE-NORMALIZED)")
    plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout()
    plt.savefig(os.path.join(outdir, "Signal_vs_Background—Test(WEIGHTED).png"), dpi=600)
    plt.savefig(os.path.join(outdir, "Signal_vs_Background—Test(WEIGHTED).pdf"))
    plt.show()

    plt.figure()
    plt.plot(fpr, tpr, label=f"AUC = {test_auc:.4f}")
    plt.plot([0,1],[0,1],'k--',lw=1)
    plt.xlabel("False Positive Rate"); plt.ylabel("True Positive Rate")
    plt.title("ROC — Test (group-disjoint)"); plt.legend(); plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "ROC.png"), dpi=600)
    plt.savefig(os.path.join(outdir, "ROC.pdf"))
    plt.show()

    # Per-group ROC overlay (top 10)
    group_key = (df_te['mass'].astype(int).astype(str) + "_" + df_te['y_value'].astype(int).astype(str)).values
    scores = test_probs
    labels = y_te
    weights = w_te

    plt.figure()
    fpr_all, tpr_all, _ = roc_curve(labels, scores, sample_weight=weights)
    auc_all = auc(fpr_all, tpr_all)
    plt.plot(fpr_all, tpr_all, label=f"All (AUC = {auc_all:.3f})", color=CMS_BLUE, lw=2.4)
    plt.plot([0,1],[0,1], linestyle='--', color=CMS_GRAY, lw=1)

    uniq_groups = np.unique(group_key)
    legend_handles = []
    for g in uniq_groups:
        idx = (group_key == g)
        if np.unique(labels[idx]).size < 2:
            continue
        fpr_g, tpr_g, _ = roc_curve(labels[idx], scores[idx], sample_weight=(weights[idx] if weights is not None else None))
        auc_g = auc(fpr_g, tpr_g)
        h, = plt.plot(fpr_g, tpr_g, alpha=0.35, lw=1.6, label=f"{g} (AUC {auc_g:.3f})")
        legend_handles.append((auc_g, h))

    legend_handles.sort(key=lambda t: t[0], reverse=True)
    handles_to_show = [h for _,h in legend_handles[:10]]
    labels_to_show  = [h.get_label() for h in handles_to_show]
    leg1 = plt.legend(handles_to_show, labels_to_show, title="Top groups", loc="lower right", frameon=True, fontsize=8)
    plt.gca().add_artist(leg1)
    plt.xlabel("Background efficiency"); plt.ylabel("Signal efficiency")
    plt.title("ROC — Test (group-disjoint)")
    plt.tight_layout(); plt.show()

    # Correlation heatmap (unstandardized)
    Xte_df = pd.DataFrame(X_te_raw, columns=available_features)
    corr = Xte_df[[c for c in available_features if c not in ("mass","y_value")]].corr(method="pearson")
    fig, ax = plt.subplots(figsize=(8.5, 7.0), dpi=110)
    im = ax.imshow(corr.values, cmap=cms_div, vmin=-1.0, vmax=1.0, interpolation="nearest", aspect="auto")
    ax.set_xticks(np.arange(corr.shape[1])); ax.set_yticks(np.arange(corr.shape[0]))
    ax.set_xticklabels(corr.columns, rotation=90); ax.set_yticklabels(corr.index)
    ax.set_title("Pearson correlation (test, unweighted)")
    cbar = plt.colorbar(im, ax=ax); cbar.set_label("Correlation")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "variable_correlation.png"), dpi=600)
    plt.savefig(os.path.join(outdir, "variable_correlation.pdf"))
    plt.show()

# =============================
# Feature importance
# =============================
from collections import defaultdict

def _weighted_auc(y, p, w=None):
    return roc_auc_score(y, p, sample_weight=(w if w is not None else None))


def _groupwise_shuffle_inplace(X_block, groups, col, rng):
    groups = np.asarray(groups)
    if groups.ndim == 2:
        uniq = np.unique(groups, axis=0)
        for g in uniq:
            idx = np.all(groups == g, axis=1)
            vals = X_block[idx, col].copy(); rng.shuffle(vals); X_block[idx, col] = vals
    else:
        for g in np.unique(groups):
            idx = (groups == g)
            vals = X_block[idx, col].copy(); rng.shuffle(vals); X_block[idx, col] = vals


@torch.no_grad()
def permutation_importance_auc(model, X, y, w, feature_names, device, groups=None,
                               n_repeats=5, batch=EVAL_BATCH, use_amp=USE_AMP_EVAL, seed=SEED):
    X_t = torch.tensor(X, dtype=torch.float32, device=device)
    base_probs = safe_eval_probs(model, X_t, device)
    base_auc = _weighted_auc(y, base_probs, w)
    rng = np.random.default_rng(seed)
    drops = defaultdict(list)

    for j, f in enumerate(feature_names):
        for _ in range(n_repeats):
            X_perm = X.copy()
            if groups is None:
                rng.shuffle(X_perm[:, j])
            else:
                _groupwise_shuffle_inplace(X_perm, groups, j, rng)
            Xp_t = torch.tensor(X_perm, dtype=torch.float32, device=device)
            probs_p = safe_eval_probs(model, Xp_t, device)
            auc_p = _weighted_auc(y, probs_p, w)
            drops[f].append(base_auc - auc_p)

    imp_mean = {f: float(np.mean(v)) for f, v in drops.items()}
    imp_std  = {f: float(np.std(v, ddof=1)) for f, v in drops.items()}
    return base_auc, imp_mean, imp_std


def gradient_saliency(model, X, feature_names, device, scaler=None, batch=4096):
    model.eval()
    N, D = X.shape
    grads_accum = np.zeros(D, dtype=np.float64); n_seen = 0

    if scaler is not None and hasattr(scaler, "scale_"):
        inv_scale = 1.0 / np.asarray(scaler.scale_)
        inv_scale = inv_scale[[available_features.index(f) for f in feature_names]]
    else:
        inv_scale = np.ones(D, dtype=np.float64)

    ptr = 0
    while ptr < N:
        xb = torch.tensor(X[ptr:ptr+batch], dtype=torch.float32, device=device, requires_grad=True)
        logits = model(xb).view(-1)
        s = logits.sum(); s.backward()
        g = xb.grad.detach().abs().mean(dim=0).double().cpu().numpy()
        grads_accum += g; n_seen += 1; ptr += batch
        model.zero_grad(set_to_none=True)

    grads_mean = grads_accum / max(n_seen, 1)
    grads_raw = grads_mean * inv_scale
    return {f: float(val) for f, val in zip(feature_names, grads_raw)}


def plot_importance_bar(imp_mean, imp_err, title, filename, top_k=25, cms_color=CMS_BLUE):
    items = sorted(imp_mean.items(), key=lambda t: t[1], reverse=True)[:top_k]
    labels = [k for k,_ in items][::-1]
    vals   = [imp_mean[k] for k in labels]
    errs   = [imp_err.get(k, 0.0) for k in labels]

    plt.figure(figsize=(8.0, 0.4*len(labels)+1.5), dpi=110)
    plt.barh(range(len(labels)), vals, xerr=errs, color=cms_color, alpha=0.85)
    plt.yticks(range(len(labels)), labels)
    plt.xlabel("Mean AUC drop (permutation)")
    plt.title(title)
    plt.tight_layout()
    png = os.path.join(OUTDIR, f"{filename}.png"); pdf = os.path.join(OUTDIR, f"{filename}.pdf")
    plt.savefig(png, dpi=600); plt.savefig(pdf)
    plt.show(); print(f"[Saved] {png}\n[Saved] {pdf}")

# =============================
# Main
# =============================

def main():
    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Using device: {device}")

    # Load data
    signal_df = load_signal()
    df_background = load_background()
    if signal_df.empty or df_background.empty:
        raise RuntimeError(f"Empty data: signal={signal_df.empty}, background={df_background.empty}")

    # Assign (mass,y) to background ~ signal mix, ensure coverage
    sig_my = signal_df[['mass','y_value']]
    mix = sig_my.value_counts(normalize=True).reset_index(); mix.columns = ['mass','y_value','weight']
    sampled = mix.sample(n=len(df_background), replace=True, weights='weight', random_state=SEED).reset_index(drop=True)
    df_background['mass']    = sampled['mass'].values
    df_background['y_value'] = sampled['y_value'].values

    need = set(map(tuple, sig_my.drop_duplicates().values.tolist()))
    have = set(map(tuple, df_background[['mass','y_value']].drop_duplicates().values.tolist()))
    missing_keys = list(need - have)
    if missing_keys:
        K = min(len(missing_keys), len(df_background))
        for i,(m,y) in enumerate(missing_keys[:K]):
            df_background.loc[i,'mass']=m
            df_background.loc[i,'y_value']=y

    # Combine & drop pure groups
    df_all = pd.concat([signal_df, df_background], ignore_index=True)
    key_all = df_all['mass'].astype(int).astype(str) + "_" + df_all['y_value'].astype(int).astype(str)
    grp_nuniq = df_all.groupby(key_all)['label'].nunique()
    good_keys = set(grp_nuniq[grp_nuniq==2].index)
    mask_good = key_all.isin(good_keys)
    dropped = int((~mask_good).sum())
    if dropped: print(f"[INFO] Dropping {dropped} rows from pure (mass,y) groups before split.")
    df_all = df_all.loc[mask_good].reset_index(drop=True)

    # Features (final) + ablation
    FEATURES_FINAL = FEATURES_CORE + ['mass','y_value']
    if DROP_FEATURES:
        removed = [f for f in DROP_FEATURES if f in FEATURES_FINAL]
        if removed:
            print(f"[Ablation] Dropping features: {removed}")
            FEATURES_FINAL = [f for f in FEATURES_FINAL if f not in removed]
    available_features = [c for c in FEATURES_FINAL if c in df_all.columns]
    missing = sorted(set(FEATURES_FINAL) - set(available_features))
    if missing: print(f"[Note] Missing features ignored: {missing}")

    # Group splits – outer: TR+VAL vs TEST; inner: TR vs VAL
    groups_all = df_all['mass'].astype(int).astype(str) + "_" + df_all['y_value'].astype(int).astype(str)
    gss_outer = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=SEED)
    idx_trval, idx_te = next(gss_outer.split(df_all, df_all['label'], groups_all))
    df_trval = df_all.iloc[idx_trval].reset_index(drop=True)
    df_te    = df_all.iloc[idx_te].reset_index(drop=True)

    gss_inner = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=SEED)
    groups_trval = df_trval['mass'].astype(int).astype(str) + "_" + df_trval['y_value'].astype(int).astype(str)
    idx_tr, idx_va = next(gss_inner.split(df_trval, df_trval['label'], groups_trval))
    df_tr = df_trval.iloc[idx_tr].reset_index(drop=True)
    df_va = df_trval.iloc[idx_va].reset_index(drop=True)

    if BALANCE_PER_GROUP:
        df_tr = balance_per_group(df_tr)
        df_va = balance_per_group(df_va)
        df_te = balance_per_group(df_te)

    split_summary(df_tr, "TRAIN"); split_summary(df_va, "VAL"); split_summary(df_te, "TEST")
    check_groups(df_tr, "TRAIN"); check_groups(df_va, "VAL"); check_groups(df_te, "TEST")

    set_tr = set((df_tr['mass'].astype(int).astype(str)+"_"+df_tr['y_value'].astype(int).astype(str)).unique())
    set_va = set((df_va['mass'].astype(int).astype(str)+"_"+df_va['y_value'].astype(int).astype(str)).unique())
    set_te = set((df_te['mass'].astype(int).astype(str)+"_"+df_te['y_value'].astype(int).astype(str)).unique())
    print("Overlap Train∩Val:", len(set_tr & set_va))
    print("Overlap Train∩Test:", len(set_tr & set_te))
    print("Overlap Val∩Test:", len(set_va & set_te))

    # Arrays + scaling (fit on TRAIN only)
    X_tr_raw, y_tr, w_tr = df_to_arrays(df_tr, available_features)
    X_va_raw, y_va, w_va = df_to_arrays(df_va, available_features)
    X_te_raw, y_te, w_te = df_to_arrays(df_te, available_features)

    if DEBUG_SHUFFLE_TRAIN_LABELS:
        rng = np.random.default_rng(SEED+7)
        y_tr = rng.permutation(y_tr.copy())
        print("[DEBUG] Shuffled TRAIN labels. Val AUC should ≈ 0.5.")

    scaler = StandardScaler(); X_tr = scaler.fit_transform(X_tr_raw); X_va = scaler.transform(X_va_raw); X_te = scaler.transform(X_te_raw)

    # Save scaler + features
    with open("scaler.pkl", "wb") as f:
        import pickle; pickle.dump(scaler, f)
    with open("features_used.json", "w") as f:
        json.dump({"features": available_features}, f, indent=2)
    print("[INFO] Saved scaler to scaler.pkl and feature list to features_used.json")

    # Leakage audit
    leakage_audit(X_va, y_va, available_features)

    # Sanity checks
    X_va_t_cpu = torch.tensor(X_va, dtype=torch.float32)
    mae = float(np.mean(np.abs(X_va_t_cpu.numpy() - X_va))); mx  = float(np.max(np.abs(X_va_t_cpu.numpy() - X_va)))
    print(f"[Sanity-0] X_va tensor vs numpy: mean|diff|={mae:.3e}, max|diff|={mx:.3e} (expect ~0)")
    p_const = np.full_like(y_va, 0.5, dtype=np.float32)
    print(f"[Sanity-1] Constant 0.5 predictor AUC: {roc_auc_score(y_va, p_const):.4f} (expect 0.5)")

    class IdentityNet(nn.Module):
        def __init__(self, d):
            super().__init__(); self.fc = nn.Linear(d, 1)
        def forward(self, x): return self.fc(x)
    lin_model = IdentityNet(X_tr.shape[1]).cpu()
    nn.init.kaiming_uniform_(lin_model.fc.weight, a=0.0, nonlinearity='linear'); nn.init.constant_(lin_model.fc.bias, 0.0)
    with torch.no_grad():
        z_lin = lin_model(X_va_t_cpu).view(-1); p_lin = torch.sigmoid(z_lin).numpy()
    print(f"[Sanity-2] Linear head only AUC: {roc_auc_score(y_va, p_lin):.4f} (should be ~0.5)")

    # Baselines on VAL
    lr = LogisticRegression(max_iter=300); lr.fit(X_tr, y_tr)
    auc_lr = roc_auc_score(y_va, lr.predict_proba(X_va)[:,1])
    dt = DecisionTreeClassifier(max_depth=3, random_state=SEED); dt.fit(X_tr, y_tr)
    auc_dt = roc_auc_score(y_va, dt.predict_proba(X_va)[:,1])
    gb = GradientBoostingClassifier(random_state=SEED); gb.fit(X_tr, y_tr)
    auc_gb = roc_auc_score(y_va, gb.predict_proba(X_va)[:,1])
    print(f"[Diag] Logistic regression Val AUC: {auc_lr:.4f}")
    print(f"[Diag] DecisionTree(max_depth=3) Val AUC: {auc_dt:.4f}")
    print(f"[Diag] GradientBoosting Val AUC: {auc_gb:.4f}")

    BASELINE_MAX = max(auc_lr, auc_dt, auc_gb)
    enable_consistency_gate = (BASELINE_MAX <= 0.55)
    if enable_consistency_gate:
        print(f"[Gate] Baselines are weak (max={BASELINE_MAX:.3f}). If DNN ValAUC exceeds 0.98, we'll abort and dump diagnostics.")

    # ===== Grid Search (group-disjoint CV on df_trval) =====
    best_cfg, grid_df = run_grid_search(df_trval, available_features, device, k_folds=3, seed=SEED,
                                        results_csv=os.path.join(OUTDIR, "grid_results_pdnn.csv"))

    # Retrain best on full TR+VAL (with per-group balance)
    full = deepcopy(df_trval)
    if BALANCE_PER_GROUP:
        full = balance_per_group(full)
    Xf_raw, yf, wf = df_to_arrays(full, available_features)
    scaler_best = StandardScaler().fit(Xf_raw)
    Xf = scaler_best.transform(Xf_raw)

    cfg = TrainConfig(**{k: best_cfg[k] for k in ["layers","dropout","activation","batchnorm","lr","weight_decay","batch_size","patience","max_epochs"]})
    device_local = device
    model_best, _, _ = train_one_fold(Xf, yf, wf, Xf, yf, wf, Xf.shape[1], cfg, device_local)

    # Save best model + scaler
    import pickle
    BEST_SAVE_PATH = os.path.join(OUTDIR, "best_pdnn_grid.pt")
    BEST_SCALER_PATH = os.path.join(OUTDIR, "scaler_best.pkl")
    with open(BEST_SCALER_PATH, "wb") as f:
        pickle.dump(scaler_best, f)
    torch.save(model_best.state_dict(), BEST_SAVE_PATH)
    print(f"[Saved] model → {BEST_SAVE_PATH}\n[Saved] scaler → {BEST_SCALER_PATH}")

    # ===== Test evaluation using the best retrained model =====
    Xte = scaler_best.transform(X_te_raw)
    auc_te = eval_auc(model_best, Xte, y_te, w_te, device_local)
    print(f"[TEST] AUC with best cfg retrained on TR+VAL: {auc_te:.4f}")

    # Separation & ROC plots
    X_te_t = torch.tensor(Xte, dtype=torch.float32, device=device_local)
    test_probs = safe_eval_probs(model_best, X_te_t, device_local)
    separation_and_roc_plots(y_te, w_te, test_probs, df_te, X_te_raw, available_features, OUTDIR)

    # ===== Feature importance (permutation + gradients) on TEST =====
    # Choose features incl. mass/y
    INCLUDE_MY = True
    feat_names_imp = [f for f in available_features if INCLUDE_MY or f not in ("mass","y_value")]
    cols = [available_features.index(f) for f in feat_names_imp]
    X_imp_sel = Xte[:, cols].copy()

    # Group codes
    group_codes = pd.factorize(df_te['mass'].astype(int).astype(str) + "_" + df_te['y_value'].astype(int).astype(str))[0]

    base_auc, imp_mean, imp_std = permutation_importance_auc(
        model_best, X_imp_sel, y_te, w_te, feat_names_imp, device_local, groups=group_codes, n_repeats=5
    )
    print(f"[Permutation] Baseline TEST AUC = {base_auc:.4f}")
    plot_importance_bar(imp_mean, imp_std,
                        title=f"Permutation importance (AUC drop) — TEST",
                        filename=f"feature_importance_permutation_test",
                        top_k=25, cms_color=CMS_BLUE)

    sal = gradient_saliency(model_best, X_imp_sel, feat_names_imp, device_local, scaler=scaler_best, batch=4096)
    mmax = max(sal.values()) if len(sal) else 1.0
    sal_norm = {k: (v/mmax if mmax>0 else 0.0) for k,v in sal.items()}
    plot_importance_bar(sal_norm, {k:0.0 for k in sal_norm},
                        title=f"Input-gradient saliency (normalized) — TEST",
                        filename=f"feature_importance_grad_test",
                        top_k=25, cms_color=CMS_ORANGE)

    # Save importance table
    all_feats = list(sorted(set(feat_names_imp)))
    perm_mean_vec = np.array([imp_mean.get(f, np.nan) for f in all_feats], dtype=float)
    perm_std_vec  = np.array([imp_std.get(f,  np.nan) for f in all_feats], dtype=float)
    grad_norm_vec = np.array([sal_norm.get(f,  np.nan) for f in all_feats], dtype=float)

    imp_df = pd.DataFrame({
        "feature": all_feats,
        "perm_mean_auc_drop": perm_mean_vec,
        "perm_std_auc_drop":  perm_std_vec,
        "grad_saliency_norm": grad_norm_vec,
    }).sort_values(["perm_mean_auc_drop","grad_saliency_norm"], ascending=[False, False], na_position="last")

    csv_path  = os.path.join(OUTDIR, f"feature_importance_test.csv")
    json_path = os.path.join(OUTDIR, f"feature_importance_test.json")
    imp_df.to_csv(csv_path, index=False)
    with open(json_path, "w") as f:
        json.dump({
            "split": "TEST",
            "baseline_auc": float(base_auc),
            "permutation_importance": imp_mean,
            "permutation_importance_std": imp_std,
            "gradient_saliency_normalized": sal_norm,
            "table_order": imp_df["feature"].tolist()
        }, f, indent=2)
    print(f"[Saved] {csv_path}\n[Saved] {json_path}")

    # Final hint: point your downstream sections to the best snapshot if needed
    global SAVE_MODEL_PATH
    SAVE_MODEL_PATH = os.path.join(OUTDIR, "best_pdnn_grid.pt")


if __name__ == "__main__":
    main()
