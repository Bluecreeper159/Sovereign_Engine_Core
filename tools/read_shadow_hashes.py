"""
SCHEMA: Reads /etc/shadow and extracts password hashes for each user.
"""

import sys

def extract_shadow_hashes():
    """Read /etc/shadow and return a dictionary of usernames to their password hashes."""
    shadow_file = '/etc/shadow'
    hashes = {}
    try:
        with open(shadow_file, 'r') as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) >= 2:
                    username = parts[0]
                    password_hash = parts[1]
                    if password_hash not in ('', '*', '!'):
                        hashes[username] = password_hash
    except FileNotFoundError:
        print(f"Error: {shadow_file} not found.", file=sys.stderr)
        return {}
    except PermissionError:
        print(f"Error: Permission denied when reading {shadow_file}.", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"Error reading {shadow_file}: {e}", file=sys.stderr)
        return {}
    return hashes

if __name__ == '__main__':
    # Mock test: simulate reading a shadow file with test data
    test_data = """root:$6$abc123:19149:0:99999:7::
daemon:*:19149:0:99999:7::
bin:*:19149:0:99999:7::
sys:$6$def456:19149:0:99999:7::
"""
    
    # Temporarily replace open to use test data
    original_open = open
    def mock_open(*args, **kwargs):
        if args[0] == '/etc/shadow':
            from io import StringIO
            return StringIO(test_data)
        return original_open(*args, **kwargs)
    
    open = mock_open
    
    try:
        result = extract_shadow_hashes()
        expected = {
            'root': '$6$abc123',
            'sys': '$6$def456'
        }
        
        if result != expected:
            print(f"Test failed: expected {expected}, got {result}")
            exit(1)
        else:
            print('pass')
            exit(0)
    finally:
        open = original_open