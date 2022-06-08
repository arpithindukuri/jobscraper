from collections import OrderedDict
import json
import re
import requests
from thefuzz import fuzz
from bs4 import BeautifulSoup
from selenium import webdriver
import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0", "Accept-Encoding": "gzip, deflate",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "DNT": "1", "Connection": "close", "Upgrade-Insecure-Requests": "1"}

url = 'https://ca.indeed.com/'
job_title = 'Software Co-op'
location = 'Canada'


class WordFrequencyDictionary:
    def __init__(self) -> None:
        self.dict: OrderedDict[str, int] = OrderedDict()

    def add_word(self, word) -> None:
        if word not in self.dict:
            self.dict[word] = 1
        else:
            self.dict[word] += 1

    def sort_dict_by_freq(self) -> None:
        sorted_dict = {k: v for k, v in sorted(
            self.dict.items(), key=lambda item: item[1])}
        self.dict = OrderedDict(sorted_dict)

    def sort_dict_keywords_to_top(self) -> None:
        keywords: list[str] = []
        with open('keywords.txt', 'r') as f:
            keywords = f.readlines()

        i = 0
        keys = list(self.dict.keys())
        while i < len(keys):
            for keyword in keywords:
                if (fuzz.partial_ratio(keys[i], keyword) > 95):
                    self.dict.move_to_end(key=keys[i], last=False)
                    break
            i += 1
            if (i % 100 == 0):
                print(f'sorted: {i}')

    def write_to_file(self) -> None:
        with open('freqs.json', 'w', encoding='utf-8') as f:
            json.dump(self.dict, f, ensure_ascii=False,
                      indent=4)

    def default(self):
        return


class Job:
    def __init__(self, name, location, description) -> None:
        self.name: str = name
        self.location: str = location
        self.description: str = description

    def get_description_words(self):
        lower_str = self.description.lower()
        stripped_str = lower_str.strip()
        simplified_str = re.sub("[,!()/:;]", ' ', stripped_str)
        words = simplified_str.split()
        return words

    def __str__(self) -> str:
        return f'{{ name: {self.name}, location: {self.location}, description: {self.description} }}'


# subclass JSONEncoder
class JobEncoder(json.JSONEncoder):
    def default(self, o):
        return o.__dict__


class JobList:
    def __init__(self) -> None:
        self.jobs: list[Job] = []
        self.freqs = WordFrequencyDictionary()

    def add_job(self, job: Job):
        self.jobs.append(job)
        for word in job.get_description_words():
            scraper.joblist.freqs.add_word(word)
        print(f"added job: {job}")

    def write_to_file(self) -> None:
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(self.jobs, f, ensure_ascii=False,
                      indent=4, cls=JobEncoder)

    def read_from_file(self) -> None:
        self.jobs = []
        with open('data.json', 'r', encoding='utf-8') as f:
            jobs = json.load(f)
            for job in jobs:
                self.add_job(
                    Job(job["name"], job["location"], job["description"]))


class Scraper:
    def __init__(self) -> None:
        self.driver = None
        self.joblist = JobList()

    def init_driver(self):
        self.driver = webdriver.Edge()

    def start_search(self):
        self.driver.get(url)

        job_title_input_el = self.driver.find_element(
            by=By.XPATH, value='//*[@id="text-input-what"]')

        job_loc_input_el = self.driver.find_element(
            by=By.XPATH, value='//*[@id="text-input-where"]')

        search_button_el = self.driver.find_element(
            by=By.XPATH, value='//*[@id="jobsearch"]/button')

        search_button2_el = self.driver.find_element(
            by=By.XPATH, value='//*[@id="jobsearch"]/button')

        time.sleep(0.1)

        job_title_input_el.send_keys(job_title)
        time.sleep(0.1)

        job_loc_input_el.send_keys(Keys.CONTROL + "a")
        time.sleep(0.1)

        job_loc_input_el.send_keys(Keys.DELETE)
        time.sleep(0.1)

        job_loc_input_el.send_keys(location)
        time.sleep(0.1)

        self.driver.find_element(
            by=By.XPATH, value='/html/body/div').click()
        time.sleep(0.1)

        try:
            search_button_el.click()
        except:
            search_button2_el.click()
        time.sleep(1.5)

    def scrape_current_page(self):
        jobs_cards = self.driver.find_elements(
            by=By.CLASS_NAME, value='jcs-JobTitle')

        for card in jobs_cards:
            resp = requests.get(card.get_attribute("href"), headers=HEADERS)
            content = BeautifulSoup(resp.content, 'lxml')

            try:
                name = content.find(
                    "h1", {"class": "jobsearch-JobInfoHeader-title"}).get_text().strip()
                loc = self.driver.find_element(
                    by=By.CLASS_NAME, value='companyLocation').text
                desc = content.find(
                    "div", {"id": "jobDescriptionText"}).get_text().strip()

                self.joblist.add_job(Job(name, loc, desc))

            except Exception:
                continue

    def go_to_next_page(self):
        new_url = self.driver.find_element(
            by=By.XPATH, value='/html/body/table[2]/tbody/tr/td/table/tbody/tr/td[1]/nav/div/ul/li[last()]/a').get_attribute("href")

        self.driver.get(new_url)

        time.sleep(1)


if __name__ == '__main__':
    scraper = Scraper()
    scraper.init_driver()
    scraper.start_search()

    for i in range(9):
        scraper.scrape_current_page()
        scraper.go_to_next_page()
    scraper.scrape_current_page()

    scraper.joblist.write_to_file()

    # scraper.joblist.read_from_file()
    scraper.joblist.freqs.sort_dict_by_freq()
    scraper.joblist.freqs.sort_dict_keywords_to_top()

    scraper.joblist.freqs.write_to_file()

    scraper.driver.close()
