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

### Setup a CMSSW release area
```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
export CMSSW_GIT_REFERENCE=/cvmfs/cms.cern.ch/cmssw.git.daily

cd /eos/user/<first-letter-of-username>/<username>
mkdir YOURWORKINGAREA
cd YOURWORKINGAREA
### If you are using Bash shell
export SCRAM_ARCH=el9_amd64_gcc11
### Alternatively, If you are using the default tcsh shell (or csh shell)
setenv SCRAM_ARCH el9_amd64_gcc11
### Then, in both cases:
cmsrel CMSSW_13_0_17
cd CMSSW_13_0_17/src
cmsenv
```
other methods can be 
```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsrel CMSSW_X_Y_Z  # Replace X_Y_Z with the desired release version
cd CMSSW_X_Y_Z/src
cmsenv
```
further, compile and test using
```bash
scram b -j 8  # Adjust the number 8 depending on the number of cores available
```
To be able to check out specific CMSSW packages from GitHub, you will need to configure your local account. You only have to do this command once for any given cluster you are working on, such as lxplus:

```bash
git config --global user.name "[Name]"
git config --global user.email [Email]
git config --global user.github [Account]
```

To see your current git configuration you can use the following command:

```shell
git config --global -l
```
Now you can initialize the CMSSW area as a local git repository:

```bash
git cms-init
```
This last command will take some time to execute and will produce some long output, be patient.

When you get the prompt again, run the following command:

```shell
echo $CMSSW_BASE
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

# setup jupyter on LPC
```bash
ssh -L localhost:8899:localhost:8899 sraj@cmslpc-el9.fnal.gov

source ~/.bashrc

# Env setup
conda activate hhbbgg-awk


##Navigate to the specified directory
jupyter notebook --no-browser --port=8899 --ip 127.0.0.1


# Notify the user that the script has finished
echo "Initialized mamba, activated hhbbgg-awk environment, and changed directory to hhbbgg_AwkwardAnalyzer."
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
## LCG environment and Containers
Container instructions: https://cms-ml.github.io/documentation/software_envs/containers.html
LCG environemnt: https://cms-ml.github.io/documentation/software_envs/lcg_environments.html

## Setup ROOT
### Instruction to setup root(Ubuntu)
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
### Install Root on `mac`
```bash
brew update
brew install cmake
```

Install root 
```bash
brew install root
```

Check the root version using
```bash
root -v
```

## Git Commands
To clone/pull all branch at once from the github, as for example we are taking our hhbbgg_analyzer file, `git@github.com:raj2022/hhbbgg_AwkwardAnalyzer.git`
- `git checkout --track "branch name"`
Examples, 
```bash
git checkout --track origin/NMSSM
```
 and 
```bash
git checkout --track origin/v2_higgsdna
```
### Configuration
- `git config --global user.name "Your Name"`: Sets your name in Git configuration.
- `git config --global user.email "you@example.com"`: Sets your email in Git configuration.
- `git config --global color.ui auto`: Enables colored output in Git.

### Repository Setup
- `git init`: Initializes a new Git repository.
- `git clone <repo-url>`: Clones an existing repository from a remote source.

### Basic Snapshotting
- `git status`: Displays the state of the working directory and staging area.
- `git add <file>`: Stages a file.
- `git add .`: Stages all changes in the current directory.
- `git commit -m "Commit message"`: Commits staged changes with a message.
- `git commit -am "Commit message"`: Adds and commits changes in one step.

### Branching and Merging
- `git branch`: Lists all branches in your repository.
- `git branch <branch-name>`: Creates a new branch.
- `git checkout <branch-name>`: Switches to the specified branch.
- `git checkout -b <branch-name>`: Creates and switches to a new branch.
- `git merge <branch-name>`: Merges the specified branch into the current branch.
- `git branch -d <branch-name>`: Deletes the specified branch.
- `git branch -D <branch-name>`: Force-deletes the specified branch.

### Remote Repositories
- `git remote add <name> <url>`: Adds a remote repository.
- `git remote -v`: Lists the URLs of all remote repositories.
- `git fetch <remote>`: Fetches changes from the remote repository.
- `git pull <remote> <branch>`: Fetches and merges changes from the remote branch into the current branch.
- `git push <remote> <branch>`: Pushes committed changes to the remote branch.
- `git push origin --delete <branch-name>`: Deletes a remote branch.

### Undoing Changes
- `git checkout -- <file>`: Discards changes in the working directory.
- `git reset HEAD <file>`: Unstages a file without discarding changes.
- `git reset --hard`: Discards all local changes.
- `git revert <commit>`: Creates a new commit that undoes changes made in the specified commit.
- `git reset --soft <commit>`: Resets the index to the specified commit without changing the working directory.

### Viewing History
- `git log`: Shows commit history.
- `git log --oneline`: Displays the commit history in a condensed format.
- `git log --graph --oneline --all`: Visualizes the commit history as a graph.
- `git diff`: Shows changes between commits, commit and working tree, etc.
- `git show <commit>`: Displays changes introduced by a specific commit.

### Stashing
- `git stash`: Stashes the current changes in the working directory.
- `git stash list`: Lists all stashes.
- `git stash apply`: Applies the most recent stash.
- `git stash apply stash@{n}`: Applies a specific stash from the stash list.
- `git stash drop`: Deletes the most recent stash.
- `git stash drop stash@{n}`: Deletes a specific stash.

### Submodules
- `git submodule add <repo-url>`: Adds a submodule to your repository.
- `git submodule update --init`: Initializes, fetches, and checks out the content of the submodule.
- `git submodule update --remote`: Updates the submodule to the latest commit.

### Working with Tags
- `git tag`: Lists all tags.
- `git tag <tag-name>`: Creates a new tag.
- `git tag -d <tag-name>`: Deletes a local tag.
- `git push origin <tag-name>`: Pushes a tag to the remote repository.
- `git push origin --tags`: Pushes all tags to the remote repository.

### Advanced Commands
- `git cherry-pick <commit>`: Applies the changes from a specific commit.
- `git rebase <branch>`: Applies commits from another branch onto the current branch.
- `git reflog`: Shows a log of all the references in the local repository.
- `git bisect start`: Starts a bisecting session to find a specific commit that introduced a bug.

### Resolving Conflicts
- `git merge --abort`: Aborts the merge process and attempts to reconstruct the pre-merge state.
- `git mergetool`: Opens a merge tool to resolve conflicts.
- `git add <file>`: After resolving conflicts, stage the resolved file(s).
- `git commit`: Completes the merge after resolving conflicts.

### Cleaning Up
- `git clean -f`: Removes untracked files.
- `git clean -fd`: Removes untracked files and directories.

### Miscellaneous
- `git blame <file>`: Shows who modified each line of a file and when.
- `git shortlog`: Summarizes `git log` output by author.

---
# Vim Commands

## Basic Navigation
- `h`: Move cursor left.
- `j`: Move cursor down.
- `k`: Move cursor up.
- `l`: Move cursor right.
- `0`: Move to the beginning of the line.
- `$`: Move to the end of the line.
- `w`: Move to the beginning of the next word.
- `b`: Move to the beginning of the previous word.
- `G`: Go to the end of the file.
- `gg`: Go to the beginning of the file.
- `:n`: Go to line `n` (e.g., `:10` to go to line 10).
- `Ctrl + f`: Move forward one screen.
- `Ctrl + b`: Move backward one screen.

## Modes
- `i`: Insert mode (start inserting text before the cursor).
- `I`: Insert mode at the beginning of the line.
- `a`: Insert mode (start inserting text after the cursor).
- `A`: Insert mode at the end of the line.
- `o`: Insert a new line below the current line and enter insert mode.
- `O`: Insert a new line above the current line and enter insert mode.
- `Esc`: Return to normal mode.
- `v`: Enter visual mode (select text).
- `V`: Enter visual line mode (select whole lines).
- `Ctrl + v`: Enter visual block mode (select a block of text).

## Editing Text
- `x`: Delete the character under the cursor.
- `dd`: Delete the current line.
- `dw`: Delete from the cursor to the end of the word.
- `d$`: Delete from the cursor to the end of the line.
- `d0`: Delete from the cursor to the beginning of the line.
- `u`: Undo the last action.
- `Ctrl + r`: Redo the last undone action.
- `yy`: Copy (yank) the current line.
- `yw`: Copy (yank) from the cursor to the end of the word.
- `y$`: Copy (yank) from the cursor to the end of the line.
- `p`: Paste after the cursor.
- `P`: Paste before the cursor.
- `r`: Replace the character under the cursor.
- `R`: Enter replace mode (overwrite characters).

## Searching and Replacing
- `/pattern`: Search for `pattern` in the file (e.g., `/foo` to search for "foo").
- `n`: Move to the next occurrence of the search pattern.
- `N`: Move to the previous occurrence of the search pattern.
- `:%s/old/new/g`: Replace all occurrences of `old` with `new` in the file.
- `:%s/old/new/gc`: Replace all occurrences with confirmation.

## Saving and Exiting
- `:w`: Save the current file.
- `:wq`: Save and exit Vim.
- `:q`: Quit Vim.
- `:q!`: Quit without saving changes.
- `:wq!`: Force save and exit (useful when the file is read-only).
- `ZZ`: Save and quit (equivalent to `:wq`).
- `ZQ`: Quit without saving (equivalent to `:q!`).

## Visual Mode
- `v`: Start visual mode.
- `V`: Start visual line mode.
- `Ctrl + v`: Start visual block mode.
- `y`: Yank (copy) the selected text.
- `d`: Delete the selected text.
- `p`: Paste the yanked text after the selection.
- `>`: Indent the selected text.
- `<`: Unindent the selected text.

## Indentation
- `>>`: Indent the current line.
- `<<`: Unindent the current line.
- `=`: Auto-indent the selected text or current line.

## Working with Multiple Files
- `:e filename`: Open `filename` for editing.
- `:bnext` or `:bn`: Go to the next buffer.
- `:bprev` or `:bp`: Go to the previous buffer.
- `:bd`: Close the current buffer.
- `:ls`: List all open buffers.

## Splits and Tabs
- `:split filename`: Open `filename` in a horizontal split.
- `:vsplit filename`: Open `filename` in a vertical split.
- `Ctrl + w, s`: Split the current window horizontally.
- `Ctrl + w, v`: Split the current window vertically.
- `Ctrl + w, w`: Switch between split windows.
- `Ctrl + w, q`: Close the current split window.
- `:tabnew filename`: Open `filename` in a new tab.
- `gt`: Go to the next tab.
- `gT`: Go to the previous tab.
- `:tabclose`: Close the current tab.

## Useful Commands
- `.`: Repeat the last command.
- `:!command`: Run an external shell command (e.g., `:!ls`).
- `:set number`: Show line numbers.
- `:set nonumber`: Hide line numbers.
- `:set ignorecase`: Ignore case in searches.
- `:set noignorecase`: Make searches case-sensitive.
- `:set hlsearch`: Highlight search results.
- `:set nohlsearch`: Disable search result highlighting.

## Registers
- `"a`: Access register `a`.
- `"ap`: Paste the contents of register `a`.
- `"ayy`: Yank into register `a`.
- `:reg`: View the contents of all registers.

## Macros
- `qa`: Start recording a macro into register `a`.
- `q`: Stop recording the macro.
- `@a`: Play the macro stored in register `a`.
- `@@`: Replay the last played macro.

## Exiting Insert Mode
- `jk`: Map `jk` to exit insert mode (can be set in your `.vimrc`).


---
# Bash Commands

## File and Directory Operations
- `ls`: List directory contents.
  - `ls -l`: List with detailed information.
  - `ls -a`: List all files, including hidden ones.
  - `ls -lh`: List with human-readable file sizes.

- `cd <directory>`: Change the current directory.
  - `cd ..`: Move up one directory level.
  - `cd ~`: Change to the home directory.
  - `cd -`: Go back to the previous directory.

- `pwd`: Print the current working directory.

- `mkdir <directory>`: Create a new directory.
  - `mkdir -p <path>`: Create directories along the specified path.

- `rmdir <directory>`: Remove an empty directory.
- `rm <file>`: Remove a file.
  - `rm -r <directory>`: Remove a directory and its contents recursively.
  - `rm -f <file>`: Force removal of a file without prompting.
  - `rm -rf <directory>`: Force remove a directory and its contents.

- `cp <source> <destination>`: Copy files or directories.
  - `cp -r <source> <destination>`: Copy directories recursively.
  - `cp -p <source> <destination>`: Preserve file attributes during copy.

- `mv <source> <destination>`: Move or rename files or directories.

- `touch <file>`: Create an empty file or update the timestamp of an existing file.

- `cat <file>`: Concatenate and display the content of a file.
  - `cat file1 file2 > combined_file`: Concatenate multiple files into one.

- `more <file>`: View the content of a file one screen at a time.
- `less <file>`: View the content of a file with backward navigation.

- `head <file>`: Display the first 10 lines of a file.
  - `head -n <number> <file>`: Display the first `<number>` lines.

- `tail <file>`: Display the last 10 lines of a file.
  - `tail -n <number> <file>`: Display the last `<number>` lines.
  - `tail -f <file>`: Follow the file as it grows, useful for log files.

## Text Processing
- `grep <pattern> <file>`: Search for a pattern in a file.
  - `grep -r <pattern> <directory>`: Recursively search for a pattern in files under a directory.
  - `grep -i <pattern> <file>`: Case-insensitive search.
  - `grep -v <pattern> <file>`: Invert match; display lines that do not match the pattern.
  - `grep -n <pattern> <file>`: Display line numbers with matching lines.

- `sed 's/old/new/g' <file>`: Replace all occurrences of `old` with `new` in a file.
  - `sed -i 's/old/new/g' <file>`: In-place replacement in a file.

- `awk '{print $1, $2}' <file>`: Print specific columns from a file.

- `cut -d '<delimiter>' -f <fields> <file>`: Cut out sections from a file using a delimiter.

- `sort <file>`: Sort lines in a file.
  - `sort -r <file>`: Sort lines in reverse order.
  - `sort -n <file>`: Sort lines numerically.

- `uniq <file>`: Report or filter out repeated lines.
  - `uniq -c <file>`: Count and display occurrences of repeated lines.

- `wc <file>`: Count the number of lines, words, and characters in a file.
  - `wc -l <file>`: Count lines.
  - `wc -w <file>`: Count words.
  - `wc -c <file>`: Count characters.

## File Permissions
- `chmod <permissions> <file>`: Change the file permissions.
  - `chmod 755 <file>`: Give the owner full access and others read and execute access.
  - `chmod +x <file>`: Make a file executable.

- `chown <owner>:<group> <file>`: Change the owner and group of a file.
  - `chown -R <owner>:<group> <directory>`: Change ownership recursively.

- `chgrp <group> <file>`: Change the group ownership of a file.

## Networking
- `ping <host>`: Check connectivity to a host.
- `ifconfig`: Display or configure network interfaces.
- `curl <url>`: Transfer data from or to a server.
  - `curl -O <url>`: Download a file from a URL.
  - `curl -I <url>`: Fetch the headers only.
  
- `wget <url>`: Download files from the web.
  - `wget -c <url>`: Continue a previous download.

- `scp <source> <user@host:destination>`: Securely copy files between hosts.
  - `scp -r <source> <user@host:destination>`: Recursively copy directories.

- `ssh <user@host>`: Securely connect to a remote server.

## Process Management
- `ps`: Display currently running processes.
  - `ps aux`: Display all processes with detailed information.

- `top`: Display real-time system resource usage and running processes.
- `htop`: Enhanced version of `top` with more features (if installed).

- `kill <pid>`: Kill a process by its PID.
  - `kill -9 <pid>`: Force kill a process.
  
- `killall <process_name>`: Kill all processes with a specific name.

- `bg`: Move a job to the background.
- `fg`: Bring a job to the foreground.
- `jobs`: List all jobs.

## Shell Scripting
- `#!/bin/bash`: Shebang line to specify the script should be run in Bash.
- `echo "text"`: Print text to the terminal.
- `read <variable>`: Read user input into a variable.
- `$(command)`: Command substitution; captures the output of a command.
- `var=value`: Assign a value to a variable.
- `if [ condition ]; then ... fi`: If statement.
- `for var in list; do ... done`: For loop.
- `while [ condition ]; do ... done`: While loop.
- `function_name() { ... }`: Define a function.
- `chmod +x script.sh`: Make a script executable.
- `./script.sh`: Run a script.

## Redirection and Pipelines
- `command > file`: Redirect output to a file (overwrite).
- `command >> file`: Append output to a file.
- `command 2> file`: Redirect error output to a file.
- `command1 | command2`: Pipe the output of `command1` to `command2`.
- `command < file`: Use a file as input to a command.

## Archiving and Compression
- `tar -cvf archive.tar <files>`: Create a tar archive.
- `tar -xvf archive.tar`: Extract a tar archive.
- `tar -czvf archive.tar.gz <files>`: Create a compressed tar archive with gzip.
- `tar -xzvf archive.tar.gz`: Extract a compressed tar archive with gzip.
- `tar -cjvf archive.tar.bz2 <files>`: Create a compressed tar archive with bzip2.
- `tar -xjvf archive.tar.bz2`: Extract a compressed tar archive with bzip2.
- `zip archive.zip <files>`: Create a zip archive.
- `unzip archive.zip`: Extract a zip archive.
- `gzip <file>`: Compress a file using gzip.
- `gunzip <file.gz>`: Decompress a gzip file.

## Disk Usage
- `df -h`: Display disk space usage in human-readable format.
- `du -h <directory>`: Display disk usage of a directory and its contents.
- `du -sh <directory>`: Display total disk usage of a directory.

## Package Management (Debian/Ubuntu)
- `sudo apt update`: Update the package list.
- `sudo apt upgrade`: Upgrade all installed packages.
- `sudo apt install <package>`: Install a package.
- `sudo apt remove <package>`: Remove a package.
- `sudo apt autoremove`: Remove unnecessary packages.
- `sudo apt search <package>`: Search for a package in the repository.
- `sudo apt list --installed`: List all installed packages.

## Miscellaneous
- `man <command>`: Display the manual page for a command.
- `history`: Show command history.
  - `!n`: Re-execute command number `n`.
  - `!!`: Re-execute the last command.
  
- `alias name='command'`: Create an alias for a command.
- `unalias name`: Remove an alias.
- `clear`: Clear the terminal screen.
- `date`: Display or set the system date and time.
- `cal`: Display a calendar.
- `uptime`: Show how long the system has been running.
- `whoami`: Display the current user.
- `sudo <command>`: Run a command as the superuser.
- `exit`: Exit the current shell session.
- `echo $SHELL`: Display the current shell.
- `uname -a`: Display system information.

---
