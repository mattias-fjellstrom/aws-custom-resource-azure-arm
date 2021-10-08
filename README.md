# Deploy Azure ARM-templates via AWS CloudFormation

Imagine you could use your favorite infrastructure provisioning tool (_CloudFormation_) to deploy resources to your favorite cloud provider (_Azure_). If that idea tickles your fancy, read on. This repository shows you how to realize this idea. We will create a CloudFormation custom resource backed by a Lambda function. This function will use an Azure service principal in order to set up Azure infrastructure via ARM-templates. The ARM-template is passed in as a parameter to the custom resource.

## Disclaimer

The CloudFormation custom resource will create a new resource group, or use an existing resource group if one exists with the name provided during deployment. When you delete the corresponding CloudFormation stack the Azure resource group will be deleted as well. You have been warned.

## Prerequisites

As this is a rather advanced example I will assume you know what you are getting yourself into. In short, to follow this example as-is you will need the AWS CLI, the SAM CLI, and Docker. The commands shown below assumes you use the default AWS profile.

## How to set this up

### Create an app registration in Azure

To authenticate the API calls from AWS to Azure we need to create an app registration and assign an appropriate role to the resulting service principal. It is not possible to create this registration using regular ARM templates or Azure Bicep. Follow the steps below to set this up.

1. Go to the [Azure portal](https://portal.azure.com/)
1. Go to Azure Active Directory
1. Click on `App registrations` in the left-hand menu
1. Click on `+ New registration`
1. Give the registration a suitable name, e.g. `aws-deployment-app`
1. Click on `Register`
1. Copy and save the value for the `Application (client ID)` and the `Directory (tenant) ID` shown on the overview page
1. Click on `Certificates & secrets` in the left-hand menu
1. Click on `+ New client secret`
1. Enter a description for the secret and set a suitable expiration time, then click on `Add`
1. Copy and save the secret value

The three values you have stored from the above procedure will be used as input parameters when we set up the CloudFormation custom resource in AWS. Follow the steps below to assign an appropriate role to the service principal.

1. Go to your subscription
1. Click on `Access control (IAM)` in the left-hand menu
1. Click on `+ Add` then on `Add role assignment`
1. Select a role, e.g. `Contributor` and search for the name of the service principal and select it
1. Click `Save`

The role you assign will determine what operations the custom resource in AWS will be able to do. To cover many different scenarios you should set the `Contributor` role. If your template includes role-assignments you will need to give your service principal additional roles, or even set it as `Owner` on your subscription.

### Create the Custom Resource in AWS

Now we are ready to create the CloudFormation custom resource in AWS. We will use AWS SAM for this purpose.

```bash
# build the custom resource
sam build --use-container

# deploy the custom resource
sam deploy --guided
```

SAM will ask you to provide a number of inputs before it creates the custom resource. When prompted, provide the values for the client ID, the client Secret, and your tenant ID.

### Hello World example

Now we have everything we need to deploy ARM-templates from within our CloudFormation templates. A sample hello-world resource is shown below. The custom resource `ServiceToken` is available as an exported value in CloudFormation, we can reference it with `!ImportValue AzureResourceManager`.

```yaml
Parameters:
  AzureSubscriptionID:
    Type: String

  AzureResourceGroup:
    Type: String

  AzureLocation:
    Type: String

Resources:
  AzureResourceManagerDeployment:
    Type: Custom::AzureResourceManager
    Properties:
      ServiceToken: !ImportValue AzureResourceManager
      SubscriptionID: !Ref AzureSubscriptionID
      ResourceGroup: !Ref AzureResourceGroup
      Location: !Ref AzureLocation
      DeploymentName: "aws-deployment"
      TemplateParameters:
        yourName: "Mattias"
      Template: |
        {
          "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
          "contentVersion": "1.0.0.0",
          "parameters": {
            "yourName": {
              "type": "string"
            }
          },
          "variables": {
            "hello": "Hello World! - Hi"
          },
          "resources": {},
          "outputs": {
            "helloWorld": {
              "type": "string",
              "value": "[format('{0} {1}', variables('hello'), parameters('yourName'))]"
            }
          }
        }

Outputs:
  HelloWorld:
    Value: !GetAtt AzureResourceManagerDeployment.helloWorld
```

You must provide `SubscriptionID`, `ResourceGroup`, `Location` and `Template` when you create the resource. The `DeploymentName` is optional. If your ARM-template requires that you specify input parameters you can provide these in `TemplateParameters`. Any outputs from your deployment can be accessed with `!GetAtt <resource logical name>.<ARM-template output value>`.

### Advanced example

An advanced example is provided in [template.yaml](./examples/template.yaml). This example creates an Azure Container Instance and an AWS HTTP API Gateway. The API Gateway will direct traffic to the container in Azure. Deploy this example with the following command.

```bash
aws cloudformation deploy \
    --stack-name AzureExample \
    --template-file ./cloudformation/template.yaml \
    --parameter-overrides \
        AzureSubscriptionID=<subscription ID> \
        AzureResourceGroup=<resource group name> \
        AzureLocation=<Azure location>
```

## Limitations

- As of October 2021 there is no support to transform a Bicep template to an ARM-template using the Azure SDK for Python. As far as I know this is only possible using the Bicep C# library. Thus the example provided here does not support Bicep templates.
