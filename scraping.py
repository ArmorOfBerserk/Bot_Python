from datetime import datetime
import telebot
import requests
import urllib
import firebase_admin
from telebot import types
from bs4 import BeautifulSoup
from selenium import webdriver
from distutils.util import strtobool
from firebase_admin import credentials, firestore
from selenium.webdriver.chrome.options import Options
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


# METODO PULITO PER FARE LE REQUEST E SUCCESSIVAMENTE FARE LO SCRAPING
def request_and_soup(url):
    result = requests.get(url)

    if result.ok:
        soup = BeautifulSoup(result.text, 'html.parser')
        return soup
    
    else:
        print("Errore")

# METODO PER PRENDERE DA UN'ALTRA PAGINA LE RECENSIONI DEL VENDITORE
def get_ratings(url):

    soup = request_and_soup(url)
    rating = soup.find('a', class_='merchant__link').find('p', class_='rating-num').getText().split()
    n_vote = soup.find('div', class_='merchant-rating__container').find('div', class_='text-center').getText().split()
    return str(f"{rating[0]}/5.0 with {n_vote[0]} votes.")


# SERVE PER PRENDERE LA LISTA DI VENDITORI DI QUEL GIOCO. (SE È UN PO' LENTO, È COLPA DI SELENIUM.)
def venditori(url):
    
    chrome_op = Options()
    chrome_op.add_argument("--headless")
    chrome_op.add_argument("log-level=3")
    browser = webdriver.Chrome('C:\Webdrivers\chromedriver.exe', options=chrome_op)
    browser.get(url)
    content_page = browser.page_source
    browser.quit()

    soup = BeautifulSoup(content_page, 'html.parser')
    
    data = soup.find('div', class_='content-box offers').find('div', class_='offers-table x-offers').find_all('div', class_='offers-table-row x-offer')
    

    arr = []
    limit = 0

    for i in data:
        if limit != 5:
            # MI CREO IL DIZIONARIO
            my_dict = {}
            # OTTENGO IL LINK PER IL GIOCO
            my_dict["game_vendor"] = str(i.find('div', class_='x-offer-merchant-title offers-merchant text-truncate').getText()).replace('\n', '')
            my_dict["rating"] = get_ratings(i.find('div', class_='offers-merchant-reviews').find('a').get('href'))
            my_dict["price"] = str(i.find('div', class_='offers-table-row-cell buy-btn-cell').find('span', class_='x-offer-buy-btn-in-stock').getText()).split()[0]
            my_dict["url"] =str(i.find('div', class_='offers-table-row-cell buy-btn-cell').find('a').get('href'))
            limit += 1

            arr.append(my_dict)
        
    return arr

# PRIMA DI CHIAMARE "VENDITORI", VIENE PRESENTATA QUESTA LISTA CONTENENTE GLI ARTICOLI NELLA RICERCA
def ricerca_gioco(title):
    encode_title = urllib.parse.quote_plus(title)
    url_base = 'https://www.allkeyshop.com/blog/catalogue/search-' + encode_title

    soup = request_and_soup(url_base)
    data = soup.find_all('div', class_='content-box')
    
    # OTTENGO LA LISTA DI TUTTI I RISULTATI
    elem = data[1].find_all('li', class_='search-results-row')

    # MI CREO UN ARRAY CON CUI CONTENERE TUTTI I DIZIONARI
    arr = []
    limit = 0

    for i in elem:
        if limit != 5:
            # MI CREO IL DIZIONARIO
            my_dict = {}
            # OTTENGO IL LINK PER L'ARTICOLO
            my_dict["game_url"] = shorter_link(str(i.find('a').get('href')))
            #my_dict["game_url"] = "Nulla"
            my_dict["title"] = str(i.find('h2').string)
            my_dict["metacritic"] = metacritic_score(str(i.find('div', class_='metacritic d-none d-xl-block').getText()))
            my_dict["lower_price"] =str(i.find('div', class_='search-results-row-price').string).split()[0]
            limit += 1

            arr.append(my_dict)
    
    return arr

def metacritic_score(d_score):
    c_score = d_score.split()[0]
    
    if c_score == '—':
        return  f"Metascore: N/A"
    else:
        return f"Metascore: {c_score}"

# FUNZIONE OPZIONALE PER OTTENERE I LINK ACCORCIATI
def shorter_link(url):

    header = {'Authorization': 'Bearer 7sww4MZIuL9YuCvoV7ZOQ41kGXcavfuOheZRyZYzTtZjn8h8ajAgaFc6JRbe'}

    data = {
            "url": f"{url}",
            "domain": "tiny.one"
           }

    response = requests.post("https://api.tinyurl.com/create", headers=header, data=data)

    return response.json().get('data').get("tiny_url")

# SERVE PER OTTENERE, SEMPRE TRAMITE SCRAPING, I GIOCHI GRATIS DI QUESTO MESE.
def giochi_gratis():
    url = 'https://widget.allkeyshop.com/lib/generate/deals?locale=en_GB&currency=eur&typeList=free&console=all&backgroundColor=transparent&priceBackgroundColor=147ac3&borderWidth=0&borderColor=000000&apiKey=aks'
    
    soup = request_and_soup(url)
    data = soup.find('div', class_='splide__list').find_all('div', class_='splide__slide')

    arr = []

    for i in data:
        # MI CREO IL DIZIONARIO
        my_dict = {}

        my_dict["title"] = str(str(i.find('div', class_='game-container').find('img', class_='game-cover').get('alt')))

        if i.get('data-console') == 'pc':
            if i.get('data-drm') == 'none':
                my_dict["platform"] = "PC, free with Prime Gaming"
            else:
                my_dict["platform"] = "PC, free with Epic Games Store"
                
        else:
            my_dict["platform"] = str(i.get('data-console')).capitalize()

        l = i.getText().split()
        if l[0] == 'demo':
            my_dict["price"] = str(' '.join(l)).capitalize()
        
        else:    
            my_dict["price"] = str(' '.join(l))

        my_dict["url"] = str(i.find('a').get('href'))

        arr.append(my_dict)
    
    return arr