from crhelper import CfnResource
from deployer import Deployer
import logging


logger = logging.getLogger(__name__)
helper = CfnResource()


def handler(event, context):
    helper(event, context)


@helper.create
@helper.update
def create_or_update(event, _):
    logger.info("Handling CREATE or UPDATE event", event)
    deployer = get_deployer_for_event(event)
    deployer.deploy()
    helper.Data.update(deployer.outputs)


@helper.delete
def delete(event, _):
    logger.info("Handling DELETE event", event)
    deployer = get_deployer_for_event(event)
    deployer.destroy()


def get_deployer_for_event(event):
    deployment_metadata = get_deployment_metadata(event)
    resource_properties = event["ResourceProperties"]

    return Deployer(
        subscription_id=resource_properties["SubscriptionID"],
        resource_group_name=resource_properties["ResourceGroup"],
        location=resource_properties["Location"],
        template=resource_properties["Template"],
        parameters=resource_properties.get("TemplateParameters", {}),
        deployment_name=resource_properties.get("DeploymentName", "aws-deployment"),
        tags=deployment_metadata
    )


def get_deployment_metadata(event):
    stack_id = event["StackId"]
    aws_account_id = stack_id.split(":")[4]
    aws_region = stack_id.split(":")[3]
    stack_name = stack_id.split(":")[5].split("/")[1]
    return {
        "CloudFormation stack": stack_name,
        "AWS account": aws_account_id,
        "AWS region": aws_region
    }



