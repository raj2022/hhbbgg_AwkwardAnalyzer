#!/usr/bin/env python3
# =============================================================================
# plot_pdnn_variables.py
#
# X-YH -> bbgg
#
# pDNN INPUT VARIABLE VALIDATION
#
# Signal:
#     X300 / Y100
#     X1000 / Y100
#
# Backgrounds:
#     GGJets
#     DDQCDGJets
#     GGJets_Rescaled
#
# All samples are OVERLAID on the same axes.
#
# Each sample is independently normalized to unit area.
#
# Backgrounds are sampled in a memory-safe way so that very large parquet
# files do not cause the job to be killed by the OS.
#
# =============================================================================


# =============================================================================
# 1. IMPORTS
# =============================================================================

from __future__ import annotations

import json
import os
import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import matplotlib

# Important for lxplus / batch execution
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


warnings.filterwarnings("ignore")


# =============================================================================
# 2. CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class Config:

    # -------------------------------------------------------------------------
    # Reproducibility
    # -------------------------------------------------------------------------

    SEED: int = 42

    # -------------------------------------------------------------------------
    # Feature list
    # -------------------------------------------------------------------------

    FEATURES_JSON: str = "features.json"

    # -------------------------------------------------------------------------
    # Signal
    # -------------------------------------------------------------------------

    SIG_TPL: str = (
        "/eos/cms/store/group/phys_b2g/HHbbgg/bsahu/higgsdna_v7/"
        "2022postEE/merged/NMSSM_X{m}_Y{y}/nominal/"
        "NOTAG_merged.parquet"
    )

    # Requested benchmark points
    LOW_MASS_X: int = 300
    LOW_MASS_Y: int = 100

    HIGH_MASS_X: int = 1000
    HIGH_MASS_Y: int = 100

    # -------------------------------------------------------------------------
    # Full signal grid
    #
    # This is ONLY used to reproduce the background (mass,y) mixture.
    # We do NOT load the full signal grid into memory.
    # -------------------------------------------------------------------------

    MASS_POINTS: Tuple[int, ...] = (
        300, 320, 350, 400,
        450, 500, 550, 600,
        650, 700, 750, 800,
        850, 900, 950, 1000,
    )

    Y_VALUES: Tuple[int, ...] = (
        90, 95, 100, 125,
        150, 170, 200, 250,
        300, 350, 400, 450,
        500, 550, 600, 650,
        700, 800,
    )

    # -------------------------------------------------------------------------
    # Background
    # -------------------------------------------------------------------------

    BACKGROUND_BASE_DIR: str = (
        "/afs/cern.ch/user/s/sraj/Analysis/output_parquet/"
        "Run3_2022/sim/postEE"
    )

    BACKGROUND_FILES: Tuple[Tuple[str, str], ...] = (

        (
            "GGJets",
            "GGJets_MGG-80/NOTAG_merged.parquet",
        ),

        (
            "DDQCDGJets",
            "DDQCCDGJets/DDQCDGJets_Rescaled.parquet",
        ),

        (
            "GGJets_Rescaled",
            "DDQCCDGJets/GGJets_MGG-80_Rescaled.parquet",
        ),

    )

    # -------------------------------------------------------------------------
    # MEMORY CONTROL
    #
    # Maximum events retained from EACH background.
    #
    # 100k is more than sufficient for smooth shape plots.
    # -------------------------------------------------------------------------

    MAX_BACKGROUND_EVENTS: int = 100_000

    # Number of rows read from parquet at a time.
    #
    # This controls memory usage while scanning large files.
    PARQUET_BATCH_SIZE: int = 50_000

    # -------------------------------------------------------------------------
    # Histogram
    # -------------------------------------------------------------------------

    NBINS: int = 50

    LOW_PERCENTILE: float = 0.5
    HIGH_PERCENTILE: float = 99.5

    # -------------------------------------------------------------------------
    # Weight
    # -------------------------------------------------------------------------

    WEIGHT_COLUMN: str = "weight_central"

    USE_WEIGHTS: bool = True

    # -------------------------------------------------------------------------
    # Output
    # -------------------------------------------------------------------------

    OUTPUT_DIR: str = "outputs_pdnn_variables"

    # -------------------------------------------------------------------------
    # Plot
    # -------------------------------------------------------------------------

    FIGURE_WIDTH: float = 8.0
    FIGURE_HEIGHT: float = 6.0

    DPI: int = 300


CFG = Config()


# =============================================================================
# 3. OUTPUT DIRECTORY
# =============================================================================

PLOT_DIR = os.path.join(
    CFG.OUTPUT_DIR,
    "X300Y100_vs_X1000Y100",
)


# =============================================================================
# 4. PLOT COLORS
# =============================================================================

COLORS = {

    "X300/Y100": "#d62728",       # red

    "X1000/Y100": "#1f77b4",      # blue

    "GGJets": "#555555",

    "DDQCDGJets": "#888888",

    "GGJets_Rescaled": "#b0b0b0",

}


LINESTYLES = {

    "X300/Y100": "-",

    "X1000/Y100": "--",

    "GGJets": "-.",

    "DDQCDGJets": ":",

    "GGJets_Rescaled": (0, (6, 2, 1, 2)),

}


LINEWIDTHS = {

    "X300/Y100": 2.5,

    "X1000/Y100": 2.5,

    "GGJets": 1.8,

    "DDQCDGJets": 1.8,

    "GGJets_Rescaled": 1.8,

}


# =============================================================================
# 5. FEATURE LABELS
# =============================================================================

FEATURE_LABELS = {

    "lead_eta":
        r"Leading photon $\eta$",

    "lead_phi":
        r"Leading photon $\phi$",

    "Res_dijet_eta":
        r"Dijet $\eta$",

    "Res_dijet_phi":
        r"Dijet $\phi$",

    "Res_HHbbggCandidate_eta":
        r"$HH$ candidate $\eta$",

    "Res_HHbbggCandidate_phi":
        r"$HH$ candidate $\phi$",

    "Res_HHbbggCandidate_pt":
        r"$p_T^{HH}$ [GeV]",

    "Res_DeltaR_jg_min":
        r"$\min\Delta R(j,\gamma)$",

    "Res_CosThetaStar_gg":
        r"$|\cos\theta^*_{\gamma\gamma}|$",

    "Res_CosThetaStar_jj":
        r"$|\cos\theta^*_{jj}|$",

    "Res_CosThetaStar_CS":
        r"$|\cos\theta^*_{\mathrm{CS}}|$",

    "lead_mvaID_run3":
        r"Leading photon MVA ID",

    "n_leptons":
        r"$N_{\ell}$",

    "n_jets":
        r"$N_{\mathrm{jets}}$",

    "puppiMET_pt":
        r"PUPPI MET $p_T$ [GeV]",

    "puppiMET_phi":
        r"PUPPI MET $\phi$",

    "Res_chi_t0":
        r"$\chi_{t0}$",

    "Res_chi_t1":
        r"$\chi_{t1}$",

    "Res_dijet_pt":
        r"$p_T^{jj}$ [GeV]",

    "Res_pholead_PtOverM":
        r"$p_T^{\gamma_1}/m_{\gamma\gamma}$",

    "Res_phosublead_PtOverM":
        r"$p_T^{\gamma_2}/m_{\gamma\gamma}$",

    "Res_FirstJet_PtOverM":
        r"$p_T^{j_1}/m_{jj}$",

    "Res_SecondJet_PtOverM":
        r"$p_T^{j_2}/m_{jj}$",

    "ptjj_over_mHH":
        r"$p_T^{jj}/m_{HH}$",

    "ptHH_over_mHH":
        r"$p_T^{HH}/m_{HH}$",

    "mass":
        r"$m_X$ [GeV]",

    "y_value":
        r"$m_Y$ [GeV]",

}


# =============================================================================
# 6. FEATURE CATEGORIES
# =============================================================================

ANGLE_FEATURES = {

    "lead_phi",
    "Res_dijet_phi",
    "Res_HHbbggCandidate_phi",
    "puppiMET_phi",

}


INTEGER_FEATURES = {

    "n_leptons",
    "n_jets",

}


PARAMETER_FEATURES = {

    "mass",
    "y_value",

}


# =============================================================================
# 7. MATPLOTLIB STYLE
# =============================================================================

def configure_plot_style():

    plt.rcParams.update({

        "figure.figsize": (
            CFG.FIGURE_WIDTH,
            CFG.FIGURE_HEIGHT,
        ),

        "figure.dpi": 110,

        "axes.grid": True,

        "grid.alpha": 0.25,

        "grid.linestyle": "--",

        "axes.axisbelow": True,

        "axes.titlesize": 14,

        "axes.labelsize": 13,

        "xtick.labelsize": 11,

        "ytick.labelsize": 11,

        "legend.fontsize": 10,

        "legend.frameon": False,

        "lines.linewidth": 2.0,

    })


# =============================================================================
# 8. LOAD FEATURES
# =============================================================================

def load_features() -> List[str]:

    if not os.path.exists(
        CFG.FEATURES_JSON
    ):

        raise FileNotFoundError(
            f"\nCould not find:\n"
            f"    {CFG.FEATURES_JSON}\n"
        )


    with open(
        CFG.FEATURES_JSON,
        "r",
    ) as f:

        data = json.load(f)


    features = data["features"]


    print(
        "\n============================================================"
    )

    print(
        "FEATURES FROM features.json"
    )

    print(
        "============================================================"
    )


    for i, feature in enumerate(
        features,
        start=1,
    ):

        print(
            f"{i:2d}. {feature}"
        )


    print(
        f"\nTotal features: {len(features)}"
    )


    return features


# =============================================================================
# 9. PREPROCESSING
# =============================================================================

def ensure_photon_mva_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()


    if (
        "lead_mvaID_run3" not in df.columns
        and
        "lead_mvaID_nano" in df.columns
    ):

        df["lead_mvaID_run3"] = (
            df["lead_mvaID_nano"]
        )


    return df


# -----------------------------------------------------------------------------

def add_engineered_features(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()


    # -------------------------------------------------------------------------
    # pT(jj) / mHH and pT(HH) / mHH
    # -------------------------------------------------------------------------

    if "Res_HHbbggCandidate_mass" in df.columns:

        m_hh = (
            df["Res_HHbbggCandidate_mass"]
            .replace(0, np.nan)
        )


        if "Res_dijet_pt" in df.columns:

            df["ptjj_over_mHH"] = (
                df["Res_dijet_pt"] /
                m_hh
            )


        if "Res_HHbbggCandidate_pt" in df.columns:

            df["ptHH_over_mHH"] = (
                df["Res_HHbbggCandidate_pt"] /
                m_hh
            )


    # -------------------------------------------------------------------------
    # Same treatment used by pDNN training.
    # -------------------------------------------------------------------------

    for feature in (

        "Res_CosThetaStar_gg",

        "Res_CosThetaStar_jj",

        "Res_CosThetaStar_CS",

    ):

        if feature in df.columns:

            df[feature] = (
                df[feature].abs()
            )


    # -------------------------------------------------------------------------
    # Replace infinities.
    # -------------------------------------------------------------------------

    for feature in (

        "ptjj_over_mHH",

        "ptHH_over_mHH",

    ):

        if feature in df.columns:

            df[feature] = (

                df[feature]

                .replace(
                    [np.inf, -np.inf],
                    np.nan,
                )

            )


    return df


# -----------------------------------------------------------------------------

def prepare_dataframe(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()


    # -------------------------------------------------------------------------
    # Raw diphoton mass.
    #
    # The pDNN uses "mass" for the X parameter, so preserve the physical
    # diphoton mass under "diphoton_mass".
    # -------------------------------------------------------------------------

    if "mass" in df.columns:

        df = df.rename(
            columns={
                "mass": "diphoton_mass",
            }
        )


    df = ensure_photon_mva_columns(
        df
    )


    df = add_engineered_features(
        df
    )


    return df


# =============================================================================
# 10. BUILD REQUIRED PARQUET COLUMN LIST
# =============================================================================

def build_required_columns(
    features: Sequence[str],
) -> List[str]:

    required = set(
        features
    )


    # -------------------------------------------------------------------------
    # Engineered features need these raw columns.
    # -------------------------------------------------------------------------

    required.update({

        "Res_HHbbggCandidate_mass",

        "Res_dijet_pt",

        "Res_HHbbggCandidate_pt",

    })


    # -------------------------------------------------------------------------
    # MVA fallback.
    # -------------------------------------------------------------------------

    required.add(
        "lead_mvaID_nano"
    )


    # -------------------------------------------------------------------------
    # Event weight.
    # -------------------------------------------------------------------------

    required.add(
        CFG.WEIGHT_COLUMN
    )


    return sorted(
        required
    )


# =============================================================================
# 11. GET EXISTING PARQUET COLUMNS
# =============================================================================

def get_available_columns(
    filepath: str,
) -> List[str]:

    parquet_file = pq.ParquetFile(
        filepath
    )

    return list(
        parquet_file.schema.names
    )


# =============================================================================
# 12. READ A SMALL SIGNAL SAMPLE
# =============================================================================

def load_signal_point(
    mass: int,
    y: int,
) -> pd.DataFrame:

    filepath = CFG.SIG_TPL.format(
        m=mass,
        y=y,
    )


    print(
        "\n------------------------------------------------------------"
    )

    print(
        f"Signal: X={mass}, Y={y}"
    )

    print(
        filepath
    )

    print(
        "------------------------------------------------------------"
    )


    if not os.path.exists(
        filepath
    ):

        raise FileNotFoundError(
            f"Signal file does not exist:\n{filepath}"
        )


    df = pd.read_parquet(
        filepath
    )


    df = prepare_dataframe(
        df
    )


    df["mass"] = mass

    df["y_value"] = y

    df["label"] = 1


    print(
        f"Events loaded: {len(df):,}"
    )


    return df


# =============================================================================
# 13. MEMORY-SAFE BACKGROUND READER
# =============================================================================
#
# We scan the large parquet file in batches.
#
# We NEVER load the complete parquet into memory.
#
# Reservoir sampling gives a reproducible approximately-uniform sample of
# MAX_BACKGROUND_EVENTS from the entire file.
# =============================================================================

def read_parquet_sampled(
    filepath: str,
    columns: Sequence[str],
    max_events: int,
    batch_size: int,
    seed: int,
) -> pd.DataFrame:

    parquet_file = pq.ParquetFile(
        filepath
    )


    total_rows = (
        parquet_file.metadata.num_rows
    )


    print(
        f"Total events in file: {total_rows:,}"
    )


    # -------------------------------------------------------------------------
    # If the file is already small, read everything.
    # -------------------------------------------------------------------------

    if total_rows <= max_events:

        print(
            "File is smaller than sampling limit; "
            "reading all events."
        )


        existing_columns = set(
            parquet_file.schema.names
        )


        columns = [
            c
            for c in columns
            if c in existing_columns
        ]


        table = parquet_file.read(
            columns=columns
        )


        return table.to_pandas()


    # -------------------------------------------------------------------------
    # Reservoir sampling.
    # -------------------------------------------------------------------------

    rng = np.random.default_rng(
        seed
    )


    reservoir_data = None

    reservoir_size = 0

    rows_seen = 0


    for batch_number, batch in enumerate(

        parquet_file.iter_batches(

            batch_size=batch_size,

            columns=list(columns),

        )

    ):

        batch_df = batch.to_pandas()

        n_batch = len(
            batch_df
        )


        if n_batch == 0:

            continue


        # ---------------------------------------------------------------------
        # Fill reservoir initially.
        # ---------------------------------------------------------------------

        if reservoir_size < max_events:

            n_needed = (
                max_events -
                reservoir_size
            )

            n_take = min(
                n_needed,
                n_batch,
            )


            if n_take > 0:

                chosen = rng.choice(

                    n_batch,

                    size=n_take,

                    replace=False,

                )


                selected = (
                    batch_df.iloc[chosen]
                    .copy()
                )


                if reservoir_data is None:

                    reservoir_data = selected

                else:

                    reservoir_data = pd.concat(

                        [
                            reservoir_data,
                            selected,
                        ],

                        ignore_index=True,

                    )


                reservoir_size = len(
                    reservoir_data
                )


        rows_seen += n_batch


        # ---------------------------------------------------------------------
        # Reservoir replacement.
        # ---------------------------------------------------------------------

        if reservoir_size >= max_events:

            # Global row positions in this batch.
            global_positions = (
                np.arange(n_batch)
                +
                rows_seen -
                n_batch
            )


            # For each new row, decide whether it enters reservoir.
            for local_position, global_position in enumerate(
                global_positions
            ):

                if global_position < max_events:

                    continue


                replacement = rng.integers(

                    0,

                    global_position + 1,

                )


                if replacement < max_events:

                    reservoir_data.iloc[
                        replacement
                    ] = batch_df.iloc[
                        local_position
                    ].values


        if (
            batch_number + 1
        ) % 10 == 0:

            print(
                f"  scanned {rows_seen:,} / "
                f"{total_rows:,} rows"
            )


    if reservoir_data is None:

        raise RuntimeError(
            f"No events could be sampled from {filepath}"
        )


    reservoir_data = (
        reservoir_data
        .reset_index(drop=True)
    )


    print(
        f"Sampled events retained: "
        f"{len(reservoir_data):,}"
    )


    return reservoir_data


# =============================================================================
# 14. LOAD BACKGROUNDS
# =============================================================================

def load_backgrounds(
    features: Sequence[str],
) -> Dict[str, pd.DataFrame]:

    print(
        "\n============================================================"
    )

    print(
        "LOADING BACKGROUNDS"
    )

    print(
        "============================================================"
    )


    backgrounds = {}


    required_columns = build_required_columns(
        features
    )


    print(
        f"\nRequested parquet columns: "
        f"{len(required_columns)}"
    )


    for background_index, (
        name,
        relative_path,
    ) in enumerate(
        CFG.BACKGROUND_FILES
    ):

        filepath = os.path.join(

            CFG.BACKGROUND_BASE_DIR,

            relative_path,

        )


        print(
            "\n------------------------------------------------------------"
        )

        print(
            f"Background: {name}"
        )

        print(
            filepath
        )

        print(
            "------------------------------------------------------------"
        )


        if not os.path.exists(
            filepath
        ):

            print(
                "[WARNING] File does not exist. Skipping."
            )

            continue


        # ---------------------------------------------------------------------
        # Inspect schema without reading events.
        # ---------------------------------------------------------------------

        available_columns = set(
            get_available_columns(
                filepath
            )
        )


        columns_to_read = [

            c
            for c in required_columns
            if c in available_columns

        ]


        missing = sorted(

            set(required_columns)
            -
            available_columns

        )


        if missing:

            print(
                "[INFO] Missing columns:"
            )

            for column in missing:

                print(
                    f"    {column}"
                )


        print(
            f"Reading {len(columns_to_read)} "
            f"columns instead of the complete parquet."
        )


        # ---------------------------------------------------------------------
        # Memory-safe sample.
        # ---------------------------------------------------------------------

        df = read_parquet_sampled(

            filepath=filepath,

            columns=columns_to_read,

            max_events=CFG.MAX_BACKGROUND_EVENTS,

            batch_size=CFG.PARQUET_BATCH_SIZE,

            seed=CFG.SEED + background_index,

        )


        # ---------------------------------------------------------------------
        # Physics preprocessing.
        # ---------------------------------------------------------------------

        df = prepare_dataframe(
            df
        )


        df["label"] = 0


        backgrounds[name] = df


        memory_mb = (

            df.memory_usage(
                deep=True
            ).sum()
            /
            1024**2

        )


        print(
            f"Final sample: {len(df):,} events"
        )

        print(
            f"DataFrame memory: {memory_mb:.1f} MB"
        )


    if not backgrounds:

        raise RuntimeError(
            "No background samples were loaded."
        )


    return backgrounds


# =============================================================================
# 15. GET FULL SIGNAL-GRID MIXTURE
# =============================================================================
#
# The pDNN training assigns background mass/y values according to the signal
# event mixture:
#
#     signal_df[['mass','y_value']].value_counts(normalize=True)
#
# We reproduce the same idea without loading the entire signal grid.
#
# Parquet metadata gives us the number of rows in each signal file.
# =============================================================================

def build_signal_mass_y_mixture() -> pd.DataFrame:

    print(
        "\n============================================================"
    )

    print(
        "BUILDING FULL SIGNAL (MASS,Y) MIXTURE"
    )

    print(
        "============================================================"
    )


    rows = []


    n_found = 0

    n_missing = 0


    for mass in CFG.MASS_POINTS:

        for y in CFG.Y_VALUES:

            filepath = CFG.SIG_TPL.format(

                m=mass,

                y=y,

            )


            if not os.path.exists(
                filepath
            ):

                n_missing += 1

                continue


            try:

                parquet_file = pq.ParquetFile(
                    filepath
                )


                n_events = (
                    parquet_file.metadata.num_rows
                )


                if n_events <= 0:

                    continue


                rows.append({

                    "mass": mass,

                    "y_value": y,

                    "count": n_events,

                })


                n_found += 1


            except Exception as exc:

                print(
                    f"[WARNING] Could not inspect "
                    f"X={mass}, Y={y}: {exc}"
                )


    if not rows:

        raise RuntimeError(
            "Could not construct the signal mass/y mixture."
        )


    mixture = pd.DataFrame(
        rows
    )


    mixture["probability"] = (

        mixture["count"]
        /
        mixture["count"].sum()

    )


    print(
        f"\nFound signal points: {n_found}"
    )

    print(
        f"Missing signal points: {n_missing}"
    )

    print(
        f"Total signal events represented: "
        f"{mixture['count'].sum():,}"
    )


    return mixture


# =============================================================================
# 16. ASSIGN BACKGROUND MASS/Y
# =============================================================================
#
# This follows the training implementation:
#
#     sample mass/y according to the full signal mixture.
#
# This is only relevant for plotting "mass" and "y_value".
# =============================================================================

def assign_background_parameters(
    background: pd.DataFrame,
    mixture: pd.DataFrame,
    seed: int,
) -> pd.DataFrame:

    background = background.copy()


    rng = np.random.default_rng(
        seed
    )


    probabilities = mixture[
        "probability"
    ].to_numpy()


    indices = rng.choice(

        len(mixture),

        size=len(background),

        replace=True,

        p=probabilities,

    )


    sampled = mixture.iloc[
        indices
    ]


    background["mass"] = (
        sampled["mass"]
        .to_numpy()
    )


    background["y_value"] = (
        sampled["y_value"]
        .to_numpy()
    )


    # -------------------------------------------------------------------------
    # Ensure every signal point can appear at least once where possible.
    # This mirrors the intent of the training implementation.
    # -------------------------------------------------------------------------

    required_points = set(

        zip(

            mixture["mass"].astype(int),

            mixture["y_value"].astype(int),

        )

    )


    current_points = set(

        zip(

            background["mass"].astype(int),

            background["y_value"].astype(int),

        )

    )


    missing_points = list(

        required_points -
        current_points

    )


    if missing_points:

        n_replace = min(

            len(missing_points),

            len(background),

        )


        for i in range(
            n_replace
        ):

            mass, y = missing_points[i]

            background.iloc[
                i,
                background.columns.get_loc(
                    "mass"
                ),
            ] = mass

            background.iloc[
                i,
                background.columns.get_loc(
                    "y_value"
                ),
            ] = y


    return background


# =============================================================================
# 17. CLEAN VALUES
# =============================================================================

def extract_values(
    df: pd.DataFrame,
    feature: str,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:

    if feature not in df.columns:

        return (
            np.array([], dtype=float),
            None,
        )


    values = pd.to_numeric(

        df[feature],

        errors="coerce",

    ).to_numpy(
        dtype=float
    )


    valid = np.isfinite(
        values
    )


    values = values[
        valid
    ]


    # -------------------------------------------------------------------------
    # Event weights.
    # -------------------------------------------------------------------------

    weights = None


    if (
        CFG.USE_WEIGHTS
        and
        CFG.WEIGHT_COLUMN in df.columns
    ):

        weights = pd.to_numeric(

            df.loc[
                valid,
                CFG.WEIGHT_COLUMN
            ],

            errors="coerce",

        ).to_numpy(
            dtype=float
        )


        weights = np.where(

            np.isfinite(weights),

            weights,

            0.0,

        )


        # ---------------------------------------------------------------------
        # We expect normal positive event weights for these distributions.
        #
        # If negative weights exist, don't silently distort them.
        # Instead, use absolute weights for the shape diagnostic and report it.
        # ---------------------------------------------------------------------

        if np.any(
            weights < 0
        ):

            print(
                f"[WARNING] Negative weights found for "
                f"{feature}. Using |weight| for this shape plot."
            )

            weights = np.abs(
                weights
            )


        # ---------------------------------------------------------------------
        # If all weights are zero, fall back to unweighted.
        # ---------------------------------------------------------------------

        if not np.any(
            weights > 0
        ):

            weights = None


    return (
        values,
        weights,
    )


# =============================================================================
# 18. DETERMINE COMMON RANGE
# =============================================================================

def determine_range(
    sample_values: Dict[
        str,
        Tuple[np.ndarray, Optional[np.ndarray]]
    ],
    feature: str,
) -> Optional[Tuple[float, float]]:

    arrays = [

        values

        for values, _ in sample_values.values()

        if len(values) > 0

    ]


    if not arrays:

        return None


    combined = np.concatenate(
        arrays
    )


    # -------------------------------------------------------------------------
    # Phi variables.
    # -------------------------------------------------------------------------

    if feature in ANGLE_FEATURES:

        return (
            -np.pi,
            np.pi,
        )


    # -------------------------------------------------------------------------
    # X parameter.
    # -------------------------------------------------------------------------

    if feature == "mass":

        return (
            250.0,
            1050.0,
        )


    # -------------------------------------------------------------------------
    # Y parameter.
    # -------------------------------------------------------------------------

    if feature == "y_value":

        return (
            80.0,
            810.0,
        )


    # -------------------------------------------------------------------------
    # Multiplicity.
    # -------------------------------------------------------------------------

    if feature in INTEGER_FEATURES:

        low = np.floor(
            np.nanmin(combined)
        )

        high = np.ceil(
            np.nanmax(combined)
        )


        return (
            low - 0.5,
            high + 0.5,
        )


    # -------------------------------------------------------------------------
    # Continuous variable.
    # -------------------------------------------------------------------------

    low = np.percentile(

        combined,

        CFG.LOW_PERCENTILE,

    )


    high = np.percentile(

        combined,

        CFG.HIGH_PERCENTILE,

    )


    if (
        not np.isfinite(low)
        or
        not np.isfinite(high)
    ):

        return None


    if high <= low:

        return None


    padding = 0.05 * (
        high - low
    )


    return (
        low - padding,
        high + padding,
    )


# =============================================================================
# 19. PLOT ONE FEATURE
# =============================================================================

def make_feature_plot(
    feature: str,
    samples_dataframe: Dict[str, pd.DataFrame],
) -> Optional[plt.Figure]:

    # -------------------------------------------------------------------------
    # Extract all samples.
    # -------------------------------------------------------------------------

    sample_values = {}


    for label, df in samples_dataframe.items():

        values, weights = extract_values(

            df,

            feature,

        )


        if len(values) == 0:

            print(
                f"[WARNING] No valid values for "
                f"{feature} in {label}"
            )

            continue


        sample_values[label] = (
            values,
            weights,
        )


    if not sample_values:

        return None


    # -------------------------------------------------------------------------
    # Common x range.
    # -------------------------------------------------------------------------

    plot_range = determine_range(

        sample_values,

        feature,

    )


    if plot_range is None:

        return None


    bins = np.linspace(

        plot_range[0],

        plot_range[1],

        CFG.NBINS + 1,

    )


    # -------------------------------------------------------------------------
    # Figure.
    # -------------------------------------------------------------------------

    fig, ax = plt.subplots(

        figsize=(

            CFG.FIGURE_WIDTH,

            CFG.FIGURE_HEIGHT,

        )

    )


    # -------------------------------------------------------------------------
    # Plot order.
    #
    # Signals first, backgrounds afterward.
    # -------------------------------------------------------------------------

    plot_order = (

        "X300/Y100",

        "X1000/Y100",

        "GGJets",

        "DDQCDGJets",

        "GGJets_Rescaled",

    )


    for label in plot_order:

        if label not in sample_values:

            continue


        values, weights = sample_values[
            label
        ]


        ax.hist(

            values,

            bins=bins,

            weights=weights,

            density=True,

            histtype="step",

            color=COLORS[label],

            linestyle=LINESTYLES[label],

            linewidth=LINEWIDTHS[label],

            label=label,

        )


    # -------------------------------------------------------------------------
    # Labels.
    # -------------------------------------------------------------------------

    ax.set_xlabel(

        FEATURE_LABELS.get(

            feature,

            feature,

        )

    )


    ax.set_ylabel(
        "Normalized Events"
    )


    # -------------------------------------------------------------------------
    # No generic title.
    #
    # The feature name is already given by the x-axis and the legend.
    # This makes the plot closer to your reference image.
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # CMS-style labels.
    # -------------------------------------------------------------------------

    ax.text(

        0.03,

        0.96,

        "CMS",

        transform=ax.transAxes,

        fontsize=13,

        fontweight="bold",

        va="top",

    )


    ax.text(

        0.095,

        0.96,

        "Preliminary",

        transform=ax.transAxes,

        fontsize=11,

        va="top",

    )


    ax.text(

        0.03,

        0.90,

        r"$HH\rightarrow b\bar{b}\gamma\gamma$",

        transform=ax.transAxes,

        fontsize=11,

        va="top",

    )


    # -------------------------------------------------------------------------
    # Legend.
    # -------------------------------------------------------------------------

    ax.legend(

        loc="best",

        handlelength=3.0,

    )


    # -------------------------------------------------------------------------
    # Grid.
    # -------------------------------------------------------------------------

    ax.grid(

        True,

        which="major",

        alpha=0.20,

        linestyle="--",

    )


    fig.tight_layout()


    return fig


# =============================================================================
# 20. SAVE INDIVIDUAL PLOT
# =============================================================================

def save_feature_plot(
    fig: plt.Figure,
    feature: str,
) -> None:

    os.makedirs(

        PLOT_DIR,

        exist_ok=True,

    )


    png_path = os.path.join(

        PLOT_DIR,

        f"{feature}.png",

    )


    pdf_path = os.path.join(

        PLOT_DIR,

        f"{feature}.pdf",

    )


    fig.savefig(

        png_path,

        dpi=CFG.DPI,

        bbox_inches="tight",

    )


    fig.savefig(

        pdf_path,

        bbox_inches="tight",

    )


    print(
        f"[Saved] {png_path}"
    )


# =============================================================================
# 21. CREATE MULTIPAGE PDF
# =============================================================================

def make_multipage_pdf(
    features: Sequence[str],
    samples_dataframe: Dict[str, pd.DataFrame],
) -> None:

    os.makedirs(

        CFG.OUTPUT_DIR,

        exist_ok=True,

    )


    output_path = os.path.join(

        CFG.OUTPUT_DIR,

        "pdnn_input_variables_X300Y100_vs_X1000Y100.pdf",

    )


    print(
        "\nCreating combined PDF..."
    )


    with PdfPages(
        output_path
    ) as pdf:

        for feature in features:

            fig = make_feature_plot(

                feature,

                samples_dataframe,

            )


            if fig is None:

                continue


            pdf.savefig(

                fig,

                bbox_inches="tight",

            )


            plt.close(
                fig
            )


    print(
        f"[Saved] {output_path}"
    )


# =============================================================================
# 22. WRITE SUMMARY
# =============================================================================

def write_summary(
    features: Sequence[str],
    samples_dataframe: Dict[str, pd.DataFrame],
) -> None:

    os.makedirs(

        CFG.OUTPUT_DIR,

        exist_ok=True,

    )


    output_path = os.path.join(

        CFG.OUTPUT_DIR,

        "plot_summary.txt",

    )


    with open(

        output_path,

        "w",

    ) as f:

        f.write(
            "pDNN input-variable plotting summary\n"
        )

        f.write(
            "====================================\n\n"
        )


        f.write(
            "Signal benchmarks:\n"
        )

        f.write(
            f"  X={CFG.LOW_MASS_X}, "
            f"Y={CFG.LOW_MASS_Y}\n"
        )

        f.write(
            f"  X={CFG.HIGH_MASS_X}, "
            f"Y={CFG.HIGH_MASS_Y}\n\n"
        )


        f.write(
            "Background samples:\n"
        )


        for label in (

            "GGJets",

            "DDQCDGJets",

            "GGJets_Rescaled",

        ):

            if label in samples_dataframe:

                f.write(

                    f"  {label}: "
                    f"{len(samples_dataframe[label]):,} "
                    f"events\n"

                )


        f.write(
            "\n"
        )


        f.write(
            f"Number of features: "
            f"{len(features)}\n"
        )


        f.write(
            f"Maximum background events/sample: "
            f"{CFG.MAX_BACKGROUND_EVENTS:,}\n"
        )


        f.write(
            f"Parquet batch size: "
            f"{CFG.PARQUET_BATCH_SIZE:,}\n"
        )


        f.write(
            f"Weight column: "
            f"{CFG.WEIGHT_COLUMN}\n"
        )


        f.write(
            f"Use event weights: "
            f"{CFG.USE_WEIGHTS}\n"
        )


        f.write(
            "\n"
            "Each sample is independently normalized to unit area.\n"
        )


        f.write(
            "Background samples are NOT combined.\n"
        )


        f.write(
            "Background mass/y values are assigned from the full "
            "signal-grid event mixture.\n"
        )


    print(
        f"[Saved] {output_path}"
    )


# =============================================================================
# 23. MAIN
# =============================================================================

def main():

    np.random.seed(
        CFG.SEED
    )


    configure_plot_style()


    print(
        "\n"
        "====================================================================\n"
        "                  pDNN INPUT VARIABLE PLOTS\n"
        "====================================================================\n"
        "\n"
        "Signal benchmarks:\n"
        f"    X={CFG.LOW_MASS_X}, Y={CFG.LOW_MASS_Y}\n"
        f"    X={CFG.HIGH_MASS_X}, Y={CFG.HIGH_MASS_Y}\n"
        "\n"
        "Backgrounds:\n"
        "    GGJets\n"
        "    DDQCDGJets\n"
        "    GGJets_Rescaled\n"
        "\n"
        "All distributions are overlaid on the SAME axes.\n"
        "Each sample is independently normalized to unit area.\n"
        "\n"
        f"Maximum background events/sample: "
        f"{CFG.MAX_BACKGROUND_EVENTS:,}\n"
        "\n"
        "====================================================================\n"
    )


    # -------------------------------------------------------------------------
    # Output directories.
    # -------------------------------------------------------------------------

    os.makedirs(

        CFG.OUTPUT_DIR,

        exist_ok=True,

    )


    os.makedirs(

        PLOT_DIR,

        exist_ok=True,

    )


    # -------------------------------------------------------------------------
    # Load features.json.
    # -------------------------------------------------------------------------

    features = load_features()


    # -------------------------------------------------------------------------
    # Load the two benchmark signals.
    #
    # These are small, so we keep all events.
    # -------------------------------------------------------------------------

    signal_low = load_signal_point(

        CFG.LOW_MASS_X,

        CFG.LOW_MASS_Y,

    )


    signal_high = load_signal_point(

        CFG.HIGH_MASS_X,

        CFG.HIGH_MASS_Y,

    )


    # -------------------------------------------------------------------------
    # Build full signal-grid mixture.
    #
    # Only parquet metadata is read here.
    # No full signal sample is loaded.
    # -------------------------------------------------------------------------

    signal_mixture = (
        build_signal_mass_y_mixture()
    )


    # -------------------------------------------------------------------------
    # Load large backgrounds safely.
    # -------------------------------------------------------------------------

    backgrounds = load_backgrounds(

        features

    )


    # -------------------------------------------------------------------------
    # Assign parameterization variables to each background.
    #
    # This reproduces the pDNN training convention.
    # -------------------------------------------------------------------------

    for index, (
        name,
        dataframe,
    ) in enumerate(
        list(backgrounds.items())
    ):

        backgrounds[name] = (
            assign_background_parameters(

                dataframe,

                signal_mixture,

                seed=CFG.SEED + index,

            )
        )


    # -------------------------------------------------------------------------
    # Combine samples into a dictionary.
    #
    # IMPORTANT:
    # This is only a dictionary of separate DataFrames.
    #
    # We DO NOT concatenate the backgrounds.
    # -------------------------------------------------------------------------

    samples_dataframe = {

        "X300/Y100":
            signal_low,

        "X1000/Y100":
            signal_high,

    }


    samples_dataframe.update(
        backgrounds
    )


    # -------------------------------------------------------------------------
    # Summary.
    # -------------------------------------------------------------------------

    print(
        "\n============================================================"
    )

    print(
        "SAMPLE SUMMARY"
    )

    print(
        "============================================================"
    )


    for label, dataframe in (
        samples_dataframe.items()
    ):

        print(

            f"{label:20s}: "
            f"{len(dataframe):,} events"

        )


    # -------------------------------------------------------------------------
    # Plot all features.
    # -------------------------------------------------------------------------

    print(
        "\n============================================================"
    )

    print(
        "CREATING OVERLAID FEATURE PLOTS"
    )

    print(
        "============================================================"
    )


    n_success = 0


    for feature in features:

        print(
            f"\nPlotting: {feature}"
        )


        fig = make_feature_plot(

            feature,

            samples_dataframe,

        )


        if fig is None:

            print(
                f"[WARNING] Could not produce "
                f"a plot for {feature}"
            )

            continue


        save_feature_plot(

            fig,

            feature,

        )


        plt.close(
            fig
        )


        n_success += 1


    # -------------------------------------------------------------------------
    # Multipage PDF.
    # -------------------------------------------------------------------------

    make_multipage_pdf(

        features,

        samples_dataframe,

    )


    # -------------------------------------------------------------------------
    # Summary.
    # -------------------------------------------------------------------------

    write_summary(

        features,

        samples_dataframe,

    )


    # -------------------------------------------------------------------------
    # Final.
    # -------------------------------------------------------------------------

    print(
        "\n===================================================================="
    )

    print(
        "DONE"
    )

    print(
        "===================================================================="
    )


    print(
        f"\nSuccessfully plotted: "
        f"{n_success}/{len(features)} features"
    )


    print(
        "\nIndividual plots:"
    )

    print(
        f"    {PLOT_DIR}/"
    )


    print(
        "\nCombined PDF:"
    )

    print(
        f"    {CFG.OUTPUT_DIR}/"
        "pdnn_input_variables_X300Y100_vs_X1000Y100.pdf"
    )


    print()


# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":

    main()