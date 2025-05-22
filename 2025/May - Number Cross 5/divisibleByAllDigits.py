def divisible_by_all_digits(n):
    digits = [int(d) for d in str(n)]
    if 0 in digits:
        return False
    return all(n % d == 0 for d in digits)

results = [n for n in range(100, 10000) if divisible_by_all_digits(n) and str(n).startswith('78')]
print(results)
