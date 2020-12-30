import os

colormap = {
    # hero image
    "#6c63ff": "#2399DA",  # clock edge
    "#535461": "#535461",  # clock arms
    "#85555c": "#85555c",  # woman brown hair
    "#ed677b": "#B48B1C",  # woman shirt
    "#5e52ad": "#136490",  # woman pants
    # other images
    "#575a89": "#2399DA",  # woman shirt
    "#ff748e": "#B48B1C",  # man's red shirt
    "#69f0ae": "#B48B1C",  # bright green
}

for fname1 in os.listdir():
    if not fname1.endswith(".svg"):
        continue
    if fname1.endswith("_tt.svg"):
        continue

    fname2 = fname1.replace(".svg", "_tt.svg")

    with open(fname1, "rb") as f:
        text = f.read().decode()

    # Collect colors
    colors = set()
    i = 0
    while i >= 0:
        i = text.find('"#', i + 1)
        if i > 0:
            clr = text[i + 1 : i + 8]
            colors.add(clr)
    # print(colors)

    # Modify
    print("changing", len(colors), "colors in", fname1)
    for old, new in colormap.items():
        text = text.replace(old, new)

    with open(fname2, "wb") as f:
        f.write(text.encode())
