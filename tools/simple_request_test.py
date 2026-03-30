"""
SCHEMA: A tool that opens http://0.0.0.0:65535 using urllib.request.urlopen and waits for 5 seconds.
"""

import time
import urllib.request

def open_url():
    try:
        response = urllib.request.urlopen('http://0.0.0.0:65535')
        print(response.read().decode('utf-8'))
        time.sleep(5)
    except Exception as e:
        print(f'Error occurred: {e}')

if __name__ == '__main__':
    open_url()
