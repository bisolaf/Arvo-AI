import os
from parser import parse_deployment_request
from repo import clone_repo, analyze_repo
from deploy import generate_terraform_ec2, pre_deployment_check
import subprocess
from dotenv import load_dotenv
import time
import json

load_dotenv(dotenv_path=".creds")

def run_terraform():
    """Run Terraform init and apply automatically."""
    try:
        print("Running terraform init...")
        subprocess.run(["terraform", "init"], check=True)
        
        print("Running terraform plan...")
        subprocess.run(["terraform", "plan"], check=True)
        
        print("Running terraform apply...")
        subprocess.run(["terraform", "apply", "-auto-approve"], check=True)
        
        print("DEPLOYMENT COMPLETE!")
        
        result = subprocess.run(["terraform", "output", "-json"], capture_output=True, text=True)
        return json.loads(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"Terraform command failed: {e}")
        return None

def check_application_status(app_url, max_wait=300):
    """Check if the application is accessible via HTTP"""
    print(f"Checking application accessibility at {app_url} ...")
    start_time = time.time()

    for attempt in range(1, 21):
        try:
            result = subprocess.run(
                ["curl", "-s", "--connect-timeout", "10", app_url],
                capture_output=True, text=True
            )

            if result.returncode == 0 and len(result.stdout) > 0:
                print("Application is accessible and responding!")
                return True
            else:
                elapsed = int(time.time() - start_time)
                print(f"Attempt {attempt}/20: Application not yet accessible ({elapsed}s elapsed)")
        except subprocess.CalledProcessError:
            pass
        time.sleep(15)

    print("Application not responding after multiple attempts.")
    return False

def show_enhanced_results(app_url):
    """Show deployment results"""
    print("🎉 AUTO-DEPLOYMENT SYSTEM - RESULTS")
    print(f"APPLICATION URL: {app_url}")
    print("DEPLOYMENT PROCESS DETAILS:")
    print("   • Infrastructure provisioned automatically with Terraform")
    print("   • Dependencies installed automatically (Python, Flask, Git)")
    print("   • Repository cloned automatically from GitHub")
    print("   • Application started automatically with proper configuration")
    print("   • Public URL is accessible immediately")

def main():
    if not pre_deployment_check():
        print("Pre-deployment checks failed. Please fix the issues above.")
        return
    
    nl_input = input("Enter deployment request: ")
    repo_url = input("Enter GitHub repo URL: ")
    
    try:
        deployment_info = parse_deployment_request(nl_input)
        print(f"Parsed deployment: {deployment_info}")
    except Exception as e:
        print(f"Using defaults due to parsing error: {e}")
        deployment_info = {"instance_type": "t2.micro", "framework": "Flask"}

    try:
        repo_path = clone_repo(repo_url)
        repo_info = analyze_repo(repo_path)
        print(f"Repository analysis: {repo_info}")
    except Exception as e:
        print(f"Could not analyze repo (will handle during deployment): {e}")
        repo_info = {"framework": "Flask"}

    print(f"Generating Terraform configuration...")
    tf_file = generate_terraform_ec2(
        repo_url=repo_url,
        instance_type=deployment_info.get("instance_type", "t2.micro"),
        framework=repo_info.get("framework", "Flask"),
        ssh_user=None,  # no SSH needed
    )
    print(f"Terraform config generated: {tf_file}")

    print(f"Starting deployment...")
    outputs = run_terraform()
    if not outputs:
        print("Deployment failed. Check Terraform logs.")
        return

    app_url = outputs.get("app_url", {}).get("value")
    if not app_url:
        print("No application URL found in Terraform outputs.")
        return

    if check_application_status(app_url):
        show_enhanced_results(app_url)
        print("FULL DEPLOYMENT SUCCESS!")
    else:
        print("Deployment completed but application not yet accessible. Check logs.")

if __name__ == "__main__":
    main()
