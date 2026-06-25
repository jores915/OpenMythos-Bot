import boto3
import json
import logging
from botocore.exceptions import ClientError

class BedrockClient:
    def __init__(self, region="us-east-1"):
        self.region = region
        self.client = None
        if region and region.strip():
            try:
                self.client = boto3.client("bedrock-runtime", region_name=region)
                logging.info(f"Bedrock client initialized for region {region}")
            except Exception as e:
                logging.error(f"Failed to initialize Bedrock client: {e}")
                self.client = None
        else:
            logging.info("Bedrock client disabled (no region provided)")

    def invoke_model(self, model_id, prompt, max_tokens=1000, temperature=0.7):
        if self.client is None:
            logging.warning("Bedrock client not available, returning dummy response")
            return {"content": "Bedrock disabled - dummy response"}
        try:
            body = json.dumps({
                "prompt": prompt,
                "max_tokens_to_sample": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
            })
            response = self.client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=body
            )
            response_body = json.loads(response["body"].read())
            return response_body
        except ClientError as e:
            logging.error(f"Bedrock invoke error: {e}")
            return {"error": str(e)}
