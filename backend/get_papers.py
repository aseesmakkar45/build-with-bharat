import urllib.request
import json

url = 'https://api.crossref.org/works?query=microgrid+energy+management+machine+learning+optimization&select=DOI,title,is-referenced-by-count&sort=is-referenced-by-count&order=desc&rows=3'
req = urllib.request.Request(url, headers={'User-Agent': 'mailto:test@example.com'})

try:
    response = urllib.request.urlopen(req).read().decode('utf-8')
    data = json.loads(response)
    for item in data['message']['items']:
        title = item.get('title', [''])[0]
        doi = item.get('DOI', '')
        citations = item.get('is-referenced-by-count', 0)
        print(f'- https://doi.org/{doi} ("{title}" - {citations} citations)')
except Exception as e:
    print(e)
