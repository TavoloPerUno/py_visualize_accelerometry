#!/usr/bin/env bash
# Create GitHub Releases for existing tags using release notes from CHANGELOG.md.
#
# Prerequisites: gh CLI authenticated (run `gh auth login` first)
#
# Usage:
#     bash scripts/create_releases.sh

set -euo pipefail

REPO="TavoloPerUno/py_visualize_accelerometry"

extract_notes() {
    local version="$1"
    awk -v ver="$version" '
        /^## \[/ {
            if (found) exit
            if (index($0, "[" ver "]")) { found=1; next }
        }
        found { print }
    ' CHANGELOG.md
}

for TAG in v0.1.0 v1.0.0 v1.1.0; do
    VERSION="${TAG#v}"
    echo "--- Creating release for $TAG ---"

    NOTES=$(extract_notes "$VERSION")

    if [ -z "$NOTES" ]; then
        echo "  No notes found in CHANGELOG.md for $VERSION, using auto-generated notes"
        gh release create "$TAG" --repo "$REPO" --title "$TAG" --generate-notes 2>/dev/null || \
            echo "  Release for $TAG already exists, skipping"
    else
        echo "$NOTES" > /tmp/release-notes-"$VERSION".md
        gh release create "$TAG" --repo "$REPO" --title "$TAG" \
            --notes-file /tmp/release-notes-"$VERSION".md 2>/dev/null || \
            echo "  Release for $TAG already exists, skipping"
    fi
done

echo "Done."
