#!/bin/sh

echo "You probably want to look at the script."
exit 1

git filter-branch --env-filter '

an="$GIT_AUTHOR_NAME"
am="$GIT_AUTHOR_EMAIL"
cn="$GIT_COMMITTER_NAME"
cm="$GIT_COMMITTER_EMAIL"

if [ "$GIT_COMMITTER_EMAIL" = "deploy@domU-12-31-39-0C-29-A2.compute-1.internal" ]
then
    cn="Jason Hansen"
    cm="jhansen@engineyard.com"
fi
if [ "$GIT_AUTHOR_EMAIL" = "deploy@domU-12-31-39-0C-29-A2.compute-1.internal" ]
then
    an="Jason Hansen"
    am="jhansen@engineyard.com"
fi

export GIT_AUTHOR_NAME="$an"
export GIT_AUTHOR_EMAIL="$am"
export GIT_COMMITTER_NAME="$cn"
export GIT_COMMITTER_EMAIL="$cm"
'
