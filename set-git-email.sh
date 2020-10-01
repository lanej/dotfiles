#/bin/sh
echo 'Git email:'
read email
git config --global user.email "$email"
