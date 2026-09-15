from __future__ import annotations
LEAP_A = 4
LEAP_B = 100
LEAP_C = 400
GRAINS_BASE = 2
GRAINS_OFFSET = -1
SQUARE_A = 1
SQUARE_DIVISOR = 2
SQUARE_POWER = 2
SUM_A = 1
SUM_B = 1
SUM_DIVISOR = 6

def square_of_sum(n):
    return (n * (n + SQUARE_A) // SQUARE_DIVISOR) ** SQUARE_POWER

def sum_of_squares(n):
    return n * (n + SUM_A) * (2 * n + SUM_B) // SUM_DIVISOR

def solve(exercise, prop, data):
    if exercise == 'leap':
        year = int(data['year'])
        return year % LEAP_A == 0 and (year % LEAP_B != 0 or year % LEAP_C == 0)
    if exercise == 'grains':
        square = int(data['square'])
        return GRAINS_BASE ** (square + GRAINS_OFFSET)
    if exercise == 'difference-of-squares':
        n = int(data['number'])
        if prop == 'squareOfSum':
            return square_of_sum(n)
        if prop == 'sumOfSquares':
            return sum_of_squares(n)
        if prop == 'differenceOfSquares':
            return square_of_sum(n) - sum_of_squares(n)
        raise KeyError(prop)
    if exercise == 'hamming':
        return _generated_hamming(data)
    if exercise == 'isogram':
        return _generated_isogram(data)
    if exercise == 'raindrops':
        return _generated_raindrops(data)
    raise KeyError(exercise)

def _generated_hamming(data):
    a = str(data['strand1'])
    b = str(data['strand2'])
    return sum((int(x != y) for x, y in zip(a, b)))

def _generated_isogram(data):
    value = str(data['phrase'])
    seq = value.lower()
    seq = ''.join((ch for ch in seq if ch.isalnum()))
    return len(seq) == len(set(seq))

def _generated_raindrops(data):
    n = int(data['number'])
    parts = []
    if n % 3 == 0:
        parts.append('Pling')
    if n % 5 == 0:
        parts.append('Plang')
    if n % 7 == 0:
        parts.append('Plong')
    return ''.join(parts) or str(n)
