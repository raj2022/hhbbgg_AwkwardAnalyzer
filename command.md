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

