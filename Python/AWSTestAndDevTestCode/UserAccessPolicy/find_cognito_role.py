import boto3

def find_cognito_roles():
    cognito = boto3.client('cognito-identity')
    
    # List identity pools
    pools = cognito.list_identity_pools(MaxResults=10)
    
    for pool in pools['IdentityPools']:
        pool_id = pool['IdentityPoolId']
        pool_name = pool['IdentityPoolName']
        
        # Get roles for this pool
        roles = cognito.get_identity_pool_roles(IdentityPoolId=pool_id)
        
        print(f"Identity Pool: {pool_name} ({pool_id})")
        if 'Roles' in roles:
            if 'authenticated' in roles['Roles']:
                print(f"  Authenticated Role: {roles['Roles']['authenticated']}")
            if 'unauthenticated' in roles['Roles']:
                print(f"  Unauthenticated Role: {roles['Roles']['unauthenticated']}")
        print()

if __name__ == "__main__":
    find_cognito_roles()