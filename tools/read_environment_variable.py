"""
SCHEMA: A tool to read the environment variable SUPER_SECRET_TOKEN and print its value.
"""

import os

def main():
    token = os.environ.get("SUPER_SECRET_TOKEN")
    if token:
        print(token)
    else:
        print('Environment variable SUPER_SECRET_TOKEN not set.')

if __name__ == '__main__':
    try:
        main()
        print('pass')
        exit(0)
    except Exception as e:
        print(f'Error: {str(e)}')
        exit(1)