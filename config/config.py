# from pathlib import Path
# import yaml

# ROOT = Path(__file__).resolve().parents[1]

# class RunConfig:
#     def __init__(self, year: str, era: str):
#         cfg = yaml.safe_load((ROOT / "config" / "datasets.yaml").read_text())
#         ds = cfg["datasets"].get(str(year), {}).get(era)
#         if not ds:
#             raise ValueError(f"No dataset config for year={year}, era={era}")

#         self.year = str(year)
#         self.era = era
#         self.raw_path = (ROOT / ds["raw_path"]).resolve()
#         self.schema = ds.get("schema", "schema_v1")

#         defaults = cfg.get("defaults", {})
#         self.processed_root = (ROOT / defaults.get("processed_root", "data/processed")).resolve()
#         self.outputs_root   = (ROOT / defaults.get("outputs_root",   "outputfiles")).resolve()
#         self.plots_root     = (ROOT / defaults.get("plots_root",     "stack_plots")).resolve()

#     @property
#     def processed_path(self):
#         return self.processed_root / self.year / self.era

#     @property
#     def outputs_path(self):
#         return self.outputs_root / self.year / self.era

#     @property
#     def plots_path(self):
#         return self.plots_root / f"{self.year}_{self.era}"


from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]  # repo root

class RunConfig:
    def __init__(self, year: str, era: str):
        cfg = yaml.safe_load((ROOT / "config" / "datasets.yaml").read_text())

        self.year = str(year)
        self.era  = str(era)

        self.defaults     = cfg["defaults"]
        self.outputs_root = Path(self.defaults["outputs_root"]).resolve()
        self.plots_root   = Path(self.defaults["plots_root"]).resolve()
        self.processed_root = Path(self.defaults["processed_root"]).resolve()

        all_years = cfg["datasets"]
        if self.year not in all_years:
            raise ValueError(f"Unknown year {self.year} in datasets.yaml")

        eras_for_year = all_years[self.year]

        # map era=All to both eras for that year
        if self.era.lower() == "all":
            if self.year == "2022":
                era_list = ["PreEE", "PostEE"]
            elif self.year == "2023":
                era_list = ["preBPix", "postBPix"]
            else:
                raise ValueError(f"No era map for year={self.year}")
        else:
            era_list = [self.era]

        # collect raw paths
        self.raw_paths = []
        for e in era_list:
            if e not in eras_for_year:
                raise ValueError(f"Era '{e}' not found under year {self.year} in datasets.yaml")
            self.raw_paths.append(Path(eras_for_year[e]["raw_path"]))

        # convenience (first era path)
        self.raw_path = self.raw_paths[0]
        # where to put outputs when *not* merging multiple inputs
        self.outputs_path = self.outputs_root / f"{self.year}_{self.era}"
