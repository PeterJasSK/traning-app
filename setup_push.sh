

#!/bin/bash

# Navigate to your project folder
cd ~/trener_app || { echo "Folder not found"; exit 1; }

# Initialize git if needed
if [ ! -d ".git" ]; then
    git init
    echo "Git repository initialized."
fi

# Add GitHub remote
git remote remove origin 2>/dev/null
git remote add origin git@github.com:JJSVK150/trener_app.git
echo "GitHub remote set."

# Generate SSH key if not exists
if [ ! -f "~/.ssh/id_ed25519" ]; then
    ssh-keygen -t ed25519 -C "janjas150@gmail.com" -f ~/.ssh/id_ed25519 -N ""
    echo "SSH key generated."
fi

# Start ssh-agent and add key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Show SSH public key for GitHub
echo ""
echo "Copy the following key and add it to GitHub → Settings → SSH and GPG keys → New SSH key:"
cat ~/.ssh/id_ed25519.pub
echo ""

# Stage all files
git add .

# Commit changes
git commit -m "Upload current version from PythonAnywhere" 2>/dev/null || echo "Nothing to commit"

# Test SSH connection
ssh -T git@github.com

echo ""
echo "If SSH authentication succeeds, run:"
echo "git push -u origin main"




