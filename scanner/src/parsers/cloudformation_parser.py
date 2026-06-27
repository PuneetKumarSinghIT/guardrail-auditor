import json
import logging
from typing import Dict, Any

try:
    import cfn_flip
    HAS_CFN_FLIP = True
except ImportError:
    HAS_CFN_FLIP = False
    import yaml

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def parse(content: bytes) -> Dict[str, Dict[str, Any]]:
    """
    Parse CloudFormation YAML or JSON and extract resources.

    Args:
        content: raw bytes of CloudFormation template

    Returns:
        Nested dict: {ResourceType: {LogicalId: Properties}}
        Example: {"AWS::S3::Bucket": {"MyBucket": {"AccessControl": "PublicRead"}}}
    """
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError as e:
        logger.error(json.dumps({"error": "decode_failed", "details": str(e)}))
        return {}

    try:
        if HAS_CFN_FLIP:
            template, _ = cfn_flip.load(text)
        else:
            template = yaml.safe_load(text)
    except Exception as e:
        logger.error(json.dumps({"error": "parse_failed", "details": str(e)}))
        return {}

    if not isinstance(template, dict) or "Resources" not in template:
        logger.error(json.dumps({"error": "invalid_template", "details": "Resources key missing"}))
        return {}

    result = {}
    resources = template["Resources"]

    for logical_id, resource_def in resources.items():
        if not isinstance(resource_def, dict):
            continue

        resource_type = resource_def.get("Type")
        properties = resource_def.get("Properties", {})

        if resource_type:
            if resource_type not in result:
                result[resource_type] = {}
            result[resource_type][logical_id] = properties

    return result
