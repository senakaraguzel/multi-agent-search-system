import asyncio
import random

async def solve_captcha(page, agent_name="anti-bot"):
    """
    Asynchronous function to bypass Cloudflare Turnstile or specific platform captchas (like Sahibinden).
    Does NOT belong in the core browser loop; should be called externally by Generic Browsing Agent if needed.
    """
    try:
        # 1. Cloudflare Turnstile Checkbox
        try:
            for _ in range(3):
                cf_iframe = page.frame_locator("iframe[src*='cloudflare'], iframe[title*='Widget']").locator(
                    ".ctp-checkbox-label, input[type='checkbox'], #challenge-stage").first
                
                if await cf_iframe.is_visible(timeout=3000):
                    print(f"[{agent_name}] Cloudflare Turnstile tespit edildi, tiklaniyor...")
                    box = await cf_iframe.bounding_box()
                    if box:
                        # Tıklamayı direkt koordinata yap ki bot algılanmasın
                        x = box["x"] + box["width"] / 2
                        y = box["y"] + box["height"] / 2
                        await page.mouse.move(x, y, steps=10)
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                        await page.mouse.click(x, y)
                    else:
                        await cf_iframe.click(force=True)
                        
                    await asyncio.sleep(random.uniform(3, 5))
                else:
                    break
        except Exception:
            pass

        # 2. Sahibinden Klasik "Basılı Tutun"
        try:
            button = page.locator("button:has-text('Basılı Tutun'), button:has-text('Press and Hold')").first
            if await button.is_visible(timeout=3000):
                print(f"[{agent_name}] CAPTCHA cozuluyor (Basili Tut)...")
                box = await button.bounding_box()
                if box:
                    x = box["x"] + box["width"] / 2
                    y = box["y"] + box["height"] / 2

                    await page.mouse.move(x, y)
                    await page.mouse.down()
                    await asyncio.sleep(random.uniform(4, 6))
                    await page.mouse.up()
                    print(f"[{agent_name}] CAPTCHA gecildi.")
        except Exception:
            pass

    except Exception as e:
        print(f"[{agent_name}] Anti-Bot hatasi: {e}")
