#!/usr/bin/env python3
"""
Remove 'Auth: Authorizer: NONE' blocks from OPTIONS endpoints in template.yml.
OPTIONS endpoints should have no Auth block to be public by default.
"""

import re

def fix_options_auth(template_path):
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Pattern to match OPTIONS endpoints with Auth: Authorizer: NONE
    # This matches:
    #   Method: OPTIONS
    #   Auth:
    #     Authorizer: NONE
    pattern = r'(\s+Method: OPTIONS\n)(\s+Auth:\n\s+Authorizer: NONE\n)'
    
    # Replace with just the Method: OPTIONS line (remove Auth block)
    fixed_content = re.sub(pattern, r'\1', content)
    
    # Count how many replacements were made
    matches = len(re.findall(pattern, content))
    
    with open(template_path, 'w') as f:
        f.write(fixed_content)
    
    return matches

if __name__ == '__main__':
    template_path = 'template.yml'
    count = fix_options_auth(template_path)
    print(f"Fixed {count} OPTIONS endpoints by removing Auth: Authorizer: NONE blocks")
