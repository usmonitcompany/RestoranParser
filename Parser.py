import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from time import sleep
import json
from tqdm import tqdm
from tkinter import Tk
from tkinter.filedialog import askopenfile
import os
import requests
from simple_term_menu import TerminalMenu
from datetime import datetime
import pandas as pd
from ftplib import FTP
import re



class GetPics:
  def __init__(self, validation_class):
    with askopenfile(mode='r', filetypes=[('Json', '*.json')]) as file:
      if file is not None:
        data = json.load(file)

      else:
        print("% Invalid File")

        sys.exit(0)

    self.data = data
    self.val_class = validation_class

    picture_sizes_input = "1600-1200".split("-") # str(input("Width and Height -> Format (w-h)  ")).split("-")
    self.picture_sizes = {"x": picture_sizes_input[0], "y": picture_sizes_input[1]}
    self.pictures_totalNumber = self.getTotalSizePics()
    self.progress_bar = tqdm(range(self.pictures_totalNumber), desc="Progress", colour="green")

    self.directory = self.mkdir_(os.getcwd(), f"pictures {datetime.now().strftime('%d_%m_%Y %H-%M-%S')}")

  def parse_pictures(self):
    for rest_name, rest_data in self.data.items():
        restoran_path = self.mkdir_(self.directory, rest_name)

        for category_name, category_data in rest_data.items():
            category_name = self.val_class.text_validator(category_name)
            category_path = self.mkdir_(restoran_path, category_name)

            for it in category_data:
                try:
                  # print(it["name"], it["picture"])
                  self.get_soloPic(it["picture"].replace("jpeg", "jpg"), self.val_class.text_validator(it["name"]), category_path)

                except Exception as e:
                  pass

                self.progress_bar.update(1)
                self.progress_bar.refresh()

    self.progress_bar.close()

    return self.directory, self.pictures_totalNumber

  def get_soloPic(self, picture_url, picture_name, category_path):
    img_data = requests.get(self.make_picUrl(picture_url)).content

    with open(f"{os.path.join(category_path, picture_name)}.jpg", "wb") as handler:
      handler.write(img_data)

    sleep(0.5)

  def make_picUrl(self, picture_url):
    return f"https://eda.yandex{picture_url.replace('{w}', self.picture_sizes['x']).replace('{h}', self.picture_sizes['y'])}"


  def mkdir_(self, path, dir_name):
    return_path = os.path.join(path, dir_name)
    os.mkdir(return_path)

    return return_path

  def getTotalSizePics(self):
    return_value = 0

    for i in self.data.values():
      for f in i.values():
        return_value += len(f)

    return return_value


class Urls:
  def __init__(self):
    with askopenfile(mode='r', filetypes=[('Text', '*.txt')]) as file:
      if file is not None:
        urls = file.readlines()

      else:
        print("% Invalid File")

        sys.exit(0)

    self.urls = urls
    self.urls_list = self.url_decode()

  def url_decode(self):
    decoded_urls = []

    for url in self.urls:
      splitted_url = url.split("placeSlug=")[1]
      if ("&" in splitted_url):
        splitted_url = splitted_url.split("&")[0]

      decoded_urls.append(splitted_url.replace("\n", ""))

    return decoded_urls


class SaveToExcel:
  def __init__(self, results, dir_path):
    self.results = results

    self.data_frames = []
    self.data_frames_category_names = []
    self.headers = ["name", "description", "price", "weight", "calories", "carbohydrates", "fats",
                    "proteins", "picture"]

    for restoran_name, restoran_data in results.items():
      for category_name, category_data in restoran_data.items():
        self.data_frames.append(pd.DataFrame(self.createDF(category_data), columns=self.headers))
        self.data_frames_category_names.append(category_name)

      with pd.ExcelWriter(os.path.join(dir_path, f"{restoran_name}.xlsx")) as writer:
        for index, data_frame in enumerate(self.data_frames):
          data_frame.to_excel(writer, sheet_name=self.data_frames_category_names[index], index=False)

      self.data_frames = []
      self.data_frames_category_names = []

  def createDF(self, global_data):
    data = []
    for index, item in enumerate(global_data):
      column = []
      if ("nutrients_detailed" in item.keys()):
        cp_nutrd = item["nutrients_detailed"]
        for key, value in cp_nutrd.items():
          item[key] = value

        del item["nutrients_detailed"]

      for header in self.headers:
        try:
          column.append(item[header])

        except Exception as e:
          column.append("-")

      data.append(column)

    return data


class SaveToCsv:
  def __init__(self, results, dir_path, validation_class):
    self.results = results

    self.data_frame = {"name": [], "description": [], "price": [], "category": [], "image": []}
    self.val_class = validation_class

    for restoran_name, restoran_data in results.items():
      for category_name, category_data in restoran_data.items():
        self.createDF(category_data, category_name, restoran_name)

      pd.DataFrame(self.data_frame).to_csv(os.path.join(dir_path, f"{restoran_name}.csv"), index=False)


  def createDF(self, global_data, category_name, restoran_name):
    for item in global_data:
      for key in self.data_frame.keys():
        try:
          if (key == "category"):
            self.data_frame["category"].append(category_name)

          elif (key == "image"):
            if ("picture" in item.keys()):
              self.data_frame[key].append(f"https://bvh.usmonit.com/public-images/{restoran_name}/{self.val_class.text_validator(category_name)}/{self.val_class.text_validator(item['name'])}.jpg")

            else:
              raise Exception("No Picture", "picture")

          else:
            self.data_frame[key].append(item[key])

        except Exception as e:
          if (e.args[1] == "picture"):
            self.data_frame[key].append(f"https://bvh.usmonit.com/public-images/none-picture.jpg")



class Parser:
  def __init__(self, browser, res_list, validation_class):
    self.val_class = validation_class
    self.browser = browser
    self.restoran_list = res_list

    self.fetch_script_origin = open("fetch_script.txt", "r").read()
    self.fetch_script = ""


  def run(self):
    return_data = {}

    for it in tqdm(range(len(self.restoran_list)), bar_format="{l_bar}{bar:20}|", desc ="Progress", colour="green"):
      self.refactor_Fetch(self.restoran_list[it])

      rest_data = self.parse()
      return_data[self.restoran_list[it]] = rest_data

      sleep(2)

    return return_data

  def parse(self):
    fetch_result = self.browser.execute_script(self.fetch_script)

    data = {}
    for category in fetch_result["payload"]["categories"]:
      cart_category = []

      for item in category["items"]:
          data_toFind = {"name": "name", "description": "description", "price": "price",
                                "weight": "weight", "nutrients_detailed": {"calories": ["nutrients_detailed", "calories", "value"],
                                                                                 "carbohydrates": ["nutrients_detailed", "carbohydrates", "value"],
                                                                                 "fats": ["nutrients_detailed", "fats", "value"],
                                                                                 "proteins": ["nutrients_detailed", "proteins", "value"]},
                         "picture": ["picture", "uri"]}

          flag = self.val_class.blocked_content(item["name"], item["description"])

          item_data = {}
          for key, value in data_toFind.items():
            try:
              if (type(value) == str):
                item_data[key] = item[value]

              elif (type(value) == list):
                item_data[key] = self.getCurrent_it(item, value)

              elif(type(value) == dict):
                buf_dict = {}
                for key_it, value_it in value.items():
                  buf_dict[key_it] = self.getCurrent_it(item, value_it)

                  item_data[key] = buf_dict

            except:
              pass

          if (flag == True):
            # item_data["name"] = self.val_class.text_validator(item_data["name"])

            cart_category.append(item_data)

      if (len(cart_category) != 0):
        data[category["name"]] = cart_category   # self.val_class.text_validator(


    return data


  def getCurrent_it(self, item, value):
    current_it_value = item
    for it in value:
      current_it_value = current_it_value[it]

    return current_it_value

  def refactor_Fetch(self, rest_name):
    self.fetch_script = self.fetch_script_origin.replace("name", rest_name)


class Validation:
  def __init__(self):
    self.blocked_list = ['свин', 'пив', 'водк', 'вин', 'шампанск', 'ром', 'виск', 'бренд', 'текил', 'джин', 'ликер', 'коньяк', 'вермут', 'портвейн', 'абсент', 'сидр', 'медовух', 'мескаль', 'грапп', 'сак', 'вермут', 'пунш', 'джек дэниелс', 'женев', 'кальвадос', 'зернохранилищ', 'бурбон', 'мартини', 'самбук', 'шнапс', 'pivo', 'vodka', 'vino', 'shampanskoe', 'rom', 'whisky', 'brendi', 'tekila', 'dzhin', 'liqery', "kon'yak", 'vermut', 'portveyn', 'absent', 'sidr', 'medovukha', "mezkal'", 'grappa', 'sake', 'vermut', 'punsh', 'dzhek deniels', 'zheneva', "kal'vados", 'zernokhranilishche', 'burbon', 'martini', 'sambuka', 'shnaps', 'beer', 'vodka', 'wine', 'champagne', 'rum', 'whisky', 'brandy', 'tequila', 'gin', 'liqueurs', 'cognac', 'vermouth', 'port wine', 'absinthe', 'cider', 'mead', 'mezcal', 'grappa', 'sake', 'vermouth', 'punch', 'jack daniels', 'geneva', 'calvados', 'granary', 'bourbon', 'martini', 'sambuca', 'schnapps']

    self.russian_to_english = {
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z',
    'И': 'I', 'Й': 'J', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R',
    'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'C', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
    'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z',
    'и': 'i', 'й': 'j', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
    'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'}

  def blocked_content(self, name, description):
    name_ = name.lower()
    desc_ = description.lower()

    for blocked_word in self.blocked_list:
      if (blocked_word in name_ or blocked_word in desc_):
          return False

    return True

  def dataValidation(self, data):
    return data.replace("\xa0", "")\
      .replace("'", '"')

  def text_validator(self, text):
    result = re.sub(r"[^\w\s]", "", text).replace(" ", "_")

    return_result = ""
    for char in result:
      if char in self.russian_to_english:
        return_result += self.russian_to_english[char]

      else:
        return_result += char

    return return_result


class UploadFTP:
  def __init__(self, picture_directory, pictures_totalNumber):
    self.ftp_host = '195.2.73.74'
    self.ftp_user = 'ilya'
    self.ftp_pass = '5Ck50A0SS9d5x1hW'

    self.local_folder = ""
    self.pic_dir = picture_directory

    self.progress_bar = tqdm(range(pictures_totalNumber), desc="Uploading", colour="green")
    self.connect()

  def connect(self):
    with FTP(self.ftp_host) as ftp:
      ftp.login(user=self.ftp_user, passwd=self.ftp_pass)

      for folder in os.listdir(self.pic_dir):
        self.uploader(ftp, os.path.join(self.pic_dir, folder), folder)

      self.progress_bar.close()

  def uploader(self, ftp, local_folder, remote_folder):
    try:
        ftp.mkd(remote_folder)

        for item in os.listdir(local_folder):
            local_path = os.path.join(local_folder, item)
            remote_path = os.path.join(remote_folder, item)

            if os.path.isfile(local_path):
                with open(local_path, 'rb') as f:
                  ftp.storbinary('STOR ' + remote_path, f)

            elif os.path.isdir(local_path):
                self.uploader(ftp, local_path, remote_path)

            self.progress_bar.update(1)
            self.progress_bar.refresh()

    except Exception as e:
        print(f"Error uploading folder: {e}")

def saving(results, type, validation_class):
  path = os.path.join(os.getcwd(), f"Data {datetime.now().strftime('%d_%m_%Y %H-%M-%S')}")
  os.mkdir(path)

  with open(os.path.join(path, "results.json"), "w") as file:
    file.write(json.dumps(results, indent=4, ensure_ascii=False))

  SaveToExcel(results, path) if (type == "excel") else SaveToCsv(results, path, validation_class)


menu_options = ["Dishes Parsing (urls_file)", "Download Pictures (results_json)", "Quit"]

mainMenu = TerminalMenu(menu_options)
optionIndex = mainMenu.show()

validation_class = Validation()

if (optionIndex == 0):
  type_menu_options = ["Excel", "Csv"]

  typeMenu = TerminalMenu(type_menu_options)
  type_optionIndex = typeMenu.show()

  print("% Preparing")

  chrome_options = webdriver.ChromeOptions()
  chrome_options.add_experimental_option("detach", True)
  chrome_options.add_argument("--headless")

  chrome_service = Service("chromedriver")

  browser = webdriver.Chrome(options=chrome_options, service=chrome_service)
  browser.get("https://eda.yandex.ru/")

  Tk().withdraw()
  restorans = Urls()

  parser = Parser(browser, restorans.urls_list, validation_class)
  results = parser.run()

  saving(results, "excel" if (type_optionIndex == 0) else "csv", validation_class)

elif (optionIndex == 1):
  print("% Starting")
  Tk().withdraw()

  clss = GetPics(validation_class)
  pic_dir, pics_nSize = clss.parse_pictures()

  pictures_store_menu_options = ["Upload (pictures) on Server", "Quit"]

  pictures_storeMenu = TerminalMenu(pictures_store_menu_options)
  pictures_store_optionIndex = pictures_storeMenu.show()

  if (pictures_store_optionIndex == 0):
    UploadFTP(pic_dir, pics_nSize)

else:
  pass


print("% Finished")