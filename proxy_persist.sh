#!/bin/bash -e
set -o nounset

echo ------------------------
echo Persisting report_dir in Git

pwd

report_dir=${1:-$report_dir}
git_branch=${2:-$git_branch}

mkdir -p /tmp/.ssh
SSH_FILE=/tmp/.ssh/id_rsa

if [ -z ${SSH_PRIVATE_KEY+x} ]; then
    echo SSH_PRIVATE_KEY not set
else
    echo Create SSH file
    echo "${SSH_PRIVATE_KEY}" > $SSH_FILE
    chmod 400 $SSH_FILE
fi

git config --global user.name "Jenkins Agent"
git config --global user.email "Jenkins_Agent@localhost"
git add $report_dir
git commit -m "adding report"

remote_url=$(git remote get-url origin)
if [[ $remote_url =~ ^https.* ]]; then
    path=$(echo $remote_url | sed -e "s|https://.*gitlab.com/||g")
    git remote set-url origin 'git@gitlab.com:'${path%/}
fi

GIT_SSH_COMMAND="ssh -o 'StrictHostKeyChecking no' -i $SSH_FILE" git push origin $(git rev-parse HEAD):$git_branch