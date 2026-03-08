import asyncio
import re
from urllib.parse import urlparse

async def handle_sahibinden(page, agent_name, limit=20):
    """
    Sahibinden'deki listeleme (searchResultsItem) kartlarini doner.
    Varsayim: Sayfa onceden acilmis, bypass edilmis ve liste icerisinde bulunuyor.
    """
    print(f"[{agent_name}] Sahibinden.com ozel parser'i baslatildi.")
    results = []
    base_url = "https://www.sahibinden.com"
    
    try:
        # Ilan satir selectorleri
        found = False
        selectors = ["tr.searchResultsItem", ".searchResultsItem", "table.searchResultsTable tr", ".classified-list li"]
        for sel in selectors:
            try:
                await page.wait_for_selector(sel, timeout=10000)
                found = True
                break
            except:
                continue
                
        if not found:
            print(f"[{agent_name}] Sahibinden tablo listesi bulunamadi, fallback link toplanacak.")
            
        links = await page.locator("a.classifiedTitle").all()
        
        for l in links[:limit]:
            href = await l.get_attribute("href")
            try:
                title = await l.inner_text()
            except:
                title = "Ilan"
                
            if href:
                url = href if href.startswith("http") else (base_url.rstrip("/") + href)
                results.append({
                    "url": url,
                    "metadata": {
                        "source": "sahibinden",
                        "title": title.encode('ascii', 'ignore').decode('ascii')
                    }
                })
        print(f"[{agent_name}] Sahibinden'den {len(results)} ilan basariyla ayiklandi.")
    except Exception as e:
        print(f"[{agent_name}] Sahibinden extraction hatasi: {e}")
        
    return results

async def handle_reddit(page, agent_name, base_url, query="", limit=20):
    """
    Reddit platformuna ozel veri cikarici.
    Eger DDGS'den donen root link direkt bir baslik oradan girmisse liste aramaz, kendisi listedir.
    """
    print(f"[{agent_name}] Reddit ozel parser'i baslatildi.")
    results = []
    
    # Eger gelinen sayfa zaten bir baslik(comment) zemberegi ise (ornek: reddit.com/r/Anahaber/comments/...)
    # bu sitenin icinde baska basliklar ("a" taglari) aramak botu spamlattirir ve luzumsuzdur. Direkt o sayfanin kendisi hedeftir.
    if "/comments/" in base_url or "/t3_" in base_url:
        print(f"[{agent_name}] Reddit url'si bir detay sayfasi, dogrudan hedef alinarak isleniyor.")
        results.append({
            "url": base_url,
            "metadata": {
                "source": "reddit_direct",
                "title": await page.title() if hasattr(page, 'title') else "Reddit Thread"
            }
        })
        return results

    # Eger subreddit ana sayfasina veya Arama sonuclarina dusulmulse Shadow DOM postlarini (shreddit-post veya a taglari) bul
    try:
        links = await page.locator("a[slot='full-post-link'], a[data-testid='post-title'], shreddit-post a").all()
        if not links:
            # Fallback for old reddit or different UI
            links = await page.locator("a").all()
            
        seen = set()
        for l in links:
            if len(results) >= limit: break
            try:
                href = await l.get_attribute("href")
                if not href or href.startswith("javascript"): continue
                
                url = href if href.startswith("http") else "https://www.reddit.com" + href
                
                if "/comments/" in url and url not in seen:
                    seen.add(url)
                    results.append({
                        "url": url,
                        "metadata": {
                            "source": "reddit_post",
                            "title": "Reddit Konusu" # LLM zaten basligi scraper ile isleyecek
                        }
                    })
            except:
                pass
        print(f"[{agent_name}] Reddit dizininden {len(results)} konu ayiklandi.")
    except Exception as e:
        print(f"[{agent_name}] Reddit extraction hatasi: {e}")

    return results

async def handle_generic_fallback(page, agent_name, base_url, query="", limit=20):
    """
    Daha once tanimlanmamis (Ozel handler'i olmayan) sitelerden, listeleme baglantilarini (Grid/Card) ceker.
    """
    print(f"[{agent_name}] Ozel parser bulunamadi, jenerik link/kart toplayici cagiriliyor.")
    results = []
    seen = set()
    
    # Kelimelere ayir, filtrelemek icin (orjinal sorgudaki onemli kelimeler)
    query_words = []
    if query:
        # Kucult, 3 harften kucuk baglaclari at
        query_words = [w.lower() for w in re.split(r'\W+', query) if len(w) > 2]

    try:
        links = await page.locator("a").all()
        for l in links:
            if len(results) >= limit:
                break
            try:
                href = await l.get_attribute("href")
                if not href or href.startswith("javascript") or href.startswith("#") or "mailto" in href:
                    continue
                    
                text_content = await l.inner_text()
                if not text_content or len(text_content.strip()) < 5: 
                    continue # Cok kisa/bos resim linkleri atla
                    
                url = href if href.startswith("http") else urlparse(base_url).scheme + "://" + urlparse(base_url).netloc + href
                
                # RELEVANCE CHECK (Sorgu Kelimeleri Kontrolu)
                if query_words:
                    text_lower = text_content.lower()
                    url_lower = url.lower()
                    
                    # Sayfa kenarlarindaki baglantilari (Haberler, iletisim vs.) atlamak icin en az 1-2 kelime eslesmesi ara
                    match_count = sum(1 for w in query_words if w in text_lower or w in url_lower)
                    
                    # Toplam test kelimesinin %30'u veya en az 1 anahtar kelime gecmiyorsa, cop linktir.
                    if match_count == 0 and len(query_words) > 0:
                        continue
                        
                # Temizleyip ekle
                if url not in seen:
                    seen.add(url)
                    results.append({
                        "url": url,
                        "metadata": {
                            "source": "generic_listing",
                            "title": text_content.strip()[:150].encode('ascii', 'ignore').decode('ascii')
                        }
                    })
            except:
                pass
                
        print(f"[{agent_name}] Degerli gorunebilecek {len(results)} listeleme url'si ayrilmistir.")
    except Exception as e:
         print(f"[{agent_name}] Jenerik extraction hatasi: {e}")
         
    return results

async def route_platform(page, url, query="", agent_name="handler", limit=20):
    """
    Domain'e bakarak ilgili platform handler'ini dondurur.
    """
    domain = urlparse(url).netloc.lower()
    
    if "sahibinden.com" in domain:
        return await handle_sahibinden(page, agent_name, limit)
    elif "reddit.com" in domain:
        return await handle_reddit(page, agent_name, url, query, limit)
    else:
        return await handle_generic_fallback(page, agent_name, url, query, limit)
