# List of commands which we are using frequently

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

