# import imageio
import webruntime


sizes = 16, 32, 48, 64, 128, 256

icon = webruntime.util.icon.Icon()
for size in sizes:
    fname = f"timetagger{size}_sf.png"
    icon.read(fname)
    # imb = imageio.imread(fname)
    # imw = 255 - imb  # make white the inverse
    # imw[:, :, 3] = imb[:, :, 3]  # Transfer original alpha channel
    # imageio.imsave(f"timetagger{size}w.png", imw)

icon.write(f"timetagger_sf.ico")
icon.write(f"favicon.ico")

# %%

im1, shape = webruntime.util.png.read_png(open("timetagger192.png", "rb"))
im2, shape = webruntime.util.png.read_png(open("timetagger192w.png", "rb"))

# soften alpha
for i in range(3, len(im1), 4):
    im1[i] = int(im1[i] * 0.1 + 0.4999)
    im2[i] = int(im2[i] * 0.1 + 0.4999)

with open("timetagger192soft.png", "wb") as f:
    webruntime.util.png.write_png(im1, shape, f)
with open("timetagger192wsoft.png", "wb") as f:
    webruntime.util.png.write_png(im2, shape, f)
