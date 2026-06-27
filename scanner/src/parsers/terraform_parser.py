import hcl2
import json
import io
import logging

logger = logging.getLogger(__name__)


def parse(content: bytes) -> dict:
    """
    Parse Terraform HCL content and return a nested dict structure.

    Args:
        content: Raw bytes of a .tf or .hcl file

    Returns:
        dict: {resource_type: {resource_name: attrs_dict}}
        Example: {"aws_s3_bucket": {"my_bucket": {"acl": ["public-read"]}}}
        Returns {} on parse error (logged via logger.error)
    """
    try:
        text_stream = io.StringIO(content.decode('utf-8'))
        parsed = hcl2.load(text_stream)

        if not parsed or 'resource' not in parsed:
            return {}

        resource_section = parsed['resource']
        if not isinstance(resource_section, list):
            return {}

        result = {}
        for resource_block in resource_section:
            if isinstance(resource_block, dict):
                for resource_type, resources in resource_block.items():
                    if resource_type not in result:
                        result[resource_type] = {}
                    if isinstance(resources, dict):
                        result[resource_type].update(resources)

        return result

    except UnicodeDecodeError as e:
        logger.error(json.dumps({
            "error": "terraform_parser_decode_error",
            "message": str(e),
        }))
        return {}
    except Exception as e:
        logger.error(json.dumps({
            "error": "terraform_parser_error",
            "message": str(e),
            "type": type(e).__name__,
        }))
        return {}
