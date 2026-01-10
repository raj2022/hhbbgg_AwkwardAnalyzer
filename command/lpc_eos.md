# CERN EOS → CMSLPC Workflow Summary
### Stable, Conda-safe, XRootD-safe data staging and analysis

---

## 1. Objective

Access and process **parquet datasets stored on CERN EOS (lxplus)** from **CMSLPC (FNAL)** in a **robust, reproducible, and failure-free way**.

This document summarizes:
- EOS access from LPC
- Certificate & proxy handling
- XRootD + Conda OpenSSL conflicts
- Correct data staging procedure
- Analyzer execution strategy
- Lessons learned & best practices

---

## 2. High-Level Conclusion (TL;DR)

- ❌ Do **NOT** read EOS paths directly from CMSLPC in Python  
- ❌ Do **NOT** use `root://` paths with `pathlib`  
- ❌ Do **NOT** run `xrdcp` inside Conda / Miniforge  
- ✅ Stage EOS data **locally on LPC**  
- ✅ Use `env -i /usr/bin/xrdcp` for clean transfers  
- ✅ Run the analyzer **only on local filesystem paths**

---

## 3. Directory Layout (Recommended)

```
/uscms/home/sraj/sraj/
└── eos_stage/
    ├── 2024/
    ├── preEE/
    ├── postEE/
    ├── preBPix/
    └── postBPix/
```

---

## 4. Certificate & Proxy

```bash
voms-proxy-init -voms cms
voms-proxy-info -timeleft
```

---

## 5. Why Direct EOS Access Failed

- `pathlib.Path` cannot resolve `root://` URLs
- EOS directory walking is slow/unreliable
- Python expects local POSIX paths

---

## 6. XRootD + Conda Conflict

Typical error:
```
libssl.so.3: version `OPENSSL_3.4.0' not found
```

Cause:
- Conda overrides system OpenSSL via `LD_LIBRARY_PATH`

---

## 7. Guaranteed Fix: Clean Environment xrdcp

```bash
env -i \
  PATH=/usr/bin:/bin \
  HOME=$HOME \
  X509_USER_PROXY=$X509_USER_PROXY \
  /usr/bin/xrdcp -r \
  root://eosuser.cern.ch//eos/user/s/sraj/Work_/CUA_20--/Analysis/output_root/v4_production/2024 \
  /uscms/home/sraj/sraj/eos_stage/2024
```

---

## 8. Important xrdcp Behavior

`xrdcp` does **not** create directories automatically.

Always run:
```bash
mkdir -p /uscms/home/sraj/sraj/eos_stage/2024
```

---

## 9. Full Copy Procedure

```bash
mkdir -p /uscms/home/sraj/sraj/eos_stage/{2024,preEE,postEE,preBPix,postBPix}
```

Then copy each dataset using the clean `env -i xrdcp` command.

---

## 10. Verification

```bash
find /uscms/home/sraj/sraj/eos_stage -name "*.parquet" | wc -l
```

---

## 11. Run Analyzer

```bash
python hhbbgg_analyzer_lxplus_par.py \
  --config-year 2024 \
  -i /uscms/home/sraj/sraj/eos_stage/2024 \
  -i /uscms/home/sraj/sraj/eos_stage/preEE \
  -i /uscms/home/sraj/sraj/eos_stage/postEE \
  -i /uscms/home/sraj/sraj/eos_stage/preBPix \
  -i /uscms/home/sraj/sraj/eos_stage/postBPix \
  --tag DD_CombinedAll
```

---

## 12. Final Recommendation

**Stage once, analyze locally, forget EOS exists.**
