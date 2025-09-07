import requests
import os
import subprocess
import sys
import random
import string

def get_my_ip():
    try:
        return requests.get("https://checkip.amazonaws.com").text.strip()
    except:
        return "0.0.0.0"

def ensure_ssh_keys():
    public_key_path = os.path.expanduser("~/.ssh/id_rsa_tf.pub")
    private_key_path = os.path.expanduser("~/.ssh/id_rsa_tf")
    
    if not os.path.exists(private_key_path) or not os.path.exists(public_key_path):
        print("SSH keys not found. Generating new key pair...")
        
        ssh_dir = os.path.expanduser("~/.ssh")
        os.makedirs(ssh_dir, exist_ok=True)
        
        for key_file in [private_key_path, public_key_path]:
            if os.path.exists(key_file):
                os.remove(key_file)
        
        try:
            subprocess.run([
                "ssh-keygen", 
                "-t", "rsa", 
                "-b", "4096",
                "-f", private_key_path,
                "-N", "", 
                "-C", "terraform-deployment"
            ], check=True)
            
            
            os.chmod(private_key_path, 0o600)
            os.chmod(public_key_path, 0o644)
            
            print("SSH keys generated successfully")
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to generate SSH keys: {e}")
            sys.exit(1)
    else:
        os.chmod(private_key_path, 0o600)
        os.chmod(public_key_path, 0o644)
        print("SSH keys found and permissions set")
    
    return private_key_path, public_key_path

def generate_terraform_ec2(repo_url, instance_type="t2.micro", framework="Flask", ssh_user="ubuntu"):
    if not framework:
        framework = "Flask"
    framework = framework.lower()

    my_ip = get_my_ip()
    
    private_key_path, public_key_path = ensure_ssh_keys()
    
    public_key_path = public_key_path.replace("\\", "/")
    private_key_path = private_key_path.replace("\\", "/")

    packages = ["python3-pip", "git", "curl", "wget"]
    if framework == "node.js":
        packages += ["nodejs", "npm"]

    app_port = "5000" if framework == "flask" else "8000" if framework == "django" else "3000"

    user_data_script = f"""#!/bin/bash
set -x  

exec > >(tee /var/log/user-data.log) 2>&1

echo "=== AUTO-DEPLOYMENT STARTED AT $(date) ==="
echo "Repository: {repo_url}"
echo "Framework: {framework}"
echo "App Port: {app_port}"


log() {{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}}

# Update system
log "Updating system packages..."
apt update
apt install -y {' '.join(packages)}

log "Setting up Python environment..."
if ! pip3 --version; then
    curl -fsSL https://bootstrap.pypa.io/get-pip.py | python3
fi


cd /home/ubuntu
log "Working directory: $(pwd)"

log "Cloning repository from {repo_url}..."
if timeout 60 git clone {repo_url} app 2>&1; then
    log "Repository cloned successfully"
    chown -R ubuntu:ubuntu app
    cd app
    
    if [ -d "examples/hello" ]; then
        log "Detected Flask example app, changing directory..."
        cd examples/hello
        
        if [ ! -f "requirements.txt" ]; then
            log "Creating requirements.txt for Flask example"
            echo "Flask==2.3.3" > requirements.txt
        fi

        log "Installing Python requirements..."
        sudo -u ubuntu pip3 install -r requirements.txt --user
        
        log "Starting Flask application..."
        sudo -u ubuntu bash -c "nohup python3 app.py > /home/ubuntu/app.log 2>&1 &"
        
    else
        log "Repository does not contain a supported app structure, creating a default Flask app."
        
        if [ ! -f "requirements.txt" ]; then
            log "Creating requirements.txt"
            echo "Flask==2.3.3" > requirements.txt
        fi

        log "Installing Python requirements..."
        sudo -u ubuntu pip3 install -r requirements.txt --user
        
        if [ ! -f "app.py" ]; then
            log "Creating app.py"
            cat > app.py << 'FLASK_APP_EOF'
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '''
    <h1> App deployed!</h1>
    <p>Successfully deployed from: {repo_url}</p>
    <p>Framework: {framework}</p>
    <p>Instance: {instance_type}</p>
    '''

@app.route('/health')
def health():
    return {{'status': 'healthy'}}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port={app_port}, debug=False)
FLASK_APP_EOF
        fi
        
        log "Starting Flask application..."
        sudo -u ubuntu bash -c "nohup python3 app.py > /home/ubuntu/app.log 2>&1 &"
        
    fi
    
else
    log "Repository clone failed, creating default app"
    mkdir -p app
    cd app
    chown -R ubuntu:ubuntu /home/ubuntu/app
    
    echo "Flask==2.3.3" > requirements.txt
    sudo -u ubuntu pip3 install Flask --user
    
    cat > app.py << 'DEFAULT_APP_EOF'
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '''
    <h1>Default App</h1>
    <p>Repository clone failed: {repo_url}</p>
    <p>But your deployment system works!</p>
    '''

@app.route('/health')
def health():
    return {{'status': 'healthy'}}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port={app_port}, debug=False)
DEFAULT_APP_EOF

    log "Starting Flask application..."
    sudo -u ubuntu bash -c "nohup python3 app.py > /home/ubuntu/app.log 2>&1 &"
    
fi


chown -R ubuntu:ubuntu /home/ubuntu/app

sleep 3
if pgrep -f "python.*app.py" > /dev/null; then
    log "Flask app started successfully"
    echo "SUCCESS - App running at $(date)" > /home/ubuntu/setup_complete.txt
else
    log "Flask app failed to start"
    echo "FAILED - Check app.log for details" > /home/ubuntu/setup_complete.txt
fi

chown ubuntu:ubuntu /home/ubuntu/setup_complete.txt
log "=== DEPLOYMENT COMPLETED AT $(date) ==="
"""
    unique_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    tf_content = f"""provider "aws" {{
  region = "us-east-1"
}}

resource "aws_key_pair" "app_key" {{
  key_name   = "my-app-key-${{random_string.suffix.result}}"
  public_key = file("/Users/bisolafolarin/.ssh/id_rsa_tf.pub")
}}

resource "random_string" "suffix" {{
  length  = 8
  special = false
  upper   = false
}}

resource "aws_security_group" "app_sg" {{
  name        = "app_sg_${{random_string.suffix.result}}"
  description = "Allow SSH and app access"
  
  ingress {{
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["{my_ip}/32"]
  }}
  
  ingress {{
    from_port   = {app_port}
    to_port     = {app_port}
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}
  
  egress {{
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }}
}}

resource "aws_instance" "app_server" {{
  ami           = "ami-0c02fb55956c7d316"
  instance_type = "{instance_type}"
  vpc_security_group_ids = [aws_security_group.app_sg.id]
  key_name = aws_key_pair.app_key.key_name
  
  user_data = base64encode(<<-EOF
{user_data_script}
  EOF
  )
  
  tags = {{
    Name = "AutoDeploy-App-Server-{unique_suffix}"
    Framework = "{framework}"
  }}
}}

output "public_ip" {{
  value = aws_instance.app_server.public_ip
}}

output "app_url" {{
  value = "http://${{aws_instance.app_server.public_ip}}:{app_port}"
}}

output "ssh_command" {{
  value = "ssh -i {private_key_path} ubuntu@${{aws_instance.app_server.public_ip}}"
}}

output "status_check" {{
  value = "ssh -i {private_key_path} ubuntu@${{aws_instance.app_server.public_ip}} 'cat setup_complete.txt'"
}}
"""

    tf_file = "terraform_main.tf"
    with open(tf_file, "w") as f:
        f.write(tf_content)

    return tf_file

def pre_deployment_check():
    """Run basic pre-deployment checks."""
    print("=== PRE-DEPLOYMENT CHECKS ===")
    
    # Check Terraform
    try:
        result = subprocess.run(["terraform", "version"], capture_output=True, text=True)
        print(f"Terraform: {result.stdout.strip().split()[1]}")
    except:
        print("Terraform not found")
        return False
    
    # Check AWS CLI
    try:
        result = subprocess.run(["aws", "sts", "get-caller-identity"], capture_output=True, text=True)
        if result.returncode == 0:
            print("AWS credentials configured")
        else:
            print("AWS credentials not configured")
            return False
    except:
        print("AWS CLI not found (using environment variables)")
    
    # Check IP
    my_ip = get_my_ip()
    print(f"Your IP: {my_ip}")
    
    return True