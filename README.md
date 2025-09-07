Deploy Application

The deployment process is managed by a custom Python script that uses Terraform to provision and configure the cloud infrastructure.

Features
Automated Deployment: Deploy the entire application to an AWS EC2 instance with a single command.

Dynamic URL: The deployment script automatically generates a public URL for your application.

Git Integration: The script can clone a specified GitHub repository to deploy your own custom application.

To run:

AWS CLI: Configure your AWS credentials using the AWS CLI. The script needs permission to create EC2 instances, security groups, and key pairs. Create a .creds file

Python: The deployment script is a Python 3 file.

Requests Library: Install the Python requests library (pip3 install requests).

How to Deploy
Make sure you have all the prerequisites installed.

Run the deploy.py script from your terminal: python main.py

The script will generate a terraform_main.tf file and execute the deployment.

Once the deployment is complete, the script will output the application URL and SSH command for connecting to your instance.

ssh -i ~/.ssh/id_rsa_tf ubuntu@<your_instance_ip> 'cat setup_complete.txt'