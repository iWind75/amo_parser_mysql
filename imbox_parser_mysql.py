import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
#from selenium.webdriver.common.action_chains import ActionChains
import time, os
from datetime import datetime, timedelta, timezone
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.utils import ValueRenderOption, ValueInputOption
import logging
import sqlite3
import requests
from threading import Thread
from logging.handlers import RotatingFileHandler
import pymysql
from pymysql import err
from contextlib import contextmanager
from pathlib import Path
import sys

# Домен, токен и учетные записи amoCRM
AMOCRM_DOMAIN = 'stalservice24.amocrm.ru'
CRM_ACCOUNT_NAME = 'stalservice24'
URL_BASE =  f"https://{AMOCRM_DOMAIN}/api/v4/"
AMO_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjBhZjM4OTk5Yjc2NzMwN2U1YTBiM2FkNTNiZjQwNzljMjc2ODRmMWQ0YjZmY2I0OWQ2MTZjZDkwODdiMzVlMDAyZmNkY2NiMWUwMmEzYTVmIn0.eyJhdWQiOiJkNGRiYWM1NS01ZmY4LTRjNzQtYjc2Zi0wYWQ0NTk2NWMzZjkiLCJqdGkiOiIwYWYzODk5OWI3NjczMDdlNWEwYjNhZDUzYmY0MDc5YzI3Njg0ZjFkNGI2ZmNiNDlkNjE2Y2Q5MDg3YjM1ZTAwMmZjZGNjYjFlMDJhM2E1ZiIsImlhdCI6MTc1MTYzNjEyNiwibmJmIjoxNzUxNjM2MTI2LCJleHAiOjE5MDkzNTM2MDAsInN1YiI6IjI5NDg2NDEiLCJncmFudF90eXBlIjoiIiwiYWNjb3VudF9pZCI6MjI4MjgwMzYsImJhc2VfZG9tYWluIjoiYW1vY3JtLnJ1IiwidmVyc2lvbiI6Miwic2NvcGVzIjpbInB1c2hfbm90aWZpY2F0aW9ucyIsImZpbGVzIiwiY3JtIiwibm90aWZpY2F0aW9ucyJdLCJoYXNoX3V1aWQiOiI2YjUxNzFkYi0zM2FlLTQ1MjEtYTJlOC1mMDQ4YjNiODdmMTYiLCJhcGlfZG9tYWluIjoiYXBpLWIuYW1vY3JtLnJ1In0.Gw8j6-Y7AgaqsXXP2KX8clO_6lg2aHdK89rK1cXttj2Qmm7qKbePq-VK35ghQ6_Nj6mt8d2m8FuwY3pklO1GE2yFYmkJueNhIb1VWhHmI4JaOFjo4hXWqbm1o6xsEJenP0t_3TiIPYcOdXernraupNn70xqsN2VffvKAotMLk1Gex4yR8rTTx3H_SdeMcHyGtqx3eAfadGuT0a-Y7xj_mllQ-d5Wpnu-5d8rzUjYEA_Lr_SuPHy1WLXZiyVMY47bdFrJ-jUprzK92ToF1a3PZM9yeSO2fDzQWNvwp1NLXOA5-MZ2SGV60P-p_LV4kPbsBSX5nID0N3Dm1TkyB61j9g'
# Учетные данные AMO
AMO_LOGIN = '79250749545@polimer.me'
AMO_PASSWORD = 'iW1nd15275'

# ID таблицы результата
GOOGLE_SHEET_ID = '15zMHkKu7FHQy2Upurf2eZepDvaAzTPh4Hnoc9VPhLuE'

# Файл ключа сервисного аккаунта
GOOGLE_SERVICE_ACC_FILE = 'csg-dashboard-744071c71b72.json'
# Имя листа чатов
GOOGLE_CHATS_WORKSHEET_NAME = 'Чаты'
# Имя листа эффективности
GOOGLE_EFFI_WORKSHEET_NAME = 'Эффективность'
# Имя листа превышения времени
GOOGLE_LOSTTIME_WORKSHEET_NAME = 'Превышение времени'
# Время задержки ответа менеджера, при превышении которого чат уходит из аналитики, секунд
LOSTTIME_DELAY = 1200
# Время, через которое удаляются чаты из истории часов
CHAT_DELETE_HOURS = 36

# URL для загрузки окна чатов
CURR_PATH = 'https://stalservice24.amocrm.ru/imbox/'

CHAT_DELETE_TIME = 86400

LOGFILENAME = Path(__file__).parent.parent.joinpath('log').joinpath('AMO_ImBox_parser.log')
DEBUG = str(os.getenv('DEBUG', 'False')).lower() in ('true', '1', 't', 'y')
PROXY = os.getenv('PROXY', False)
MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql')

DB_NAME = 'eff.db'

##########################################################################
### Получение пользовательского логгера и установка уровня логирования ###
##########################################################################

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        RotatingFileHandler(LOGFILENAME, maxBytes=200000, backupCount=5, encoding='utf-8'),
        logging.StreamHandler()
    ])

if DEBUG:
    logging.getLogger().setLevel(logging.DEBUG)
    logging.info('Включен режим отладки')


# Авторизуемся в Google и открываем таблицу
#fp = os.path.join(os.getcwd(),GOOGLE_SERVICE_ACC_FILE)
#scope = ['https://spreadsheets.google.com/feeds']
#creds = ServiceAccountCredentials.from_json_keyfile_name(fp, scope)
#client = gspread.service_account(filename=fp)
#sheet = client.open_by_key(GOOGLE_SHEET_ID)
#worksheet_chat = sheet.worksheet(GOOGLE_CHATS_WORKSHEET_NAME)
#worksheet_effi = sheet.worksheet(GOOGLE_EFFI_WORKSHEET_NAME)
#worksheet_losttime = sheet.worksheet(GOOGLE_LOSTTIME_WORKSHEET_NAME)

XP_talk = "//*[contains(@class,'notification notification--talk')]"

# ==== КОНФИГУРАЦИЯ БАЗЫ ДАННЫХ ====

DB_CONFIG = {
        'host': MYSQL_HOST, 
        'port': 3306,
        'user': 'sqluser',
        'password': 'appuserpass', 
        'database': 'amo_imbox', 
        'charset': 'utf8mb4'
        }

@contextmanager
def get_db_connection(host: str, port:int, user: str, password: str, database: str, 
                     charset='utf8mb4', autocommit=True):
    """Контекстный менеджер для безопасного подключения к MySQL."""
    conn = None
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset=charset,
            autocommit=autocommit
        )
        conn.ping(reconnect=True)  # Автоматическое восстановление соединения
        yield conn
    except err.DatabaseError as e:
        logging.error(f"Ошибка БД: код={e.args[0]}, текст={e.args[1]}")
        logging.error(f"Тип: {type(e).__name__}")
        
    except err.InterfaceError as e:
        logging.error(f"Ошибка интерфейса: {e}")
        
    except Exception as e:
        logging.error(f"Другое исключение: {type(e).__name__}")
    finally:
        if conn is not None:
            conn.close()


managers = []
analysis = []
losttime = []
stop_update = False


def convert_seconds(seconds):
    return str(timedelta(seconds=seconds))

def get_managers() -> bool:
    """
    Загружает из Амо CRM список активных пользователей,
    заполняет глобальный список managers,
    обновляет базу данных, таблица managers.

    При успехе возвращает True.
    """
    global managers

    headers = {"Authorization": f"Bearer {AMO_TOKEN}"}
    pagenum = 1
    url = URL_BASE + "users"
    pageparam = {"page": pagenum, "with": "contacts,group", "limit": 249}

    managers = []
    batch = []        # батч для массовой записи в БД

    while True:
        try:
            pageparam["page"] = pagenum
            response = requests.get(url, headers=headers, params=pageparam, timeout=60)

            if response.status_code != 200:
                break

            data = response.json()
            users_data = data.get("_embedded", {}).get("users", [])

            if not users_data:
                break

            for u in users_data:
                user_id = u["id"]
                name = u.get("name", "")
                groups = u.get("_embedded", {}).get("groups", [])
                group_id = groups[0]["id"] if groups else None
                group_name = groups[0]["name"] if groups else ""

                # Проверка активности по правам (если по всем сущностям права = "D")
                rights = u.get("rights", {})
                is_inactive = True
                for ent in ["leads", "contacts", "companies", "tasks"]:
                    r = rights.get(ent, {})
                    for k in r.keys():
                        if r[k] != "D":
                            is_inactive = False
                            break
                    if not is_inactive:
                        break

                # Проверка по статусу is_active
                active = not (is_inactive and rights.get("is_active") is False)

                managers.append(
                    {
                        "id": user_id,
                        "name": name,
                        "group_id": group_id,
                        "group_name": group_name,
                        "active": active,
                    }
                )

                batch.append((user_id, name, group_id, group_name, active))

            pagenum += 1

        except requests.RequestException as e:
            logging.error(f"Ошибка получения пользователей АМОCRM: {e}")
            return False
        except Exception as e:
            logging.error(f"Неизвестная ошибка при работе с пользователями АМОCRM: {e}")
            return False

    # массовая запись в БД
    try:
        if batch:
            with get_db_connection(**DB_CONFIG) as mysql_conn:
                with mysql_conn.cursor() as cursor:
                    sql = """
                        INSERT INTO managers(id, name, group_id, group_name, active)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            name = VALUES(name),
                            group_id = VALUES(group_id),
                            group_name = VALUES(group_name),
                            active = VALUES(active)
                    """
                    cursor.executemany(sql, batch)
                    mysql_conn.commit()
        return True
    except Exception as e:
        logging.warning(f"Ошибка записи пользователей в базу данных: {e}")
        return False


### Список просроченных ответов ###
# Формат списка 
# {ID чата АМОСРМ, Клиент, Время последнего ответа клиента, Менеджер, Время последнего ответа менеджера, Время_менеджера}


def update_conversations():

    # запуск браузера Chrome
    chrome_options = Options()
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--headless')
    browser = webdriver.Remote(command_executor='http://localhost:4444/wd/hub',options=webdriver.ChromeOptions())
    browser.get(CURR_PATH) 
    login_element =  browser.find_element(By.NAME, 'username')
    login_element.send_keys(AMO_LOGIN)
    login_element =  browser.find_element(By.NAME, 'password')
    login_element.send_keys(AMO_PASSWORD)
    button_element = WebDriverWait(browser, 100).until(EC.element_to_be_clickable((By.ID, 'auth_submit')))
    browser.implicitly_wait(50)
    button_element.click()
    time.sleep(10)

    global stop_update 
    stop_update= False
    
    thread_connection = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

    def delete_chat(chat_id):
    
        connection_delete = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        try:
            cursor = connection_delete.cursor()
            sql = 'delete FROM conversations where id = ?'
            params = [chat_id]
            cursor.execute(sql,params)
            connection_delete.commit()
        except Exception as e:
            connection_delete.rollback()
            logging.error(f'12. Ошибка удаления данных из базы данных, таблица conversations: {e}')

        finally:
            connection_delete.close()

    while not stop_update:
        try:
            cursor = thread_connection.cursor()
            cursor.execute('SELECT * from conversations')
            conversations = cursor.fetchall()
        except Exception as e:
            logging.error(f'7. Ошибка получения перечня чатов, таблица conversations: {e}')
            continue

        # Пробуем получить перечень чатов из АМОСРМ
        try:
            messagelist =browser.find_element(By.ID, 'inbox_messaging_list')
        except Exception as e:
            logging.error(f'Ошибка получения чатов: {e}')
            continue

        # Делим на слайсы по \n
        messages = messagelist.text.split('\n')
        
        # Если перечень пустой - пропускаем
        if len(messages)<1:
            continue
        
        # Делим на сообщения в список по 4 значения:
        # {ID чата АМОСРМ, Дата и время сообщения, Тема сообщения, Автор: Текст сообщения}

        sliced = [messages[i:i + 4] for i in range(0, len(messages), 4)]
        
        ##################################
        ### Разбираем каждое сообщение ###
        ##################################

        for message in sliced: # Разбор полученного сообщения, сохранение в список чатов

            if len(message) < 4:
                continue

            #if message in conversations:
            #    # Если уже есть в списке бесед - пропускаем, чтобы не было дублей 
            #    continue
            
            # Если сообщения нет в списке бесед, добавляем в список бесед...
       
            ### Разбираем сообщение ###
            # ID чата АМОСРМ
            message_id = message[0]
            # Тема сообщения
            message_title = message[2]
            # Автор сообщения
            message_opponent_name = message[3].split(':')[0]
            # Сторона сообщения: если автор сообщения в списке наших менеджеров - Менеджер, иначе - Клиент
            message_direction = ('MK' if message_opponent_name in managers else 'KM')
            # Парсим дату сообщения
            try:
                t = message[1]
                t1 = t.replace('Сегодня','{:%d.%m.%Y}'.format(datetime.now())).replace('Вчера','{:%d.%m.%Y}'.format(datetime.now() - timedelta(days=1)))
                s = datetime.strptime(t1, "%d.%m.%Y %H:%M")
                message_datetime = s.timestamp()
            except Exception:
                logging.error(f"9. Ошибка парсинга даты {message[1]}") 
                continue

            # Текст сообщения
            message_text = message[3].split(':')[1] 

            id_s = list(map(lambda x:str(x[0]), conversations))
            date_s = list(map(lambda x:x[1], conversations))
            message_s = list(map(lambda x:str(x[5]),  conversations))

            if message_id in id_s and message_datetime in date_s and message_text in message_s:
                continue

            try:
                sql = 'select max(date) from conversations where id =?'
                params = (message_id,)
                cursor.execute(sql,params)
                t_tmp = cursor.fetchall()[0][0]
            except Exception as e:
                logging.error(f'10. Ошибка доступа к базе данных, таблица conversations: {e}')                    
            if t_tmp is None:
                message_ansver_time = 0
            else:
                message_ansver_time =message_datetime - t_tmp 

            if  message_ansver_time > CHAT_DELETE_TIME: 
                delete_chat(message_id)
                continue


            try:
                cursor = thread_connection.cursor()
                sql = 'INSERT INTO conversations (id, date, theme, author, direction, message,ansver_time) VALUES (?,?,?,?,?,?,?)'
                params = (message_id,message_datetime,message_title,message_opponent_name,message_direction, message_text,message_ansver_time,)
                cursor.execute(sql,params)
                thread_connection.commit()
            except Exception as e:
                thread_connection.rollback()
                logging.error(f'11. Ошибка записи сообщения в базу данных, таблица conversations: {e}')
                break      
        time.sleep (5)


def calc_losttime():
    connection_losttime = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    # Получаем записанны в базу чаты
    try:
        cursor = connection_losttime.cursor()
        cursor.execute('SELECT * FROM conversations order by date')
        chats = cursor.fetchall()
        cursor.execute('SELECT * from losttime')
        losttime = cursor.fetchall()
        cursor.execute('select author, count(*) from conversations where direction = \'MK\' group by author order by author')
    except Exception as e:
        logging.error(f'13. Ошибка получения данных из базы данных: {e}')    
    
    chat_ids = list(set(map(lambda x:x[0],chats)))
    losttime_ids = list(map(lambda x:x[0],losttime))

    # Просматриваем все чаты по уникальным ID 
    for t, chat_id  in enumerate(chat_ids):
        chat = [ch for ch in chats if ch[0] == chat_id]
    
        # Если собщений в чате больше одного - проверяем чат на повторные цепочки сообщений
        for c in range(len(chat)-1,0,-1):
            if (chat[c][4] == chat[c-1][4]):
                # Если повторные цепочки есть - удаляем лишние, чтобы остались только последние сообщения сторон
                chat.pop(c-1)                
        
        # Если после удаления повторов остались данные для аналитики - продолжаем, иначе следующий чат
        if len(chat)<2:
            continue   
        
        # Последнее сообщение - от менеджера
        if (chat[-1][4] == 'MK'): 
            time_delay = datetime.now().timestamp() - chat[-1][1]
            # если с времени последнего сообщения менеджера прошло более суток, но клиент не ответил - чат метрвый, удаляем
            if time_delay > CHAT_DELETE_TIME: 
                #delete_chat(chat_id)
                continue
            
            # Чат живой, определяем задержку ответа менеджера клиенту
            # Время сообщения клиента и менеджера
            client_msg_time = datetime.fromtimestamp(int(chat[-2][1]))
           
            # Проверяем, сообщение клиента в рабочее время или нет?
            if client_msg_time.date() < datetime.now().date() or\
                client_msg_time.date() == datetime.now().date() and client_msg_time.hour <= 9:
                # Сообщение было раньше сегодня, считаем с начала дня
                time_delay = datetime.now().replace(hour=9,minute=0,second=0).timestamp() - int(chat[-2][1])
            else:
                time_delay = int(chat[-1][1]) - int(chat[-2][1])

            if time_delay > LOSTTIME_DELAY: # Зафиксировано превышение
                # Если чат уже в таблице просрочек
                if chat_id in losttime_ids:
                    # Обновляем время просрочки
                    try:
                        cursor = connection_losttime.cursor()
                        sql = 'UPDATE losttime SET delaytime=? WHERE id = ?'
                        params =[int(time_delay), chat_id]
                        cursor.execute(sql,params)
                        connection_losttime.commit()
                    except Exception as e:
                        connection_losttime.rollback()
                        logging.error(f'14. Ошибка обновления данных, таблица losttime: {e}')
                        break                                
                else:
                    # Добавляем запись о просрочке в таблицу
                    try:
                        cursor = connection_losttime.cursor()
                        sql = 'INSERT INTO losttime (id, manager,managertime,customer, custometime,delaytime) VALUES(?,?,?,?,?,?)'
                        params =(chat_id, chat[-2][3], chat[-2][1], chat[-1][3], chat[-1][1], int(time_delay))
                        cursor.execute(sql,params)
                        connection_losttime.commit()
                    except Exception as e:
                        connection_losttime.rollback()
                        logging.error(f'15. Ошибка записи в базу данных, таблица losttime: {e}')
                        break  

def main():
    get_managers()
    while 1:
        calc_losttime()
        time.sleep(10)




    """
            # Ищем запись с соответствубщим ID чата в таблице аналитики
            find_a = False
            for a in range(0,len(analysis),1):
                if analysis[a][0] == t[0]:
                    find_a =True
                    break
            
            # Готовим переменные для списка аналитики
            time_customer = 0
            time_manager = 0
            count_customer = 0
            count_manager = 0
            customer_name = (chunks[0][2] if chunks[0][1] == 'Клиент' else '')
            manager_name = (chunks[0][2] if chunks[0][1] == 'Менеджер' else '')
            
            
            # Если сообщений в чате два и более - есть что анализировать
            if len(chunks) >= 2:
                
                # Проходим по всем сообщениям
                for c in range(0,len(chunks)-1,1):
                    
                    # Если сообщение - ответ менеджера 
                    if (chunks[c][1] == 'Клиент') and (chunks[c+1][1] == 'Менеджер'):
                        # Считаем сколько секунд прошло с сообщения клиента
                        time_manager += (datetime.strptime(chunks[c+1][0], "%d.%m.%Y %H:%M") - datetime.strptime(chunks[c][0], "%d.%m.%Y %H:%M")).seconds
                        # Увеличиваем количество сообщений для расчета среднего
                        count_manager +=1
                        # Заполняем авторов сообщений
                        customer_name = chunks[c][2]
                        manager_name = chunks[c+1][2]
                    
                    # Если сообщение - ответ клиента 
                    elif (chunks[c][1] == 'Менеджер') and (chunks[c+1][1] == 'Клиент'):
                        # Считаем сколько секунд прошло с сообщения менеджера
                        time_customer += (datetime.strptime(chunks[c+1][0], "%d.%m.%Y %H:%M") - datetime.strptime(chunks[c][0], "%d.%m.%Y %H:%M")).seconds
                        # Увеличиваем количество сообщений для расчета среднего
                        count_customer +=1
                        # Заполняем авторов сообщений
                        manager_name_name = chunks[c][2]
                        customer_name = chunks[c+1][2]
                
                if not(find_a): # Если данного чата нет в таблице расчета аналитики...
                    # Создаем новую запись таблицы аналитики
                    analysis_item = ['','','',0,0] #id, Клиент, Менеджер, Время_клиента, Время_менеджера
                    analysis_item[0] = t[0] # ID чата
                    analysis_item[1] = customer_name
                    analysis_item[2] = manager_name
                    analysis_item[3] = (0 if count_customer==0 else round(time_customer / count_customer,0))
                    analysis_item[4] = (0 if count_manager==0 else round(time_manager / count_manager,0))
                    analysis.append(analysis_item)
                else: # обновляем запись для данного чата в таблице аналитики
                    analysis[a][0] = t[0] # ID чата
                    if analysis[a][1] =='':
                        analysis[a][1] = customer_name
                    if analysis[a][2] =='':
                        analysis[a][2] = manager_name
                    analysis_item[3] = (0 if count_customer==0 else round(time_customer / count_customer,0))
                    analysis_item[4] = (0 if count_manager==0 else round(time_manager / count_manager,0))
    
        ########################################
        ### Собираем аналитику по менеджерам ###
        ########################################

        # Формируем список уникальных записей менеджеров, данные которых есть в таблице аналитики
        
        uniq_managers_tmp = []
        for a in analysis:
            uniq_managers_tmp.append(a[2])
        uniq_managers = list(set(uniq_managers_tmp))

        # Список записей данных по менеджерам
        # Формат списка: {ФИО менеджера, количество чатов, среднее время ответа}

        manager_quality = []
        # Проходим по таблице менеджеров
        for m in uniq_managers: # Собираем аналитику по менеджерам в таблицу
            item = [m,0,0.0]
            # Счетчик чатов
            chat_count = 0
            # Время ответа
            mid_time = 0
            for a in analysis:
                if (a[2] == m) and (a[4]>0):
                    chat_count +=1
                    mid_time +=a[4]
            if chat_count>0:
                item[1] = chat_count
                item[2] = (0 if chat_count == 0 else round(mid_time / chat_count,0))
                manager_quality.append(item)

        
        # Выводим результаты из таблицы аналитики и аналитики по менеджерам
        tmp1 = []
        for a in manager_quality:
            tmp1.append([a[0],str(a[1]),str(convert_seconds(a[2]))])
        try:
            worksheet_effi.batch_clear(['A7:C90', 'B4'])
            worksheet_effi.update_acell('B4','{:%d.%m.%Y %H:%M}'.format(datetime.now()))
            worksheet_effi.update('A7',tmp1,value_input_option='USER_ENTERED')

            worksheet_losttime.batch_clear(['A2:F230'])
            worksheet_losttime.update('A2',losttime,value_input_option='USER_ENTERED')

            worksheet_chat.batch_clear(['A2:E200'])
            worksheet_chat.update('A2',analysis,value_input_option='USER_ENTERED')
        except:
            logging.error('Ошибка обновления таблиц Google')

     """


if __name__ == '__main__':
    try:
        get_managers()
        Thread(target=update_conversations).start()
        main()
    except Exception as e:
        stop_update = True
        logging.error(f'00. Возникла ошибка {e}, перезапуск.')        
        time.sleep(10)
        get_managers()
        Thread(target=update_conversations).start()
        main()
    
