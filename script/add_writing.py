#!/usr/bin/env python3
"""
Script to manage LinkedIn writings in README.md and WRITINGS.md.
Uses writings.json as the structured data store.
Pure Python 3 without external dependencies.
"""

import json
import os
import shutil
import sys

# Base directory relative to script location (repository root)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

WRITINGS_JSON = os.path.join(REPO_ROOT, "db", "writings.json")
README_FILE = os.path.join(REPO_ROOT, "README.md")
WRITINGS_FILE = os.path.join(REPO_ROOT, "WRITINGS.md")
IMAGES_DIR = os.path.join(REPO_ROOT, "images")
START_MARKER = "<!-- START_WRITINGS -->"
END_MARKER = "<!-- END_MARKER_WRITINGS -->"


def format_post_markdown(post):
    """Format a single post object into Markdown matching the template."""
    title = post.get("title", "").strip()
    image = post.get("image")
    alt = post.get("alt") or title
    link = post.get("link", "").strip()
    raw_text = post.get("text", "").strip()

    # Format text blockquote lines
    lines = raw_text.splitlines()
    quoted_lines = []
    for line in lines:
        if line.strip():
            quoted_lines.append(f">{line}")
        else:
            quoted_lines.append(">")

    text_block = "\n".join(quoted_lines)

    img_html = ""
    if image:
        img_html = f'<img src="{image}" align="right" width="250" alt="{alt}" />\n '

    md = f"**{title}**\n{img_html}\n{text_block}\n>\n> 🔗 [Read the full post on LinkedIn]({link})\n\n<br clear=\"right\" />"
    return md


def load_writings():
    if os.path.exists(WRITINGS_JSON):
        with open(WRITINGS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_writings(writings):
    db_dir = os.path.dirname(WRITINGS_JSON)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    with open(WRITINGS_JSON, "w", encoding="utf-8") as f:
        json.dump(writings, f, indent=2, ensure_ascii=False)


def render_posts_section(posts):
    formatted = [format_post_markdown(p) for p in posts]
    return "\n\n".join(formatted)


def update_readme(posts):
    if not os.path.exists(README_FILE):
        print(f"Warning: {README_FILE} not found.")
        return

    top_posts = posts[:3]
    posts_md = render_posts_section(top_posts)
    link_to_more = "\n\n👉 **[Read all writings on LinkedIn ➔](WRITINGS.md)**\n"

    with open(README_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    start_idx = content.find(START_MARKER)
    end_idx = content.find(END_MARKER)

    if start_idx != -1 and end_idx != -1:
        new_content = (
            content[: start_idx + len(START_MARKER)]
            + "\n\n"
            + posts_md
            + link_to_more
            + "\n"
            + content[end_idx:]
        )
    else:
        # If markers are missing, insert under ### 📝 Writings on LinkedIn
        heading = "### 📝 Writings on LinkedIn"
        if heading in content:
            parts = content.split(heading, 1)
            rest = parts[1]
            next_sep = rest.find("\n---")
            if next_sep != -1:
                after_section = rest[next_sep:]
            else:
                after_section = ""

            new_section = (
                f"{heading}\n\n{START_MARKER}\n\n{posts_md}{link_to_more}\n{END_MARKER}"
            )
            new_content = parts[0] + new_section + after_section
        else:
            print(f"Error: Could not find section markers or heading in {README_FILE}")
            return

    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Updated {README_FILE} with top 3 posts.")


def update_writings_page(posts):
    posts_md = render_posts_section(posts)

    header = """# 📝 All Writings on LinkedIn

[← Back to Main Page](README.md)

---

"""

    footer = """

---

[← Back to Main Page](README.md)
"""

    content = f"{header}{START_MARKER}\n\n{posts_md}\n\n{END_MARKER}{footer}"

    with open(WRITINGS_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated {WRITINGS_FILE} with all {len(posts)} posts.")


def get_multiline_input(prompt):
    print(prompt)
    print("(Type 'END' on a new line by itself when finished)")
    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        except EOFError:
            break
    return "\n".join(lines)


def add_interactive_post():
    print("=" * 50)
    print("Add New LinkedIn Writing")
    print("=" * 50)

    title = input("1. Title: ").strip()
    while not title:
        print("Title cannot be empty.")
        title = input("1. Title: ").strip()

    link = input("2. LinkedIn Link: ").strip()
    while not link:
        print("Link cannot be empty.")
        link = input("2. LinkedIn Link: ").strip()

    image_input = input("3. Image path or filename (optional, press Enter to skip): ").strip()
    image_rel_path = None
    alt_text = None

    if image_input:
        if not os.path.exists(IMAGES_DIR):
            os.makedirs(IMAGES_DIR)

        if os.path.isfile(image_input):
            filename = os.path.basename(image_input)
            dest_path = os.path.join(IMAGES_DIR, filename)
            if os.path.abspath(image_input) != os.path.abspath(dest_path):
                shutil.copy2(image_input, dest_path)
                print(f"   Copied image to {dest_path}")
            image_rel_path = f"images/{filename}"
        elif os.path.isfile(os.path.join(IMAGES_DIR, image_input)):
            image_rel_path = f"images/{image_input}"
        else:
            image_rel_path = image_input

        alt_text = input("   Image alt text (press Enter to use Title): ").strip()
        if not alt_text:
            # Note: remove " for alt_text to avoid issues in rendering alt string
            # TODO: Make this more robust
            alt_text = title.replace('"','')

    print("\n4. Post Text:")
    text = get_multiline_input("Paste or type the text of your LinkedIn post below:")

    new_post = {
        "title": title,
        "image": image_rel_path,
        "alt": alt_text,
        "link": link,
        "text": text,
    }

    writings = load_writings()
    writings.insert(0, new_post)  # Newest first
    save_writings(writings)
    print("\nSaved new post to writings.json.")

    update_readme(writings)
    update_writings_page(writings)
    print("\nSuccess! Post added and pages updated.")


def rebuild_pages():
    writings = load_writings()
    if not writings:
        print("No writings found in writings.json")
        return
    update_readme(writings)
    update_writings_page(writings)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--rebuild", "-r"):
        rebuild_pages()
    else:
        add_interactive_post()
