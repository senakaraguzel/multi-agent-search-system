from typing import List
from playwright.sync_api import Page

try:
    from agents.search_agent import search_agent
    from agents.scroll_agent  import scroll_agent
except ImportError:
    from search_agent import search_agent
    from scroll_agent  import scroll_agent


class BrowsingAgent:
    """
    Google Maps gezinme sorumluluklarını üstlenen ajan.
    - search(query_text)   : Google Maps'i açar ve arama yapar.
    - collect_urls(max_scrolls) : Scroll ederek işletme URL'lerini toplar.
    """

    def __init__(self, page: Page):
        self.page = page

    def search(self, query_text: str) -> bool:
        """
        Google Maps'te verilen sorguyu arar.

        Args:
            query_text (str): Aranacak ifade.

        Returns:
            bool: Arama başarılıysa True.
        """
        print(f"[BrowsingAgent] Arama: {query_text}")
        return search_agent(self.page, query_text)

    def collect_urls(self, max_scrolls: int = 30) -> List[str]:
        """
        Arama sonuç listesinde scroll yaparak işletme URL'lerini toplar.

        Args:
            max_scrolls (int): Maksimum scroll sayısı.

        Returns:
            List[str]: Benzersiz işletme URL listesi.
        """
        print(f"[BrowsingAgent] URL toplama başladı (max_scrolls={max_scrolls})")
        urls = scroll_agent(self.page, max_scrolls=max_scrolls)
        print(f"[BrowsingAgent] Toplanan URL: {len(urls)}")
        return urls
