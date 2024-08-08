# List of commands which we are using frequently

## LPC commands
kerbrose ticket
```bash
kinit username@FNAL.GOV
username@cmslpc-el9.fnal.gov
```
Eos area 
```bash
eos root://cmseos.fnal.gov
```

### Setup eos area on LPC:
EOS area is not provided by default. A detailed instructions can be found [here](https://uscms.org/uscms_at_work/computing/LPC/usingEOSAtLPC.shtml#createEOSArea).

**How to get an EOS area enabled or linked to `CERNusername`**
Note: this linking is also used for submitting cmslpc condor jobs
1. You can get your EOS area linked to your CMS grid certificate by filling a simple form called "CMS Storage Space Request" in the LPC Service Portal form: "CMS Storage Space Request" (Request for creation of EOS area or for increases to EOS space)
	* Use your Fermilab Services credentials to login
	* Select "Enable" and fill out the form
	* Your DN is the result of voms-proxy-info --identity after authenticating your grid certificate with the cms voms on a linux system
	* Put in your CERNusername (the username that you use to login to lxplus.cern.ch)
	
**Note:** Your ServiceNow request will be completed automatically within a minute. However, the information is propagated to all nodes with a system that only runs during FNAL business hours. This may take 1-3 hours during FNAL business day.

**Note:** If you change your CERN fullname, when you renew your CERN grid certificate it will have a different identity, for instance if you went from Firstname MiddleName Lastname to Firstname Lastname in the CERN database. Then your CERN grid certificate will look different, and thus the new certificate will need to be linked to your EOS area.
To resolve this, open a new "CMS Storage Space Request" (Enable), using your services account to login, as described above.


### Commands to Setup:
* For lxplus:

    ```bash
    source lxplus.cern.ch
    cd ~/Analysis/Analysis_HH-bbgg
    conda activate higgs-dna
    #Go to HiggsDNA
    pip install -e .
    python scripts/pull_all.py --all
   ``` 
 * lpc:   
    ```bash
    login on fermilab
    cd ~/Analysis/Analysis_HH-bbgg
    conda activate higgs-dna
    #Go to HiggsDNA
    pip install -e .
    python scripts/pull_all.py --all
   ``` 


### Job submission

1. **HTCondor**
   If your cluster uses HTCondor:
   * Check the status of all your jobs:
     ```bash
     condor_q
     ```
   * Check the status of specific jobs by ID:
     ```bash
     condor_q <job_id>
     ```

2. **Slurm**
   If your cluster uses Slurm:
   * Check the status of all your jobs:
     ```bash
     squeue
     ```
   * Check the status of a specific job by ID:
     ```bash
     squeue -j <job_id>
     ```

3. **Grid Engine**
   If your cluster uses Grid Engine:
   * Check the status of all your jobs:
     ```bash
     qstat
     ```
   * Check the status of a specific job by ID:
     ```bash
     qstat -j <job_id>
     ```






# Commands for VOMS Setup
## Prerequisites

- Ensure you have the OpenSSL tool installed.
- Obtain a valid `.p12` certificate file from your certificate authority.

## Steps for VOMS Setup

### Generate User Certificate and Key

If you have a `.p12` file, extract the user certificate and key using OpenSSL:

```bash
openssl pkcs12 -in myCertificate_lpc.p12 -out usercert.pem -clcerts -nokeys
openssl pkcs12 -in myCertificate_lpc.p12 -out userkey.pem -nocerts -nodes
```
Set premission for the key file:
```bash
chmod 400 userkey.pem
```
Set Environment variables:
```bash
export X509_USER_CERT=$HOME/.globus/usercert.pem
export X509_USER_KEY=$HOME/.globus/userkey.pem
```
Initialize a VOMS proxy certificate with the following command:
```bash
voms-proxy-init --rfc --voms cms -valid 192:00
```
To view information about your VOMS proxy certificate:
```bash
voms-proxy-info --all
```
If you need to remove an old or expired VOMS proxy:
```bash
voms-proxy-destroy
```
To regenerate or update a VOMS proxy certificate:
```bash
voms-proxy-regen --voms cms
voms-proxy-update --voms cms
```





# Linux Commands

**Basic File Operations:**
```bash
ls -l
cd /path/to/directory
cp source_file destination_file
mv old_name new_name
rm -rf file_or_directory

```

**File Permissions and Ownership:**
```
chmod 755 file
chown user:group file
```
**Viewing File Contents:**
```bash
cat file

less file

head file

tail file

tail -f file
```

\```bash
date

uptime

whoami

df -h

free -m
\```

**Process Management:**
```bash
ps aux

top

kill PID

pkill process_name
```
**Network Commands:**
```bash
ifconfig

netstat -tuln

ping hostname_or_ip

wget url

scp user@host:/path/to/remote/file /path/to/local/destination
```
**Package Management (Debian/Ubuntu):**
```bash
sudo apt update

sudo apt upgrade

sudo apt install package_name

sudo apt remove package_name

apt search package_name
```

**Vim Commands:**
```bash
vim file

i

:wq

:q!
```
**Symbolic Links and Search:**

```bash
ln -s target link_name

find /path/to/search -name filename

man command
```
## Higgs-dna setup
1. lxplus/lpc: mentioned in the [tutorial](https://indico.cern.ch/event/1360961/contributions/5777678/attachments/2788218/4861762/HiggsDNA_tutorial.pdf) and [here](https://higgs-dna.readthedocs.io/en/latest/index.html) as well.

```bash
conda activate higgs-dna
```
 
## Analysis setup
1. On LPC
```bash

source ~/.bashrc

# Env setup
conda activate hhbbgg-awk


##Navigate to the specified directory
cd /uscms/home/sraj/nobackup/Hh-bbgg/Analysis_HH-bbgg/hhbbgg_AwkwardAnalyzer
#

```
2. lxplus
- navigate manually
- 
```bash
# Env setup
conda activate hhbbgg-awk
```
command to merge all produced `.parquet` files:
```bash
python3 prepare_output_file.py --input /afs/cern.ch/user/s/sraj/Analysis/output_parquet/ --merge --root --ws --syst --cats --args "--do_syst"
```
To convert merged `.parquet` to `.root` using

in general( [HiggsDNA folder](https://higgs-dna.readthedocs.io/en/latest/postprocessing.html#root-step))
```bash
python scripts/postprocessing/convert_parquet_to_root.py --input_parquet_files --output_parquet_file_output/file_name.root mc
```
eg. 
```bash
python scripts/postprocessing/convert_parquet_to_root.py ../../../output_parquet/merged/NMSSM_X300_Y100/nominal/NOTAG_NOTAG_merged.parquet ../../../output_root/NMSSM_X300_Y100/NMSSM_X300_Y100.root mc
```

# Setup ROOT
Instruction to setup root(Ubuntu)
1. Update and upgrade your system
```bash
sudo apt update
sudo apt upgrade
```

2. Install dependencies
```bash
sudo apt install dpkg-dev cmake g++ gcc binutils libx11-dev libxpm-dev libxft-dev libxext-dev python3 libssl-dev
```
3. Install optional dependencies
```bash
sudo apt install libpng-dev libjpeg-dev libgif-dev libtiff-dev libxml2-dev libssl-dev libgsl-dev
```
4. Download ROOT. ROOT can be downloaded from ROOT website with latst realease, 
https://root.cern.ch/doc/master/group__Tutorials.html, but it is preferred to use the git instructions. 
```bash
git clone https://github.com/root-project/root.git
```
5. Build and install ROOT
```bash
cd root
mkdir build
cd build
```
configure the build with Cmake:
```bash
cmake ..
```
To build ROOT (this may take some time):
```bash
cmake --build . -- -j$(nproc)
```
Once the build process is complete, you can install ROOT by running:
```bash
sudo cmake --build . --target install
```
 6. Set Up Environment Variables
Add ROOT to your environment variables by adding the following lines to your .bashrc or .bash_profile:
```bash
source /path/to/your/root/build/bin/thisroot.sh
```
Make sure to replace /path/to/your/root/build/ with the actual path to your ROOT installation.

Then apply changes,
```bash
source ~/.bashrc
```
7. Verify the installation
```bash
root
```

