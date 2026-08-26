import re
import subprocess
import sys


def modify_sub_file(sub_file_path, failed_job_numbers, output_sub_file_path):
    # Read the content of the .sub file
    with open(sub_file_path, 'r') as file:
        content = file.readlines()

    # Modify the lines as needed, but without replacing entire lines
    new_content = []
    for line in content:
        # Modify arguments = $(ProcId) to arguments = $(arg)
        if 'arguments = $(ProcId)' in line:
            line = line.replace('$(ProcId)', '$(arg)')
        # Modify output and error paths to use $(arg)
        if 'output = ' in line:
            line = line.replace('$(ProcId).out', '$(ProcId).$(arg).out')
        if 'error = ' in line:
            line = line.replace('$(ProcId).err','$(ProcId).$(arg).err')

        # Modify the queue line to include the failed job numbers
        if re.match(r'^\s*queue\b', line):
            failed_jobs_str = " ".join(str(job) for job in failed_job_numbers)
            line = re.sub(r'queue.*', f'queue arg in {failed_jobs_str}', line)

        new_content.append(line)

    # Save the modified content to the new .sub file
    with open(output_sub_file_path, 'w') as file:
        file.writelines(new_content)

    print(f"Modified .sub file saved as: {output_sub_file_path}")


def submit_condor_job(sub_file_path):
    # Submit the Condor job using the condor_submit command
    result = subprocess.run(['condor_submit', sub_file_path], capture_output=True, text=True)
    if result.returncode != 0:
        print("Failed with standard condor_submit. Trying condor_submit -spool...")
        result = subprocess.run(['condor_submit', '-spool', sub_file_path], capture_output=True, text=True)

    if result.returncode == 0:
        print(f"Condor job successfully submitted using: {sub_file_path}")
    else:
        print("Failed to submit Condor job. Error: {result.stderr}")


def main():
    # Ensure that we have the correct number of arguments
    if len(sys.argv) < 3:
        print("Usage: python script.py <path_to_sub_file> <failed_job_numbers>")
        sys.exit(1)

    # Path to the original .sub file
    sub_file_path = sys.argv[1]  # First argument is the path to the .sub file

    # Read failed job numbers from the second argument
    failed_job_numbers = list(map(int, sys.argv[2].split()))

    # Path to the new .sub file where modifications will be saved
    output_sub_file_path = sub_file_path.replace('.sub', '_modified.sub')  # Saving with "_modified"

    # Modify the .sub file and save the modified version
    modify_sub_file(sub_file_path, failed_job_numbers, output_sub_file_path)

    # Submit the Condor job with the modified .sub file
    submit_condor_job(output_sub_file_path)


if __name__ == "__main__":
    main()
