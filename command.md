# List of commands which we are using frequently

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

\```bash
ls -l

cd /path/to/directory

cp source_file destination_file

mv old_name new_name

rm -rf file_or_directory
\```

\```bash
chmod 755 file

chown user:group file
\```

\```bash
cat file

less file

head file

tail file

tail -f file
\```

\```bash
date

uptime

whoami

df -h

free -m
\```

\```bash
ps aux

top

kill PID

pkill process_name
\```

\```bash
ifconfig

netstat -tuln

ping hostname_or_ip

wget url

scp user@host:/path/to/remote/file /path/to/local/destination
\```

\```bash
sudo apt update

sudo apt upgrade

sudo apt install package_name

sudo apt remove package_name

apt search package_name
\```

vim file

i

:wq

:q!
\```

\```bash
ln -s target link_name

find /path/to/search -name filename

man command
\```

