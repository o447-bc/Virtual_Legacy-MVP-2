import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DynamoDB configuration
TABLE_NAME = 'allQuestionDB'
REGION = 'us-east-1'

def get_dynamodb_resource():
    """
    Initialize and return a DynamoDB resource connection for the specified AWS region.
    
    This function creates a boto3 DynamoDB resource object that can be used to interact with DynamoDB tables.
    It requires valid AWS credentials to be configured (via AWS CLI, environment variables, or IAM roles).
    The function will raise an exception if credentials are missing or if there's an error connecting to AWS.
    
    Args:
        None
        
    Returns:
        boto3.resources.base.ServiceResource: DynamoDB resource object for table operations
        
    Raises:
        NoCredentialsError: When AWS credentials are not found or configured
        Exception: For any other AWS connection or configuration errors
    """
    try:
        dynamodb = boto3.resource('dynamodb', region_name=REGION)
        return dynamodb
    except NoCredentialsError:
        logger.error("AWS credentials not found. Please configure your credentials.")
        raise
    except Exception as e:
        logger.error(f"Error initializing DynamoDB resource: {str(e)}")
        raise

def getUniqueQuestionTypes():
    """
    Scan the allQuestionDB DynamoDB table to extract all unique question types and retrieve their friendly names.
    
    This function performs a full table scan to collect all unique questionType values, sorts them alphabetically,
    and then looks up the friendly name for each type by querying items with questionId format '{questionType}-00000'.
    It handles DynamoDB pagination automatically to ensure all data is processed regardless of table size.
    Requires AWS credentials and DynamoDB read permissions for the allQuestionDB table.
    
    Args:
        None
        
    Returns:
        dict: Dictionary containing:
            - 'questionTypes' (list[str]): Alphabetically sorted list of unique question type strings
            - 'friendlyNames' (dict[str, str]): Mapping of question type to its friendly name from 'Question' field
            
    Raises:
        Exception: For DynamoDB access errors, credential issues, or table access problems
    """
    try:
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(TABLE_NAME)
        
        # Scan table to get all items
        logger.info(f"Scanning table {TABLE_NAME} for unique question types...")
        
        unique_types = set()
        response = table.scan()
        
        # Process initial batch
        for item in response['Items']:
            if 'questionType' in item:
                unique_types.add(item['questionType'])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            for item in response['Items']:
                if 'questionType' in item:
                    unique_types.add(item['questionType'])
        
        # Sort question types alphabetically
        sorted_types = sorted(list(unique_types))
        logger.info(f"Found {len(sorted_types)} unique question types")
        
        # Get friendly names for each question type
        friendly_names = {}
        for question_type in sorted_types:
            try:
                friendly_name = get_friendly_name(table, question_type)
                friendly_names[question_type] = friendly_name
            except Exception as e:
                logger.warning(f"Could not get friendly name for {question_type}: {str(e)}")
                friendly_names[question_type] = f"Unknown ({question_type})"
        
        return {
            'questionTypes': sorted_types,
            'friendlyNames': friendly_names
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"DynamoDB ClientError [{error_code}]: {error_message}")
        raise Exception(f"DynamoDB error: {error_message}")
    except Exception as e:
        logger.error(f"Unexpected error in getUniqueQuestionTypes: {str(e)}")
        raise

def get_friendly_name(table, question_type):
    """
    Retrieve the friendly display name for a specific question type from the DynamoDB table.
    
    This function looks up a specific item in the DynamoDB table using a composite key where questionId
    follows the pattern '{questionType}-00000' and questionType matches the input parameter. It extracts
    the human-readable name from the 'Question' field of that item. If the item or field is not found,
    it returns a descriptive fallback string. This function is used internally by getUniqueQuestionTypes.
    
    Args:
        table (boto3.resources.base.ServiceResource): DynamoDB table resource object
        question_type (str): The question type identifier to look up
        
    Returns:
        str: The friendly name from the 'Question' field, or a fallback message if not found
        
    Raises:
        ClientError: For DynamoDB-specific errors during item retrieval
        Exception: For any other unexpected errors during the lookup process
    """
    try:
        question_id = f"{question_type}-00000"
        
        response = table.get_item(
            Key={
                'questionId': question_id,
                'questionType': question_type
            }
        )
        
        if 'Item' in response:
            item = response['Item']
            if 'Question' in item:
                return item['Question']
            else:
                logger.warning(f"No 'Question' field found for {question_id}")
                return f"No friendly name ({question_type})"
        else:
            logger.warning(f"No item found with questionId: {question_id}")
            return f"Not found ({question_type})"
            
    except ClientError as e:
        logger.error(f"Error getting friendly name for {question_type}: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting friendly name for {question_type}: {str(e)}")
        raise