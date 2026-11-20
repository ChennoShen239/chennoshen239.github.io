"""Build the static gallery with python3 photos.py. Entries appear in list order."""

from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote

from PIL import Image
from PIL.ExifTags import IFD, Base


@dataclass
class Photo:
    name: str  # assets/photos/<name>.jpg
    alt: str
    description: str = ""


PHOTOS = [
    Photo(
        "sunset",
        description="Afterglow in Xiamen.",
        alt="Orange light breaks through clouds above distant mountains and reflects on the water.",
    ),  # DSC_5280
    Photo(
        "window",
        description="Berkeley, as seen from the window.",
        alt="Sunlit foliage and a parked car seen through a dark window frame.",
    ),  # DSC_4465
    Photo(
        "dsc-1661",
        description="Heaven Lake, Changbai Mountain.",
        alt="Snow covers the slopes below a dark mountain ridge under a clear blue sky.",
    ),
    Photo(
        "dsc-3034",
        description="Huludao, a Liaoning coastline, during the blue hour.",
        alt="A striped beacon rises from a stone breakwater across calm blue water.",
    ),
    Photo(
        "dsc-3590",
        description="My favorite, Routine Coffee, Anyang, my hometown.",
        alt="Warm lights illuminate coffee grinders and miniature houses behind a window.",
    ),
    Photo(
        "dsc-3847",
        description="Viewing San Francisco from Union Square.",
        alt="A red-and-white bus crosses a steep street lined with tall buildings.",
    ),
    Photo(
        "dsc-4245",
        description="La La Land, from Griffith Observatory.",
        alt="A cluster of towers rises above a city stretching to the horizon beneath a pink sky.",
    ),
    Photo(
        "dsc-5037",
        description="Master of the Nets Garden, Suzhou.",
        alt="Clusters of white blossoms hang in front of dark wooden windows.",
    ),
    Photo(
        "dsc-5299",
        description="Hotel Corridor, Aranya.",
        alt="A narrow passage between dark walls opens onto a railing and the sea.",
    ),
    Photo(
        "dsc-5747",
        description="A winter that seems to hold some hope, Beijing.",
        alt="Bare treetops catch orange light against a clear blue sky.",
    ),
]

ROOT = Path(__file__).resolve().parent


def display_size(image):
    if image.getexif().get(Base.Orientation) in (5, 6, 7, 8):
        return image.height, image.width
    return image.size


def capture_date(value):
    try:
        day = date.fromisoformat(value[:10].replace(":", "-"))
    except ValueError:
        return "—"
    return f'<time datetime="{day.isoformat()}">{day.day} {day:%b %Y}</time>'


def render_photo(photos, index):
    photo = photos[index]
    path = ROOT / "assets" / "photos" / f"{photo.name}.jpg"
    with Image.open(path) as image:
        width, height = display_size(image)
        exif = image.getexif()
        shot = exif.get_ifd(IFD.Exif)
        taken = capture_date(shot.get(Base.DateTimeOriginal, ""))
        camera = exif.get(Base.Model, "—").replace("NIKON ", "Nikon ")
        lens = shot.get(Base.LensModel, "—")

    url = f"assets/photos/{quote(photo.name)}"
    source = f"{url}.jpg"
    responsive = ""
    small_path = path.with_name(f"{path.stem}-small.jpg")
    if small_path.is_file():
        with Image.open(small_path) as image:
            small_width, _ = display_size(image)
        source = f"{url}-small.jpg"
        # The photo box is at most 1008px wide and 768px tall.
        max_width = min(1008, round(768 * width / height))
        responsive = f'''
         srcset="{source} {small_width}w, {url}.jpg {width}w"
         sizes="(max-width: 640px) calc(100vw - 32px), min(100vw - 48px, {max_width}px)"'''

    number, total = index + 1, len(photos)
    previous = quote(photos[index - 1].name)
    following = quote(photos[(index + 1) % total].name)
    priority = 'fetchpriority="high"' if index == 0 else 'loading="lazy"'
    label = f"Photograph {number} of {total}"
    name = escape(photo.name)
    description = escape(photo.description or "Your description here.")
    return f'''  <figure class="slide" id="{name}" tabindex="-1" aria-label="{label}">
    <img class="projection" src="{source}"{responsive}
         width="{width}" height="{height}" {priority}
         alt="{escape(photo.alt)}">
    <figcaption>
      <p class="photo-description" id="{name}-description">{description}</p>
      <dl class="photo-data">
        <div><dt>Date</dt><dd>{taken}</dd></div>
        <div><dt>Camera</dt><dd>{escape(camera)}</dd></div>
        <div><dt>Lens</dt><dd>{escape(lens)}</dd></div>
      </dl>
      <nav class="photo-controls" aria-label="Photo navigation">
        <a href="#{previous}" rel="prev" aria-label="Previous photograph">Previous</a>
        <span aria-label="{label}">{number} / {total}</span>
        <a href="#{following}" rel="next" aria-label="Next photograph">Next</a>
      </nav>
    </figcaption>
  </figure>'''


def build():
    names = [photo.name for photo in PHOTOS]
    if len(names) != len(set(names)):
        raise ValueError("Each photo needs a unique name.")
    figures = "\n\n".join(render_photo(PHOTOS, i) for i in range(len(PHOTOS)))
    page = ROOT / "photos.html"
    html = page.read_text(encoding="utf-8")
    start_marker = "<!-- Photos generated by photos.py -->"
    start = html.index(start_marker) + len(start_marker)
    end = html.index("  <!-- End photos -->", start)
    updated = html[:start] + "\n" + figures + "\n" + html[end:]
    if updated != html:
        with TemporaryDirectory(dir=ROOT) as directory:
            draft = Path(directory) / page.name
            draft.write_text(updated, encoding="utf-8")
            draft.replace(page)


if __name__ == "__main__":
    build()
