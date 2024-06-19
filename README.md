# Set up fresh codespace

```
curl https://pyenv.run | bash

```

Add the following to ~/.bashrc

```
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
```

Then continue with setup:

```
pipenv install
pipx install aws-sso-util
pipx install aws-export-credentials
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
export AWS_REGION=eu-west-2
export AWS_DEFAULT_SSO_REGION=eu-west-2
export AWS_DEFAULT_SSO_START_URL=https://d-9c6771b41b.awsapps.com/start#/
aws-sso-util configure profile default
aws-export-credentials --env-export
#or
eval "$(aws-export-credentials --env-export)"
cd infra
npm i
npm i -g cdk
cdk deploy
```

# To set secrets

```
aws secretsmanager create-secret --name <secret> --secret-string <value>
```

# To test locally with whitenoise instead of runserver static

```
export CLOUDFRONT_DISTRIBUTION_DOMAINNAME=d3ag4u0wverghk.cloudfront.net
export BUCKET_NAME=dev-infrastack-djangobucketbc6e918a-k4oodxzffone
export CLOUDFRONT_DISTRIBUTION_ID=E1SSVT4MU1CCD2
export DYNAMODB_SESSIONS_TABLE_NAME=Dev-InfraStack-Sessions8896A56D-IPNJ1EI9KM
export DJANGO_LOG_LEVEL=DEBUG
export TABLE_NAME=Dev-InfraStack-VersionTable780A7FFE-F4NFZ0CZHQ8Z
pipenv run python manage.py runserver --nostatic
```

# To install x86 docker

```
curl https://raw.githubusercontent.com/Homebrew/homebrew-core/05d02418e00ef6e9af79018e3655536063f68ab2/Formula/q/qemu.rb -o qemu.rb
curl https://raw.githubusercontent.com/Homebrew/homebrew-core/442f9cc511ce6dfe75b96b2c83749d90dde914d2/Formula/c/capstone.rb -o capstone.rb
brew unlink qemu
brew install qemu.rb
brew unlink capstone
brew install capstone.rb
```

# To install
