def hex_to_rgb(hex_color):
    # Remove the '#' character and convert the string to an integer using base 16
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))


def rgb_to_hex(rgb_color):
    # Convert the RGB components back to a hexadecimal string
    return '#' + ''.join(f'{c:02x}' for c in rgb_color)


def average_hex_colors(hex_colors):
    # Initialize sums for each RGB component
    sum_rgb = [0, 0, 0]

    # Convert each hex color to its RGB components and add them to the sums
    for hex_color in hex_colors:
        rgb = hex_to_rgb(hex_color)
        sum_rgb = [sum_c + rgb_c for sum_c, rgb_c in zip(sum_rgb, rgb)]

    # Calculate the average of each RGB component
    num_colors = len(hex_colors)
    avg_rgb = tuple(sum_c // num_colors for sum_c in sum_rgb)

    # Convert the average RGB back to a hex color
    return rgb_to_hex(avg_rgb)