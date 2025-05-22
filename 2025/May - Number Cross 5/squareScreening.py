def is_valid(num):
    return all(d in '23456' for d in str(num))

def generate_valid_squares():
    result = []
    n = 1
    while True:
        square = n * n
        if square > 999999999:  # 9 digits max
            break
        if is_valid(square):
            result.append(square)
        n += 1
    return result

# Run the function and print the results
valid_squares = generate_valid_squares()
print(valid_squares)
