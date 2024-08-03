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

### File Operations
\```bash
# List directory contents
ls -l

# Change directory
cd /path/to/directory

# Copy files
cp source_file destination_file

# Move or rename files
mv old_name new_name

# Remove files or directories
rm -rf file_or_directory
\```

### File Permissions
\```bash
# Change file permissions
chmod 755 file

# Change file owner
chown user:group file
\```

### Viewing File Contents
\```bash
# Display file contents
cat file

# Display file contents with pagination
less file

# Display the first 10 lines of a file
head file

# Display the last 10 lines of a file
tail file

# Follow a file (live updates)
tail -f file
\```

### System Information
\```bash
# Display current date and time
date

# Display system uptime
uptime

# Display user information
whoami

# Display disk usage
df -h

# Display memory usage
free -m
\```

### Process Management
\```bash
# Display active processes
ps aux

# Display processes in real-time
top

# Kill a process by PID
kill PID

# Kill all processes matching a name
pkill process_name
\```

### Network Commands
\```bash
# Display network configuration
ifconfig

# Display active network connections
netstat -tuln

# Test network connectivity
ping hostname_or_ip

# Download files from the internet
wget url

# Secure copy files over SSH
scp user@host:/path/to/remote/file /path/to/local/destination
\```

### Package Management (Debian/Ubuntu)
\```bash
# Update package lists
sudo apt update

# Upgrade all installed packages
sudo apt upgrade

# Install a package
sudo apt install package_name

# Remove a package
sudo apt remove package_name

# Search for a package
apt search package_name
\```

### Text Editing with `vim`
\```bash
# Open a file with vim
vim file

# Enter insert mode
i

# Save and exit
:wq

# Quit without saving
:q!
\```

### Miscellaneous
\```bash
# Create a symbolic link
ln -s target link_name

# Find files in a directory hierarchy
find /path/to/search -name filename

# Display the manual for a command
man command
\```

