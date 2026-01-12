Object-by-object confirmation
1️⃣ Jets (JEC / JER)

✔ Included

You have:

jec_syst_Total_up/down

jer_syst_up/down

They propagate to:

lead_bjet_*

sublead_bjet_*

dibjet_*

bbgg_*

ratios like FirstJet_PtOverM, dibjet_bbgg_mass, etc.

This means:

Jet energy uncertainties fully propagated to the final observable.



Photons (Energy scale & resolution)

✔ Included

You have:

ScaleEE2G_IJazZ_up/down

Smearing2G_IJazZ_up/down

They propagate to:

lead_pho_*

sublead_pho_*

diphoton_*

bbgg_*

photon-related ratios

This is exactly how CMS photon systematics are done.

✔ Correct.



Derived objects (hh, diphoton, dibjet)

✔ Automatically covered

You explicitly produce:

diphoton_mass / pt / eta / phi

dibjet_mass / pt / eta / phi

bbgg_mass / pt / eta / phi

Because these are recomputed per systematic directory, they are:

fully shape-correlated with the object-level shifts.

✔ Correct


Angular & topology variables

✔ Included

You have systematics for:

CosThetaStar_CS

CosThetaStar_gg

CosThetaStar_jj

DeltaR_jg_min

DeltaPhi_j1MET

DeltaPhi_j2MET

These come from shifted kinematics → automatically consistent.

✔ Correct.

b-tagging / PNet observables

⚠️ Partially (and correctly) included

You have shape variations for:

lead_bjet_PNetB

sublead_bjet_PNetB

PNetRegPtRawRes

This is correct for:

kinematic propagation

template stability

📌 Important (CMS convention):

b-tagging SF uncertainties are lnN, not shape

They will enter the datacard as:
```bash
CMS_btag_PNet lnN 1.02
```
Weights / event-level systematics

⚠️ Not included yet — by design

You do not yet have shape systematics for:

pileup

L1 prefiring

trigger

photon ID SF

btag SF

This is intentional and correct because:

These are normalization (lnN) systematics, not shape ones.

They will be added only in the datacard, e.g.:

```bash
lumi_2022        lnN 1.016
CMS_pu          lnN 1.01
CMS_phoID       lnN 1.02
CMS_btag        lnN 1.03
```

