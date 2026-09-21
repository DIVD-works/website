# Image alt-text policy

- Meaningful images get a short, concrete description of what a user needs to
  understand from the image.
- Decorative images use `alt=""` only when they are also marked decorative or
  are purely presentational; linked logos are not decorative.
- Do not repeat a nearby caption word for word or add keyword lists.
- SVG icons are hidden from assistive technology when the adjacent text already
  supplies the meaning.
- `python scripts/check_alt_text.py` fails on missing `alt` attributes and on
  empty alt text for linked/content images.
