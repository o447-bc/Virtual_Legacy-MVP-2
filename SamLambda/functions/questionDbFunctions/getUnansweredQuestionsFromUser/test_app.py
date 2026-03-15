import json
import unittest
import app

class TestGetUnansweredQuestions(unittest.TestCase):
    def test_integration(self):
        """Integration test using real AWS DynamoDB tables."""
        # Test parameters
        thisQuestionType = "childhood"
        thisUserId = "849854f8-c011-70bd-4ce3-2ade792a904a"
        
        # Test direct function call
        print(f"\nTesting get_unanswered_questions with questionType={thisQuestionType}, userId={thisUserId}")
        result = app.get_unanswered_questions(thisQuestionType, thisUserId)
        print(f"Found {len(result)} unanswered questions: {result}")
        self.assertIsInstance(result, list)
        
        # Test Lambda handler
        print(f"\nTesting lambda_handler with questionType={thisQuestionType}, userId={thisUserId}")
        event = {
            'queryStringParameters': {
                'questionType': thisQuestionType,
                'userId': thisUserId
            }
        }
        response = app.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        print(f"Lambda response: {body}")
        
 

if __name__ == '__main__':
    unittest.main()