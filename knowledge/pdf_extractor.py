import fitz
import json
import re
from pathlib import Path


def extract_card_index_with_pages(pdf_path: Path) -> dict[str, dict]:
    """
    Extract card index + image page mapping using fitz.
    Fitz reads each cell on a separate line:
      line 0: card_id
      line 1: card_name
      line 2: expansion
      line 3: collection_no
      line 4: 'View Image'
    Links are ordered top-to-bottom matching card rows exactly.
    """
    doc = fitz.open(str(pdf_path))
    card_index = {}

    print(f"[pdf_extractor] PDF has {len(doc)} pages")
    print(f"[pdf_extractor] Extracting card index + image page mapping...")

    for page_num in range(len(doc)):
        page  = doc[page_num]
        text  = page.get_text()
        links = page.get_links()

        # only process index pages (contain 'View Image')
        if "View Image" not in text:
            continue

        # parse lines into card records (groups of 5 lines)
        lines = [l.strip() for l in text.split("\n")
                 if l.strip() and l.strip() != "Link"]

        # skip header row
        if lines and lines[0] == "Card ID":
            lines = lines[5:]  # skip: Card ID, Card Name, Expansion, Collection No., Link

        # group into chunks of 5: [id, name, expansion, collection_no, "View Image"]
        records = []
        i = 0
        while i + 4 < len(lines):
            card_id_raw  = lines[i]
            name         = lines[i+1]
            expansion    = lines[i+2]
            col_no       = lines[i+3]
            view_img     = lines[i+4]

            # validate: card_id is numeric, view_img is "View Image"
            if re.match(r"^\d+$", card_id_raw) and "View" in view_img:
                records.append({
                    "card_id":       card_id_raw,
                    "name":          name,
                    "expansion":     expansion,
                    "collection_no": col_no,
                })
                i += 5
            else:
                i += 1  # re-sync if misaligned

        # sort links top→bottom to match record order
        sorted_links = sorted(links, key=lambda l: l["from"].y0)

        # zip records with links
        for idx, record in enumerate(records):
            image_page = None
            if idx < len(sorted_links):
                image_page = sorted_links[idx].get("page")

            card_index[record["card_id"]] = {
                **record,
                "image_page": image_page,
            }

    doc.close()
    print(f"[pdf_extractor] Mapped {len(card_index)} cards to image pages")
    return card_index


def extract_card_images(pdf_path: Path,
                        card_index: dict,
                        output_dir: Path,
                        card_ids: list = None) -> dict[str, str]:
    """
    Extract card images from their dedicated PDF pages.
    Returns {card_id: image_path}
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    doc    = fitz.open(str(pdf_path))
    targets = card_ids if card_ids else list(card_index.keys())

    image_paths = {}
    saved = 0
    failed = 0

    print(f"[pdf_extractor] Extracting {len(targets)} card images...")

    for card_id in targets:
        info = card_index.get(card_id)
        if not info or info.get("image_page") is None:
            failed += 1
            continue

        try:
            page   = doc[info["image_page"]]
            images = page.get_images(full=True)

            if images:
                xref     = images[0][0]
                base     = doc.extract_image(xref)
                ext      = base["ext"]
                filename = f"card_{int(card_id):04d}.{ext}"
                out_path = output_dir / filename
                with open(out_path, "wb") as f:
                    f.write(base["image"])
            else:
                # fallback: render page
                pix      = page.get_pixmap(dpi=150)
                filename = f"card_{int(card_id):04d}.png"
                out_path = output_dir / filename
                pix.save(str(out_path))

            image_paths[card_id] = str(out_path)
            saved += 1

            if saved % 100 == 0:
                print(f"  ... saved {saved}/{len(targets)} images")

        except Exception as e:
            failed += 1

    doc.close()
    print(f"[pdf_extractor] Done — saved:{saved}  failed:{failed}")
    return image_paths


def save_index(card_index: dict, image_paths: dict, output_path: Path):
    for card_id, path in image_paths.items():
        if card_id in card_index:
            card_index[card_id]["image_path"] = path

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(card_index, f, ensure_ascii=False, indent=2)

    with_img = sum(1 for c in card_index.values() if "image_path" in c)
    print(f"[pdf_extractor] Saved {len(card_index)} cards "
          f"({with_img} with images) → {output_path}")


def summary(card_index: dict):
    mapped  = sum(1 for c in card_index.values()
                  if c.get("image_page") is not None)
    with_img = sum(1 for c in card_index.values()
                   if c.get("image_path"))
    expansions = {}
    for c in card_index.values():
        exp = c.get("expansion", "?")
        expansions[exp] = expansions.get(exp, 0) + 1

    print(f"\n── PDF index summary ───────────────────────")
    print(f"  Total cards     : {len(card_index)}")
    print(f"  Image page map  : {mapped}")
    print(f"  Images saved    : {with_img}")
    print(f"  Expansions      : {len(expansions)}")
    print(f"\n── Top expansions ──────────────────────────")
    for exp, count in sorted(expansions.items(), key=lambda x: -x[1])[:10]:
        print(f"  {exp:10} : {count}")
    print(f"────────────────────────────────────────────\n")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import PDF_EN, IMAGES_DIR, KNOW_DIR

    # Step 1 — extract index + page mapping
    card_index = extract_card_index_with_pages(PDF_EN)

    # Step 2 — test: extract first 5 images only
    print("\nTest — extracting first 5 card images...")
    test_ids    = list(card_index.keys())[:5]
    image_paths = extract_card_images(
        pdf_path   = PDF_EN,
        card_index = card_index,
        output_dir = IMAGES_DIR,
        card_ids   = test_ids,
    )

    # Step 3 — summary
    summary(card_index)

    # Step 4 — show samples
    print("── Sample entries ──────────────────────────")
    for card_id, data in list(card_index.items())[:5]:
        print(f"  {card_id:6} | {data['name']:25} | "
              f"page:{str(data.get('image_page','?')):5} | "
              f"{data.get('image_path', 'not extracted')}")
    print("────────────────────────────────────────────")

    # Step 5 — save
    out = KNOW_DIR / "pdf_card_index.json"
    save_index(card_index, image_paths, out)

    print("\nTo extract ALL images:")
    print("  change card_ids=test_ids → card_ids=None")