import requests
import re
import urllib.parse

def test_search(query):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
    print(f"\nBuscando: {url}")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
        links = re.findall(r'<a[^>]+class=\"result-link\"[^>]*>([^<]+)</a>', r.text, re.IGNORECASE)
        snippets = re.findall(r'<td[^>]+class=\"result-snippet\"[^>]*>([^<]+)</td>', r.text, re.IGNORECASE)
        for i in range(min(3, len(links))):
            print(f"- {links[i]}")
            if i < len(snippets): print(f"  {snippets[i][:100]}...")
    except Exception as e:
        print(f"Error: {e}")

test_search("Tu Quincho Rosario")
