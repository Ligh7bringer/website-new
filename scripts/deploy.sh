#!/bin/bash

echo -e "\033[0;32mDeploying updates to GitHub...\033[0m"

# activate virtualenv
# source .venv/bin/activate
# get up-to-date data from github
python3 github_stats.py

git add .

# generate a commit message
msg="rebuilding site $(date)"
if [ $# -eq 1 ]; then
  msg="$1"
fi

# commit
git commit -m "$msg"

# push
git push origin main
