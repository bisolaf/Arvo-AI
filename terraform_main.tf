provider "aws" {
  region = "us-east-1"
}

resource "aws_key_pair" "app_key" {
  key_name   = "my-app-key-${random_string.suffix.result}"
  public_key = file("/Users/bisolafolarin/.ssh/id_rsa_tf.pub")
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

resource "aws_security_group" "app_sg" {
  name        = "app_sg_${random_string.suffix.result}"
  description = "Allow SSH and app access"
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["128.148.205.52/32"]
  }
  
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "app_server" {
  ami           = "ami-0c02fb55956c7d316"
  instance_type = "t2.micro"
  vpc_security_group_ids = [aws_security_group.app_sg.id]
  key_name = aws_key_pair.app_key.key_name
  
  user_data = base64encode(<<-EOF
#!/bin/bash
set -x  

exec > >(tee /var/log/user-data.log) 2>&1

echo "=== AUTO-DEPLOYMENT STARTED AT $(date) ==="
echo "Repository: https://github.com/Arvo-AI/hello_world"
echo "Framework: flask"
echo "App Port: 5000"


log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Update system
log "Updating system packages..."
apt update
apt install -y python3-pip git curl wget

log "Setting up Python environment..."
if ! pip3 --version; then
    curl -fsSL https://bootstrap.pypa.io/get-pip.py | python3
fi


cd /home/ubuntu
log "Working directory: $(pwd)"

log "Cloning repository from https://github.com/Arvo-AI/hello_world..."
if timeout 60 git clone https://github.com/Arvo-AI/hello_world app 2>&1; then
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
    <p>Successfully deployed from: https://github.com/Arvo-AI/hello_world</p>
    <p>Framework: flask</p>
    <p>Instance: t2.micro</p>
    '''

@app.route('/health')
def health():
    return {'status': 'healthy'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
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
    <p>Repository clone failed: https://github.com/Arvo-AI/hello_world</p>
    <p>But your deployment system works!</p>
    '''

@app.route('/health')
def health():
    return {'status': 'healthy'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
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

  EOF
  )
  
  tags = {
    Name = "AutoDeploy-App-Server-x6ku56i4"
    Framework = "flask"
  }
}

output "public_ip" {
  value = aws_instance.app_server.public_ip
}

output "app_url" {
  value = "http://${aws_instance.app_server.public_ip}:5000"
}

output "ssh_command" {
  value = "ssh -i /Users/bisolafolarin/.ssh/id_rsa_tf ubuntu@${aws_instance.app_server.public_ip}"
}

output "status_check" {
  value = "ssh -i /Users/bisolafolarin/.ssh/id_rsa_tf ubuntu@${aws_instance.app_server.public_ip} 'cat setup_complete.txt'"
}
