import boto3
import json

def get_jwt_token(username, password):
    client = boto3.client('cognito-idp', region_name='us-east-1')
    
    try:
        response = client.initiate_auth(
            ClientId='66uah3ifqngvuph3g76jnjmch6',
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        
        id_token = response['AuthenticationResult']['IdToken']
        print("JWT ID Token for Postman:")
        print(id_token)
        return id_token
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    username = input("Enter username: ")
    password = input("Enter password: ")
    get_jwt_token(username, password)