#!/usr/bin/env python3
"""
Automatic deployment to GitHub
"""
import os
import subprocess
import sys

def run_command(cmd, check=True):
    """Run shell command"""
    print(f"🔧 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return False
    return True

def deploy_to_github():
    """Deploy to GitHub automatically"""
    print("🚀 Starting automatic deployment to GitHub...")
    
    # Get GitHub username
    username = input("📝 Enter your GitHub username: ").strip()
    if not username:
        print("❌ GitHub username is required!")
        return False
    
    repo_name = "video-splitter"
    repo_url = f"https://github.com/{username}/{repo_name}.git"
    
    print(f"📍 Repository will be: {repo_url}")
    
    # Initialize git if not already done
    if not os.path.exists(".git"):
        if not run_command("git init"):
            return False
    
    # Add all files
    if not run_command("git add ."):
        return False
    
    # Initial commit
    if not run_command('git commit -m "🎬 Initial release: Video Splitter with automatic builds"'):
        return False
    
    # Add remote
    if not run_command(f"git remote add origin {repo_url}"):
        return False
    
    # Push to GitHub
    if not run_command("git push -u origin main"):
        print("⚠️ Push failed. You may need to:")
        print("   1. Create the repository on GitHub first")
        print("   2. Run: git push -u origin main")
        return False
    
    print("✅ Successfully deployed to GitHub!")
    print(f"🌐 Repository: https://github.com/{username}/{repo_name}")
    print("📋 Next steps:")
    print("   1. Go to your repository on GitHub")
    print("   2. Go to Settings → Secrets and variables → Actions")
    print("   3. Create a release with tag v1.0.0")
    print("   4. Wait for automatic builds to complete")
    
    return True

if __name__ == "__main__":
    deploy_to_github()
