"""
Posts a caption + link to X using a previously saved, authenticated session
(see login_and_save_session.py). Designed to run headless inside CI.

Required env vars:
    POST_CAPTION          - the caption text (optional, can be empty)
    POST_LINK             - the URL to post (required)
    X_STORAGE_STATE_PATH  - path to the storage_state JSON file
                            (default: x_storage_state.json)
"""

import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

CAPTION = os.environ.get("POST_CAPTION", "").strip()
LINK = os.environ.get("POST_LINK", "").strip()
STORAGE_STATE_PATH = os.environ.get("X_STORAGE_STATE_PATH", "x_storage_state.json")

if not LINK:
    sys.exit("POST_LINK env var is required")


def post_tweet() -> None:
    full_text = f"{CAPTION}\n{LINK}" if CAPTION else LINK

    with sync_playwright() as p:
        # Mobile-style viewport/UA/touch emulation, not a literal native browser
        device = p.devices["iPhone 13"]

        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state=STORAGE_STATE_PATH,
            **device,
        )
        page = context.new_page()

        page.goto("https://x.com/compose/post", wait_until="domcontentloaded")

        # If the session is stale/expired, X bounces to /login or /i/flow/login
        if "login" in page.url:
            browser.close()
            sys.exit(
                "Session looks expired (redirected to login). "
                "Re-run login_and_save_session.py locally and refresh the "
                "X_STORAGE_STATE_B64 secret."
            )

        textbox = page.get_by_test_id("tweetTextarea_0")
        textbox.wait_for(state="visible", timeout=15000)
        textbox.click()
        textbox.fill(full_text)

        # Give X a moment to render the link preview card before posting
        try:
            page.wait_for_selector('[data-testid="card.wrapper"]', timeout=12000)
        except PWTimeout:
            print("Warning: link preview card didn't render in time, posting anyway.")

        post_button = page.get_by_test_id("tweetButton")
        post_button.wait_for(state="visible", timeout=10000)
        post_button.click()

        # Wait for the composer to clear, which signals a successful post
        page.wait_for_timeout(4000)
        browser.close()

    print("Post submitted.")


if __name__ == "__main__":
    post_tweet()
