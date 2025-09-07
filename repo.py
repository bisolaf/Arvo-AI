import os
import subprocess
import json

def clone_repo(repo_url, dest_dir="temp_repo"):
    if os.path.exists(dest_dir):
        subprocess.run(["rm", "-rf", dest_dir])
    subprocess.run(["git", "clone", repo_url, dest_dir])
    return dest_dir

def analyze_repo(repo_path):
    result = {"framework": None, "dependencies": [], "start_command": None}
    
    if os.path.exists(os.path.join(repo_path, "requirements.txt")):
        with open(os.path.join(repo_path, "requirements.txt")) as f:
            reqs = f.read().splitlines()
            result["dependencies"] = reqs
            if "flask" in reqs:
                result["framework"] = "Flask"
                result["start_command"] = "python app.py"
            elif "django" in reqs:
                result["framework"] = "Django"
                result["start_command"] = "python manage.py runserver 0.0.0.0:8000"

    if os.path.exists(os.path.join(repo_path, "package.json")):
        with open(os.path.join(repo_path, "package.json")) as f:
            pkg = json.load(f)
            result["dependencies"] = list(pkg.get("dependencies", {}).keys())
            result["framework"] = "Node.js"
            result["start_command"] = "npm start"
            
    return result
