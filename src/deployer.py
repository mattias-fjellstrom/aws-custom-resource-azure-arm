import json
import os
from azure.identity import ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import DeploymentMode, Deployment
import logging


logger = logging.getLogger(__name__)


class Deployer(object):
    def __init__(self, subscription_id, resource_group_name, location, template, deployment_name, parameters={}, tags={}):
        self.subscription_id = subscription_id
        self.resource_group_name = resource_group_name
        self.location = location
        self.template = self._load_arm_template_as_json(template)
        self.parameters = self._construct_deployment_parameters(parameters)
        self.deployment_name = deployment_name
        self.tags = tags
        self.outputs = {}

        self.credentials = ClientSecretCredential(
            client_id=os.environ.get("AZURE_CLIENT_ID"),
            client_secret=os.environ.get("AZURE_CLIENT_SECRET"),
            tenant_id=os.environ.get("AZURE_TENANT_ID")
        )

        self.client = ResourceManagementClient(
            self.credentials,
            self.subscription_id
        )

    @staticmethod
    def _load_arm_template_as_json(template):
        return json.loads(template)

    @staticmethod
    def _construct_deployment_parameters(parameters):
        return {k: {"value": v} for k, v in parameters.items()}

    def deploy(self):
        self.client.resource_groups.create_or_update(
            self.resource_group_name,
            {
                "location": self.location,
                "tags": [{"key": k, "value": v} for k, v in self.tags.items()]
            }
        )

        deployment_properties = {
            "mode": DeploymentMode.INCREMENTAL,
            "template": self.template,
            "parameters": self.parameters,
        }

        deployment_async_operation = self.client.deployments.begin_create_or_update(
            resource_group_name=self.resource_group_name,
            deployment_name=self.deployment_name,
            parameters=Deployment(properties=deployment_properties),
        )
        deployment_async_operation.wait()

        results = deployment_async_operation.result()
        self.outputs = {k: v["value"] for k, v in results.properties.outputs.items()}

    def destroy(self):
        rg_async_operation = self.client.resource_groups.begin_delete(self.resource_group_name)
        rg_async_operation.wait()
