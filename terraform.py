import subprocess

def apply_terraform(tf_file):
    subprocess.run(["terraform", "init"])
    subprocess.run(["terraform", "apply", "-auto-approve"])
