import matplotlib.pyplot as plt

def plot_abcd_yields(abcd_dict, output_path="abcd_yields.png"):
    labels = ["B", "C", "D"]
    values = [abcd_dict["N_B"], abcd_dict["N_C"], abcd_dict["N_D"]]
    plt.figure(figsize=(6, 4))
    bars = plt.bar(labels, values, color=["skyblue", "orange", "green"])
    for bar, val in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width()/2, val + 0.5, f"{val:.1f}", ha='center')
    plt.title("Yields in Regions B, C, D")
    plt.ylabel("Events")
    plt.savefig(output_path)
    plt.close()

def plot_closure_test(abcd_dict, output_path="abcd_closure.png"):
    obs = abcd_dict["N_A_obs"]
    est = abcd_dict["N_A_est"]
    err = abcd_dict["N_A_est_err"]

    plt.figure(figsize=(4, 6))
    bars = plt.bar(["Observed", "Estimated"], [obs, est], yerr=[0, err], capsize=6, color=["#9467bd", "#d62728"])
    for bar, val in zip(bars, [obs, est]):
        plt.text(bar.get_x() + bar.get_width()/2, val + 0.5, f"{val:.1f}", ha='center')
    plt.title("ABCD Closure in Region A")
    plt.ylabel("Events in Region A")
    plt.savefig(output_path)
    plt.close()

