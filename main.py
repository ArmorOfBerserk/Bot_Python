from datetime import datetime
from time import sleep
from random import randint
import threading
import firebase_admin
from telebot import types
from distutils.util import strtobool
from firebase_admin import credentials, firestore
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from util_function import *
from scraping import *

bot = bot_instance()

# CREDENZIALI DATABASE
cred = credentials.Certificate("")
firebase_admin.initialize_app(cred)
db = firestore.client()
DOMAIN = ""

#-----------------------------------------------------------------------------------------------------------------------------------------#
#SEZIONE PER I COMANDI

#COMANDO START
@bot.message_handler(commands=['start'])
def command_start(message):
    # L'username può essere None. Se si capita in questo caso, utilizzare il first name (OBBLIGATORIO).
    update_info(db, message.from_user.id, message.from_user.first_name, message.from_user.last_name)

    bot.send_message(chat_id=message.chat.id, 
    text=f"""Hello {message.from_user.first_name} and welcome to Gamendler! If you\'d like to do a search, just hit the button below this entry. If you want to learn about my features, feel free to check out the <b>commands section</b> of this chat... And if you have any doubts, check out the <b>/help</b> section!""", parse_mode='HTML', reply_markup=InlineKeyboardMarkup( keyboard = [ [InlineKeyboardButton("Search a videogame", switch_inline_query_current_chat="")] ]) )

# COMANDO LIST
@bot.message_handler(commands=['mylist'])
def command_list(message):
    #RITORNA UNA LISTA DAL DB
    update_info(db, message.from_user.id, message.from_user.first_name, message.from_user.last_name)
    get_list(message.chat.id, message.from_user.id)

# COMANDO FREE GAMES
@bot.message_handler(commands=['freegm'])
def command_credit(message):
    result = giochi_gratis()

    text = """<b>Hi! These are the free games available right now in major services and online stores. To access the link and redeem these games, you can click above the name!</b> \n\n\n"""

    for i in result:
        text += f'<a href="{i.get("url")}">{i.get("title")}</a> - {i.get("price")} - {i.get("platform")}.\n\n'

    bot.send_message(message.chat.id, text=text, parse_mode= 'HTML', disable_web_page_preview=True)

# COMANDO STATS
@bot.message_handler(commands=['stats'])
def command_stats(message):
    
    # CAMBIARE CON GIF PIU' CARINA IN CASO E VALUTARE SE FARLO PER TUTTI
    id_placeholder_msg = bot.send_animation(message.chat.id, 'https://c.tenor.com/tEBoZu1ISJ8AAAAC/spinning-loading.gif', caption="Please wait...").id

    stats = db.collection("stats")
    result = stats.order_by(u'n_search', direction=firestore.Query.DESCENDING).limit(5).stream()
    tot_stats = db.collection(u'stats').document(u"ALL").get()
    
    text = "Here are the top 5 most searched games:\n\n"
    cont = 1

    # DATA PER GRAFICO
    label = []
    data = []

    for i in result:
        
        n_search = i.to_dict().get('n_search')

        if n_search == 1:
             string = "search"
        else:
             string = "searches"

        label.append(i.to_dict().get('game_name'))
        data.append(n_search)

        text += f"<b>#{cont}</b> - <b>{i.to_dict().get('game_name')}</b> with <b>{n_search}</b> {string}.\n\n"
        cont += 1

    text += f"Currently <b><i>{tot_stats.to_dict().get('total_n_search')} searches</i></b> have been done and <b><i>{tot_stats.to_dict().get('total_game_search')} different games</i></b> have been searched! :D\n"
    

    bot.edit_message_media(media=types.InputMediaPhoto(getChart(label, data, tot_stats.to_dict().get("total_n_search"))), chat_id=message.chat.id, message_id=id_placeholder_msg)
    bot.edit_message_caption(caption=text, chat_id=message.chat.id, message_id=id_placeholder_msg, parse_mode='HTML')

# COMANDO HELP
@bot.message_handler(commands=['help'])
def command_help(message):
    text =  """<b>EXPLANATION COMMANDS TELEGRAM BOT GAMENDLER:</b>\n
<b>/start</b> is used to start the bot.\n
<b>/mylist</b> is for showing (if it exists) your list of favorite games.\n
<b>/freegm</b> is used to show all the free games that you can get from various digital stores and is updated continuously.\n
<b>/stats</b> is used to show the statistics about the use of the bot (how many searches have been done, the top 5 most searched games and so on).\n
<b>/help</b> is the command you are using now.\n
<b>/credit</b> is used to show the info of the bot author."""

    bot.send_message(message.chat.id, text, 'HTML')

# COMANDO CREDIT
@bot.message_handler(commands=['credit'])
def command_credit(message):
    text = "TelegramBot created by <b>Simone Bilotta</b> for his thesis project at the <b>University of Calabria</b>."

    bot.send_message(message.chat.id, text=text, parse_mode='HTML')

#-----------------------------------------------------------------------------------------------------------------------------------------#
# GESTIONE OPERAZIONI INLINE

#RICERCA DATI NEL DATABASE CON FUNZIONE INLINE
@bot.inline_handler(func = lambda query: query.query != '')
def search_inline(inline_query):
    bot.answer_inline_query(inline_query.id, risultati_ricerca(inline_query.query, inline_query.from_user.id))

# SALVA LE QUERY FATTE
@bot.chosen_inline_handler(func=lambda result: True)
def test_chosen(result):

    new_doc = db.collection(u'stats').document(result.result_id)
    stats = db.collection(u'stats').document(u"ALL")
    
    # SE IL DOCUMENTO NON ESISTE
    if new_doc.get().exists == False:
        # SI CREA CON LA RICERCA NEL DB
        new_doc.set({
            u'game_name': check_query(call_to_db(result.result_id, "custom", "name")[0]).get('title'),
            u'n_search' : 1
        })

        #INCREMENTO VARIABILE GIOCHI ESISTENTI ( DOCUMENTO ALL )
        stats.update({"total_game_search" : firestore.Increment(1)})
    
    # SE IL DOCUMENTO ESISTE
    else:
        new_doc.update({"n_search" : firestore.Increment(1)})
    
    #COMUNQUE VADA, VA INCREMENTATO DI UNO IL NUMERO DELLE RICERCHE TOTALI ( DOCUMENTO ALL )
    stats.update({"total_n_search" : firestore.Increment(1)})
            
# GESTIRSI TASTIERA INLINE POST QUERY
@bot.callback_query_handler(func=lambda call: call.data.find("add_list") != -1)
def action_postQuery(call):

        req = call.data
        command = req.split('-')
        
        #funzione che mi fa la query e mi crea l'oggetto
        data = call_to_db(command[1], "single")

        dict_query = check_query(data[0])

        msg = create_input_message(dict_query)

        new_doc = db.collection(u'game_and_user_list').document(str(call.from_user.id) + str(command[1]))
        if new_doc.get().exists == False:

            # QUA CREO IL DOCUMENTO
            new_doc.set({
                u'user_id': call.from_user.id,
                u'game_id': dict_query.get("id"),
                u'game_title': dict_query.get("title"),
                u'text_message': msg.message_text,
                u'parse': msg.parse_mode,
            })

            #SERVE PER DARE UNA NOTIFICA QUANDO L'AZIONE VIENE FATTA
            bot.answer_callback_query(call.id, "Game correctly added to the list!", False)
        else:
            bot.answer_callback_query(call.id, "Warning, this game is already on your list!", False)

#-----------------------------------------------------------------------------------------------------------------------------------------#
# METODI PER OPERAZIONI CON LA LISTA PRESA DAL DB

# RITORNA LA LISTA DEI GIOCHI DELL'UTENTE. SE L'UTENTE NON HA GIOCHI, ALLORA RITORNA UN MESSAGGIO "D'ERRORE"
# E CHIEDE ALL'UTENTE DI METTERNE QUALCUNO.
def get_list(chat_id, user_id, msg_id = None):

    if msg_id == None:
        id_placeholder_msg = bot.send_message(chat_id, "Please wait...").id
    
    else:
        id_placeholder_msg = bot.edit_message_text("Please wait...", chat_id, msg_id).id

    docs = db.collection(u'game_and_user_list').where(u'user_id', u'==', user_id)

    if len(docs.get()) != 0:
        keyboard = []
        for i in docs.get():
            arr_temp =[]
            arr_temp.append(InlineKeyboardButton(text = i.to_dict().get('game_title'), callback_data= i.to_dict().get('game_id')))
            keyboard.append(arr_temp)
                
            
        #MANDO MESSAGGIO E CI ALLEGO LA KEYBOARD INLINE
        bot.edit_message_text("To view the details of the game, click on it.", chat_id, id_placeholder_msg, reply_markup=InlineKeyboardMarkup(keyboard = keyboard))

    else:
        bot.edit_message_text("Empty list :( \nWant to add a game to it?", chat_id, id_placeholder_msg, reply_markup = InlineKeyboardMarkup(keyboard = [ [InlineKeyboardButton("Search a videogame", switch_inline_query_current_chat="")] ]))

# SE C'È UN GIOCO NELLA LISTA, VIENE RITORNATO E SI PUO' SCEGLIERE. QUESTA FUNZIONE CREA DEGLI ALTRI TASTI INLINE
# PER GESTIRE LE VARIE SCELTE DISPONIBILI.
@bot.callback_query_handler( func=lambda call: call.data.isdigit() )
def select_game_from_list(call):

    doc = db.collection(u'game_and_user_list').document(str(call.from_user.id) + str(call.data))
    doc_info = doc.get().to_dict()

    if db.collection(u'users').document(str(call.from_user.id)).get().to_dict().get('id_game_on') == call.data:
        bool = True
    
    else:
        bool = False

    #AGGIUNGERE SOTTO I BOTTONI CON LE INLINEKEYBOARD (per tornare indietro)
    try:
        bot.edit_message_text(doc_info.get('text_message'), chat_id=call.message.chat.id, message_id=call.message.id, parse_mode= doc_info.get('parse'), reply_markup = InlineKeyboardMarkup( keyboard = [ [InlineKeyboardButton("<< Back to list", callback_data="back")], [InlineKeyboardButton("Remove to list", callback_data=str(f"rv_{call.data}")), InlineKeyboardButton("Reviews", login_url=types.LoginUrl(f'{DOMAIN}/{call.data}'))], [InlineKeyboardButton("Search Price", callback_data=f"{call.data}-"), InlineKeyboardButton(f"News {placeholder(bool)}", callback_data="news")]]))
    except Exception as e:
        bot.answer_callback_query(call.id, "Error, game not found in the list.", False)
        print(f"ERRORE: {e}")

#-----------------------------------------------------------------------------------------------------------------------------------------#
# FUNZIONI CHE RIGUARDANO IL SINGOLO GIOCO, QUINDI TUTTE LE COSE CHE SI POSSONO FARE

# TASTO BACK, CHE TORNA SEMPRE ALLA LISTA DI GIOCHI
@bot.callback_query_handler(func=lambda call: call.data.find("back") != -1)
def back_button(call):


    # SE BACK E' DIVERSO
    if call.data.find('*') != -1:
        bot.edit_message_text("Please wait...", chat_id=None, inline_message_id=call.inline_message_id)
        command = call.data.split('*')
        data = call_to_db(command[1], "single")
        r = create_input_message(check_query(data[0]))

        bot.edit_message_text(r.message_text, chat_id=None, inline_message_id=call.inline_message_id, parse_mode=r.parse_mode, reply_markup=InlineKeyboardMarkup(keyboard= [ [InlineKeyboardButton("Add to list", callback_data = str(f'add_list-{command[1]}')),InlineKeyboardButton("Reviews", login_url=types.LoginUrl(f'{DOMAIN}/{command[1]}'))], [InlineKeyboardButton("Search a videogame", switch_inline_query_current_chat=""), InlineKeyboardButton("Search Price", callback_data=f"{command[1]}-")] ] ))
    
    else:
        # SOLO SE C'E' SCRITTO "BACK"
        get_list(call.message.chat.id, call.from_user.id, call.message.id)

# TASTO CHE RIMUOVE IL GIOCO DALLA LISTA
@bot.callback_query_handler(func=lambda call: call.data.find("_") != -1)
def delete_game(call):

    req = call.data
    command = req.split('_')

    #ELIMINO DOCUMENTO
    db.collection(u'game_and_user_list').document(str(call.from_user.id) + str(command[1])).delete()

    #CONFERMO LA CANCELLAZIONE
    bot.answer_callback_query(call.id, "Gioco rimosso correttamente dalla lista!")

    #RITORNO AL MENU' ( da confermare )
    get_list(call.message.chat.id, call.from_user.id, call.message.id)


# TASTO PRICE, CHE ATTIVA LO SCRAPING WEB DEI PREZZI
@bot.callback_query_handler(func=lambda call: call.data.find("-") != -1)
def view_price(call):

    if call.message == None:
        bot.edit_message_text("Please wait...", chat_id=None, inline_message_id=call.inline_message_id)
    else:
        placeholder_msg = bot.edit_message_text("Please wait...", call.message.chat.id, call.message.id).id
    
    req = call.data
    command = req.split('-')
    #Deve essere chiamata la funzione per la ricerca del titolo nei prezzi
    my_dict = check_query(call_to_db(command[0], "custom", "name")[0])

    search_result = ricerca_gioco(my_dict.get("title"))

    if len(search_result) != 0:
        keyboard = []

        if call.message == None:
            keyboard.append([InlineKeyboardButton(text= "<< Back to list", callback_data=f"back*{command[0]}")])
        else:
             keyboard.append([InlineKeyboardButton(text= "<< Back to list", callback_data=f"back")])

        for i in search_result:
            arr_temp = []
            arr_temp.append(InlineKeyboardButton(text = str(f"{i.get('title')} - {i.get('metacritic')}"), callback_data= f"{command[0]}+{i.get('game_url')}"))
            keyboard.append(arr_temp)
    
        if call.message == None:
            bot.edit_message_text("Here are the results of your research. To view the vendors, click on it.", chat_id=None, inline_message_id=call.inline_message_id, reply_markup=InlineKeyboardMarkup(keyboard = keyboard))
        else:
            bot.edit_message_text("Here are the results of your research. To view the vendors, click on it.", call.message.chat.id, placeholder_msg, reply_markup=InlineKeyboardMarkup(keyboard = keyboard))

    else:
        if call.message == None:
            bot.edit_message_text("I'm sorry, no results found...", chat_id=None, inline_message_id=call.inline_message_id, reply_markup=InlineKeyboardMarkup(keyboard= [[InlineKeyboardButton(text= "<< Back to list", callback_data=f"back*{command[0]}")]]))
        else:
            bot.edit_message_text("I'm sorry, no results found...", call.message.chat.id, placeholder_msg, reply_markup=InlineKeyboardMarkup(keyboard= [[InlineKeyboardButton(text= "<< Back to list", callback_data="back")]]))

@bot.callback_query_handler(func=lambda call: call.data.find("+") != -1)
def aks_result(call):

    keyboard = []
    req = call.data
    command = req.split('+')

    if call.message == None:
        bot.edit_message_text("Please wait...", chat_id=None, inline_message_id=call.inline_message_id)
        keyboard.append([InlineKeyboardButton(text= "<< Back to result", callback_data=f"back*{command[0]}")])

    else:
        bot.edit_message_text("Please wait...", call.message.chat.id, call.message.id)
        keyboard.append([InlineKeyboardButton(text= "<< Back", callback_data=f"{command[0]}-")])
        keyboard.append([InlineKeyboardButton(text= "<< Back to list", callback_data="back")])
    
    shop_list = venditori(command[1])

    for i in shop_list:
        arr_temp =[]
        arr_temp.append(InlineKeyboardButton(text = str(f"{i.get('game_vendor')} - {i.get('rating')} - {i.get('price')}"), url=f"{i.get('url')}"))
        keyboard.append(arr_temp)
    
    # INSERIRE TASTO PER TORNARE INDIETRO
    if call.message == None:
        bot.edit_message_text("Ecco qua.", chat_id=None, inline_message_id=call.inline_message_id, reply_markup=InlineKeyboardMarkup(keyboard = keyboard))
    else:
        bot.edit_message_text("Ecco qua.", call.message.chat.id, call.message.id, reply_markup=InlineKeyboardMarkup(keyboard = keyboard))

def search_news(user, chat_id, title):
    if db.collection(u'users').document(str(user)).get().to_dict().get('news_service'):

        link = db.collection(u'users').document(str(user)).get().to_dict().get('url_news')
        info = getNews(link, title)

        if info[0]:
            bot.send_message(chat_id=chat_id, text=info[1], parse_mode= 'HTML')
            db.collection(u'users').document(str(user)).update({"url_news" : info[2]})
    
        else:
            bot.send_message(chat_id=chat_id, text=f"Sorry, no new news today for {title}! :(")
        
        threading.Timer(86400, search_news, [user, chat_id, title]).start()


# TASTO DI SELEZIONE DELLE NOTIZIE ( notizie sì, notizie no )
@bot.callback_query_handler(func=lambda call: call.data == "news")
def update_button(call):

    title = call.message.text.split("\n")[1].split(" -")[0]
    id_game = (call.message.reply_markup.keyboard[1][0].callback_data).split("_")
    status = (call.message.reply_markup.keyboard[2][1].text).split(" ")
    user = call.from_user.id
    
    # SE E' DISATTIVATO, SI PROVA AD ATTIVARE
    if status[1] == "off":
        # SI PUO' PROCEDERE SOLO SE E' FALSA, QUINDI SE C'E' SOLO UN GIOCO
        if not db.collection(u'users').document(str(user)).get().to_dict().get('news_service'):
            update_info(db=db, id=user, up_news=[True, title, id_game[1]])
            bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup = InlineKeyboardMarkup( keyboard = [ [InlineKeyboardButton("<< Back to list", callback_data="back")], [InlineKeyboardButton("Remove to list", callback_data=str(f"rv_{id_game[1]}")), InlineKeyboardButton("Reviews", login_url=types.LoginUrl(f'{DOMAIN}/{id_game[1]}'))], [InlineKeyboardButton("Search Price", callback_data=f"{id_game[1]}-"), InlineKeyboardButton(f"News {placeholder(True)}", callback_data="news")]]))
            search_news(user, call.message.chat.id, title)        
            bot.answer_callback_query(call.id, f"Activated daily news service for {title}", False)

        else:
            title_on = db.collection(u'users').document(str(user)).get().to_dict().get('title_game_on')
            bot.answer_callback_query(call.id, f"Error: Service already active with {title_on} video game", False)


    elif status[1] == "on":
        update_info(db=db, id=user, up_news=[False, "", ""])
        bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup = InlineKeyboardMarkup( keyboard = [ [InlineKeyboardButton("<< Back to list", callback_data="back")], [InlineKeyboardButton("Remove to list", callback_data=str(f"rv_{id_game[1]}")), InlineKeyboardButton("Reviews", login_url=types.LoginUrl(f'{DOMAIN}/{id_game[1]}'))], [InlineKeyboardButton("Search Price", callback_data=f"{id_game[1]}-"), InlineKeyboardButton(f"News {placeholder(False)}", callback_data="news")]]))
        bot.answer_callback_query(call.id, f"Deactivated daily news service for {title}", False)
    

try:
    bot.infinity_polling()
except Exception:
    print("Ci sono problemi di linea, come sempre...")
