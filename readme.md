# Ticker API
The API returns the historical data of the ticker.

## How to set up local environment

### One time set up
> python3 -m venv .venv
> echo "*" > .venv/.gitignore
> source .venv/bin/activate
> pip install -r ./app/requirements.txt
> pip install "fastapi[standard]"
> deactivate

### How to run the application locally
> fastapi dev app/main.py

## How to deploy this in production? 🤔

### Requirement

You must have logged in AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html

### Create an Elastic Container Registry (ECR) 🏗

1. make ecr

### Lets deploy Lambda and ApiGateway 🚀

1. make deploy

### References

1. https://towardsdatascience.com/building-a-serverless-containerized-machine-learning-model-api-using-aws-lambda-api-gateway-and-a73a091ff82e

2. https://www.deadbear.io/simple-serverless-fastapi-with-aws-lambda/

3. https://www.youtube.com/watch?v=wlVcso4Ut5o
