def find_multiples_of_13():
    results = []
    num = 104  # Start from the smallest 4-digit number
    while num < 10**4:  # Limit to 7 digits; adjust as needed
        if num % 13 == 0 and str(num)[0] in ('456') and str(num)[1] in ('3456789') and '0' not in str(num) and str(num).endswith('3'):
            results.append(num)
        num += 13
    return results

# Run the function and print results
multiples = find_multiples_of_13()
print(multiples)
