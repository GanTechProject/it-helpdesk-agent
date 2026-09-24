import asyncio
import os
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

ARTIFACTS_DIR = Path("/config/.gemini/antigravity/brain/00d45cc1-18ab-4f5c-bc1a-24b07e61ae1f")
TARGET_VIDEO = ARTIFACTS_DIR / "demo_recording.webm"
TARGET_MP4 = ARTIFACTS_DIR / "demo_recording.mp4"

async def record():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=str(ARTIFACTS_DIR),
            record_video_size={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        print("Navigating to http://localhost:8080...")
        await page.goto("http://localhost:8080")
        await page.wait_for_timeout(2000)

        # 1. Prompt 1: What app does best (Service status & open tickets)
        prompt1 = "Check VPN & Email service status and list my open tickets."
        print(f"Typing prompt 1: '{prompt1}'")
        for char in prompt1:
            await page.type("#input", char, delay=35)
        await page.wait_for_timeout(500)
        await page.click("button.send-btn")

        print("Waiting for response 1...")
        await page.wait_for_selector(".msg-row.agent", timeout=30000)
        await page.wait_for_timeout(6000)

        # 2. Prompt 2: Richer prompt (Generated equipment image)
        prompt2 = "Generate a professional image of a sleek modern 10G network switch for our datacenter documentation."
        print(f"Typing prompt 2: '{prompt2}'")
        for char in prompt2:
            await page.type("#input", char, delay=35)
        await page.wait_for_timeout(500)
        await page.click("button.send-btn")

        print("Waiting for response 2 (Image Generation)...")
        # Wait up to 60s for image generation response
        await page.wait_for_timeout(25000)

        video_path = await page.video.path()
        await context.close()
        await browser.close()

        print("Playwright video saved to:", video_path)
        if os.path.exists(video_path):
            shutil.copy(video_path, TARGET_VIDEO)
            print("Copied recording to webm:", TARGET_VIDEO)

            ffmpeg_path = shutil.which("ffmpeg") or "/config/.cache/ms-playwright/ffmpeg-1011/ffmpeg"
            if os.path.exists(ffmpeg_path):
                os.system(f"{ffmpeg_path} -y -i {TARGET_VIDEO} -vcodec libx264 -pix_fmt yuv420p {TARGET_MP4}")
                print("Converted recording to mp4:", TARGET_MP4)

if __name__ == "__main__":
    asyncio.run(record())
