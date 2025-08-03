import sys
import time
from fake_useragent import UserAgent
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlparse,parse_qs
from stem import Signal
from stem.control import Controller
import hashlib
from datetime import date
import json
from pathlib import Path

ua=UserAgent()

def get_headers():
    return {
        'User-Agent': ua.random,
        'Accept-Language': 'en-US,en;q=0.9',
    }

# Tor SOCKS5 proxy
PROXIES = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}

def renew_tor_ip():#to get new tor proxy
    with Controller.from_port(port=9051) as controller:
        controller.authenticate(password='Crawling@123')  
        controller.signal(Signal.NEWNYM)

def is_tor_ip_working():#to validate the proxy
    try:
        r = requests.get('http://httpbin.org/ip', proxies=PROXIES, timeout=10)
        #print(f"Current IP: {r.text.strip()}")
        return True
    except:
        return False

def valid_ip():
    renew_tor_ip()          # Force new IP for every request
    time.sleep(10)
    if is_tor_ip_working():
        return
    else:
        valid_ip()
'''
def crawl(url):
    links=set()
    valid_ip()
    res = requests.get(url=url,headers=get_headers(),proxies=PROXIES)
    soup=BeautifulSoup(res.text,'html.parser')
    table=soup.find('table')
    if table is None:
        return links
    else:
        for a_tag in table.find_all('a', href=True):
            full_link = urljoin(url, a_tag['href'])  # Make full absolute URL
            links.add(full_link)          
        return links
'''
def hash_url(url):
    try:
        response = requests.get(url, proxies=PROXIES,timeout=10)
        response.raise_for_status()  # Raise error if not 200 OK
            # Optional: parse and prettify the HTML (to normalize formatting)
        soup = BeautifulSoup(response.text, 'html.parser')
        normalized_html = soup.prettify()
            # Compute SHA-256 hash
        hash_object = hashlib.sha256(normalized_html.encode('utf-8'))
        return hash_object.hexdigest()
    except Exception as e:
        print(f"[ERROR] Failed to hash {url}: {e}")
        return None
    
def append_to_json(file_path, repo_name, new_data):
    file = Path(file_path)
    # Load existing data or start with an empty dict
    if file.exists():
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    # Add or update repo section
    if repo_name not in data:
        data[repo_name] = {}

    data[repo_name].update(new_data)

    # Write updated data back
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def single_repo(url):
    print(f"parsing {url}.............")
    parts = urlparse(url).path.strip("/").split("/")
    repo_name=parts[0]+"/"+parts[1]
    links=set()
    valid_ip()
    res = requests.get(url=url,headers=get_headers(),proxies=PROXIES)
    soup=BeautifulSoup(res.text,'html.parser')
    table=soup.find('table')
    if table is None:
        return 
    else:
        for a_tag in table.find_all('a', href=True):
            full_link = urljoin(url, a_tag['href'])  # Make full absolute URL
            links.add(full_link)              
    '''
    links=set()
    links.add(url)
    visited=set()
    while(len(links)!=0):
        link=links.pop()
        if link in visited:
            continue
        else:
            visited.add(link)
            res=crawl(link)
            links.update(res)
    #res=crawl(url)
    #links.update(res)
    '''
    url_hash={}
    for link in links:
        hash_val=hash_url(link)
        if hash_val:
            url_hash[link] = hash_val

    filename = date.today().isoformat() + ".json"
    print("saving the data into file ................")
    append_to_json(filename,repo_name,url_hash)
   

def multi_repo(url):
    print("Executing multiple repo ........")
    valid_ip()
    res = requests.get(url=url,headers=get_headers(),proxies=PROXIES)
    soup=BeautifulSoup(res.text,'html.parser')
    links=set()
    p=0
    print("collecting all pages url ........")
    for a_tag in soup.find_all('a',class_=True,href=True):
        if len(a_tag['class']) == 1 and a_tag['class'][0] == "prc-Pagination-Page-yoEQf":
            full_url = urljoin(url, a_tag['href'])
            query_params = parse_qs(urlparse(full_url).query)
            p_value = int(query_params.get("p", [0])[0])
            if(p_value>p):
                p=p_value    

    print("Parsing each page and collecting all repos in it..........")
    b_url=soup.find('a',class_="prc-Pagination-Page-yoEQf",href=True)['href']
    base_url = b_url.split("p=")[0] + "p="
    for i in range(1,(p+1)):
        print(f"Parsing {i} page.......")
        page_url=base_url+str(i)
        valid_ip()
        page_res = requests.get(url=page_url,headers=get_headers(),proxies=PROXIES)
        page_soup=BeautifulSoup(page_res.text,'html.parser')
        for a_tag in page_soup.find_all('a',class_=True,href=True):
            if len(a_tag['class']) == 1 and a_tag['class'][0] == "prc-Link-Link-85e08":
                full_url = urljoin(url, a_tag['href'])
                links.add(full_url)

    count=0
    for link in links:
        count=count+1
        print(f"Executing the {count} repo and url is {link}")
        single_repo(link)
    print(count)
    print(p)

def get_urls(url):
    print("checking the url is single repo or multi repo ........")
    path = urlparse(url).path.strip('/')
    parts = path.split('/')
    
    if len(parts) >= 2 and parts[0] and parts[1]:
        # Check it's not 'search', 'topics', etc.
        if parts[0] not in ['search', 'topics', 'explore']:
            single_repo(url)
        else:
            multi_repo(url)
    else:
        multi_repo(url)

if __name__=="__main__":
    print("Executing main function ...........")
    if(len(sys.argv)>1):
        get_urls(sys.argv[1])
    else:
        print("URL is not present in command line arguments")
    