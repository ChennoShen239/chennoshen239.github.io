# chennoshen239.github.io

My academic homepage. Plain HTML served by GitHub Pages from `main`.

Preview locally with `python3 -m http.server 8000`.

## Photo gallery

Put `<name>.jpg` in `assets/photos/` and add `Photo("<name>", alt="…", description="")` to `PHOTOS` in `photos.py`. List order sets the slideshow order. An empty description displays the placeholder. A matching `<name>-small.jpg` supplies the smaller screen image when available.

Run `python3 photos.py` with Pillow installed to rebuild `photos.html`. The script reads the date, camera, and lens from each JPEG.
