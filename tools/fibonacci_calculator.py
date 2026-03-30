"""
SCHEMA: A tool to calculate the 15th number in the Fibonacci sequence.
"""

def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

if __name__ == '__main__':
    result = fibonacci(15)
    if result != 610:
        print('Error: Calculated Fibonacci number is not equal to 610')
        exit(1)
    else:
        print('pass')
        exit(0)