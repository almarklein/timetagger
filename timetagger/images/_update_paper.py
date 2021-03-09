"""
Script to generate a pattern from an image.
"""

import numpy as np
import imageio

# Parameters
ori = 10, 10
size1 = 1200
padding = 50
size2 = size1 + 1 * padding
clim = 220, 255

# Take a square sample
im = imageio.imread("paper0.jpg")
rgba = np.zeros((size2, size2, 4)).astype(np.float32)
rgba[:, :, :3] = im[ori[0] : ori[0] + size2, ori[1] : ori[1] + size2][:, :, :3]
assert rgba.shape == (size2, size2, 4)

# apply clim
rgb = rgba[:, :, :3]
rgb[rgb < clim[0]] = clim[0]
rgb[rgb > clim[1]] = clim[1]


def generate(fname, opacity, base_clr):

    square = rgba.copy()

    # Apply linear degrading opacity at the edges
    for x in range(size2):
        for y in range(size2):
            fx = 1
            if x < padding:
                fx = x / padding
            elif x > size2 - padding:
                fx = (size2 - x) / padding
            fy = 1
            if y < padding:
                fy = y / padding
            elif y > size2 - padding:
                fy = (size2 - y) / padding
            square[y, x, 3] = opacity * fx * fy

    # Cut out quadrants
    #  q1 q2
    #  q4 q3
    h1 = size2 // 2
    h2 = size2 // 2
    q1 = square[:h2, :h2]
    q2 = square[h1:, :h2]
    q3 = square[h1:, h1:]
    q4 = square[:h2, h1:]

    # Prepare result
    result = np.zeros((size1, size1, 4)).astype(np.float32)
    result[:, :, :3] = base_clr * (1 - opacity)
    result[:, :, 3] = 1 - opacity

    # Blend quadrants in their oposite position
    h3 = size1 // 2 - padding // 2
    h4 = size1 // 2 + padding // 2
    blend(result, q1, slice(h3, size1), slice(h3, size1))
    blend(result, q2, slice(h3, size1), slice(0, h4))
    blend(result, q3, slice(0, h4), slice(0, h4))
    blend(result, q4, slice(0, h4), slice(h3, size1))

    # Write result
    assert result[:, :, 3].min() > 0.99 and result[:, :, 3].max() <= 1.001
    result[result < 0] = 0
    result[result > 255] = 255
    imageio.imwrite(fname, result.astype(np.uint8)[:, :, :3])

    # Show avg value
    rgb = [result[:, :, i].mean() for i in range(3)]
    print(f"mean rgb({rgb[0]:0.1f}, {rgb[1]:0.1f}, {rgb[2]:0.1f})")


def blend(result, q, xslice, yslice):
    for i in range(3):
        result[yslice, xslice, i] += q[:, :, i] * q[:, :, 3]
    result[yslice, xslice, 3] += q[:, :, 3]


# -- paper 1 -> #E6E7E5 -> rgb(230, 231, 229)
generate("paper1.jpg", 0.5, 220)

# -- paper 2 -> #F4F4F4 -> rgb(244, 244, 244)
# generate("paper4.jpg", 0.6, 255)
generate("paper2.jpg", 0.5, 250)


generate("paper3.jpg", 0.2, 0)
