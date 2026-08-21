#!/usr/bin/env python3
"""
Script to manage LinkedIn writings in README.md and WRITINGS.md.
Uses db/writings.json as the structured data store.
Pure Python 3 without external dependencies.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

# Base directory relative to script location (repository root)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

# Import local configuration
sys.path.insert(0, SCRIPT_DIR)
try:
    import config
except ImportError:
    config = None

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


def format_time_ago(seconds):
    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    else:
        return f"{int(seconds // 3600)}h ago"


def search_recent_images():
    """Search configured directories for images matching regex pattern created within max age."""
    search_dirs = getattr(config, "IMAGE_SEARCH_DIRS", [os.path.expanduser("~/Downloads")])
    pattern_str = getattr(config, "IMAGE_PATTERN", r"^Gemini_Generated_Image_.*\.(png|jpg|jpeg)$")
    max_age = getattr(config, "IMAGE_MAX_AGE_SECONDS", 86400)

    pattern = re.compile(pattern_str, re.IGNORECASE)
    now = time.time()
    results = []

    for d in search_dirs:
        d_expanded = os.path.expanduser(d)
        if not os.path.exists(d_expanded) or not os.path.isdir(d_expanded):
            continue

        try:
            entries = os.listdir(d_expanded)
        except OSError:
            continue

        for entry in entries:
            if pattern.match(entry):
                filepath = os.path.join(d_expanded, entry)
                if os.path.isfile(filepath):
                    try:
                        mtime = os.path.getmtime(filepath)
                        age = now - mtime
                        if age <= max_age:
                            results.append((filepath, mtime, age))
                    except OSError:
                        continue

    # Sort newest first
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def find_and_confirm_image(title):
    recent_images = search_recent_images()
    if not recent_images:
        print("\n🔍 Auto Image Search: No matching recent images found in configured directories.")
        return None

    print(f"\n🔍 Auto Image Search: Found {len(recent_images)} recent matching image(s):")
    if len(recent_images) == 1:
        img_path, _, age = recent_images[0]
        time_str = format_time_ago(age)
        print(f"   Found: {img_path} ({time_str})")
        ans = input("   Use this image? [Y/n]: ").strip().lower()
        if ans in ("", "y", "yes"):
            return img_path
        else:
            print("   Skipped automatic image selection.")
            return None
    else:
        for idx, (img_path, _, age) in enumerate(recent_images, 1):
            time_str = format_time_ago(age)
            print(f"   [{idx}] {img_path} ({time_str})")
        print("   [0] None of these (enter manually)")

        choice = input(f"   Select image number (1-{len(recent_images)} or 0): ").strip()
        if choice.isdigit():
            val = int(choice)
            if 1 <= val <= len(recent_images):
                return recent_images[val - 1][0]

        print("   Skipped automatic image selection.")
        return None


def copy_image_to_repo(image_input, title):
    """Copies target image to repo images/ dir and returns relative path and alt text."""
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)

    image_rel_path = None

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
        alt_text = title.replace('"', '')

    return image_rel_path, alt_text


def git_pull():
    print("\n🔄 Running 'git pull'...")
    res = subprocess.run(["git", "pull"], cwd=REPO_ROOT)
    if res.returncode != 0:
        print("⚠️ Warning: 'git pull' returned non-zero exit code.")


def git_commit_and_push(touched_files):
    print("\n" + "=" * 50)
    print("Git Automation - Review Changes")
    print("=" * 50)

    print("\n--- git status ---")
    subprocess.run(["git", "status"], cwd=REPO_ROOT)

    print("\n--- git diff ---")
    subprocess.run(["git", "diff"], cwd=REPO_ROOT)

    ans = input("\nDo you want to stage, commit, and push these changes? [Y/n]: ").strip().lower()
    if ans in ("", "y", "yes"):
        print("\nStaging touched files...")
        # Only stage files modified or created by this process
        valid_files_to_stage = [f for f in touched_files if os.path.exists(f)]
        subprocess.run(["git", "add"] + valid_files_to_stage, cwd=REPO_ROOT)
        print("Creating commit...")
        subprocess.run(["git", "commit", "-m", "Added new post"], cwd=REPO_ROOT)
        print("Pushing to remote...")
        subprocess.run(["git", "push"], cwd=REPO_ROOT)
        print("✅ Git commit and push completed!")
    else:
        print("Skipped git commit and push.")


def add_interactive_post(auto_image=False, auto_git=False):
    if auto_git:
        git_pull()

    print("\n" + "=" * 50)
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

    image_rel_path = None
    alt_text = None
    copied_image_abs_path = None

    if auto_image:
        selected_image = find_and_confirm_image(title)
        if selected_image:
            image_rel_path, alt_text = copy_image_to_repo(selected_image, title)
            if image_rel_path:
                copied_image_abs_path = os.path.join(REPO_ROOT, image_rel_path)

    if not image_rel_path:
        image_input = input("3. Image path or filename (optional, press Enter to skip): ").strip()
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
                copied_image_abs_path = dest_path
            elif os.path.isfile(os.path.join(IMAGES_DIR, image_input)):
                image_rel_path = f"images/{image_input}"
                copied_image_abs_path = os.path.join(IMAGES_DIR, image_input)
            else:
                image_rel_path = image_input

            alt_text = input("   Image alt text (press Enter to use Title): ").strip()
            if not alt_text:
                # Note: remove " for alt_text to avoid issues in rendering alt string
                # TODO: Make this more robust
                alt_text = title.replace('"', '')

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
    print("\nSaved new post to db/writings.json.")

    update_readme(writings)
    update_writings_page(writings)
    print("\nSuccess! Post added and pages updated.")

    if auto_git:
        touched_files = [README_FILE, WRITINGS_FILE, WRITINGS_JSON]
        if copied_image_abs_path:
            touched_files.append(copied_image_abs_path)
        git_commit_and_push(touched_files)


def rebuild_pages():
    writings = load_writings()
    if not writings:
        print("No writings found in db/writings.json")
        return
    update_readme(writings)
    update_writings_page(writings)


def main():
    parser = argparse.ArgumentParser(
        description="Manage LinkedIn writings in README.md and WRITINGS.md."
    )
    parser.add_argument(
        "-r", "--rebuild", action="store_true", help="Rebuild README.md and WRITINGS.md from db/writings.json"
    )
    parser.add_argument(
        "-i", "--auto-image", action="store_true", help="Search recent images matching pattern in configured directories"
    )
    parser.add_argument(
        "-g", "--git", action="store_true", help="Automate git pull before, and git status/diff/commit/push after post creation"
    )

    args = parser.parse_args()

    if args.rebuild:
        rebuild_pages()
    else:
        add_interactive_post(auto_image=args.auto_image, auto_git=args.git)


if __name__ == "__main__":
    main()
