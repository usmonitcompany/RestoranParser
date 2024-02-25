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



class GetPics:
  def __init__(self):
    with askopenfile(mode='r', filetypes=[('Json', '*.json')]) as file:
      if file is not None:
        data = json.load(file)

      else:
        print("% Invalid File")

        sys.exit(0)

    self.data = data

    picture_sizes_input = str(input("Width and Height -> Format (w-h)  ")).split("-")
    self.picture_sizes = {"x": picture_sizes_input[0], "y": picture_sizes_input[1]}
    self.progress_bar = tqdm(range(self.getTotalSizePics()), desc="Progress", colour="green")

    self.directory = self.mkdir_(os.getcwd(), f"pictures {datetime.now().strftime('%d_%m_%Y %H-%M-%S')}")

  def parse_pictures(self):
    for rest_name, rest_data in self.data.items():
        restoran_path = self.mkdir_(self.directory, rest_name)

        for category_name, category_data in rest_data.items():
            category_path = self.mkdir_(restoran_path, category_name)

            for it in category_data:
                try:
                  # print(it["name"], it["picture"])
                  self.get_soloPic(it["picture"], it["name"], category_path)

                except Exception as e:
                  pass

                self.progress_bar.update(1)
                self.progress_bar.refresh()

    self.progress_bar.close()

  def get_soloPic(self, picture_url, picture_name, category_path):
    img_data = requests.get(self.make_picUrl(picture_url)).content

    with open(f"{os.path.join(category_path, picture_name)}.jpeg", "wb") as handler:
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


class Parser:
  def __init__(self, browser, res_list):
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

          cart_category.append(item_data)

      if (len(cart_category) != 0):
        data[category["name"]] = cart_category


    return data


  def getCurrent_it(self, item, value):
    current_it_value = item
    for it in value:
      current_it_value = current_it_value[it]

    return current_it_value

  def refactor_Fetch(self, rest_name):
    self.fetch_script = self.fetch_script_origin.replace("name", rest_name)


def dataValidation(data):
  return data.replace("\xa0", "")\
    .replace("'", '"')

def saving(results):
  path = os.path.join(os.getcwd(), f"Data {datetime.now().strftime('%d_%m_%Y %H-%M-%S')}")
  os.mkdir(path)

  with open(os.path.join(path, "results.json"), "w") as file:
    file.write(json.dumps(results, indent=4, ensure_ascii=False))

  SaveToExcel(results, path)


menu_options = ["Dishes Parsing (urls_file)", "Download Pictures (results_json)", "Quit"]

mainMenu = TerminalMenu(menu_options)
optionIndex = mainMenu.show()


Tk().withdraw()


if (optionIndex == 0):
  print("% Preparing")

  chrome_options = webdriver.ChromeOptions()
  chrome_options.add_experimental_option("detach", True)
  chrome_options.add_argument("--headless")

  chrome_service = Service("chromedriver")

  browser = webdriver.Chrome(options=chrome_options, service=chrome_service)
  browser.get("https://eda.yandex.ru/")


  restorans = Urls()

  parser = Parser(browser, restorans.urls_list)
  results = parser.run()

  saving(results)

elif (optionIndex == 1):
  print("% Starting")

  clss = GetPics()
  clss.parse_pictures()

else:
  pass


print("% Finished")