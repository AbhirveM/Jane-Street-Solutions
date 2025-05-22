def find_multiples_of_32():
    results = []
    num = 128  # Start from the smallest 4-digit number
    while num < 10**5:  # Limit to 7 digits; adjust as needed
            if num % 32 == 0 and str(num)[0] in ('3456789') and '0' not in str(num) and str(num)[1] in ('3') and str(num)[2] in ('3456'):
                results.append(num)
            num += 32
    return results

# Run the function and print results
multiples = find_multiples_of_32()
print(multiples)
