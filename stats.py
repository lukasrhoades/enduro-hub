def get_data_active(race):
    """Grabs race data for all participants in a triathlon race from Active Results"""
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    import time
    import re
    import pandas as pd

    url = f"https://resultscui.active.com/events/{race}"

    # Initialize browser configured for speed
    options = Options()
    options.add_argument("--headless=new")

    browser = webdriver.Chrome(options=options)

    # Go to results website
    browser.get(url)

    time.sleep(3)

    # Expand view
    dropdown = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[text()='Top 10']"))
        )
    dropdown.click()

    t100 = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[text()='Top 100']"))
        )
    t100.click()
    
    # Collect ALL participant results
    while True:
        try:
            expand = WebDriverWait(browser, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Load more']/parent::*"))
                )
            expand.click()
        except:
            break

    time.sleep(1)

    competitors = browser.find_elements(By.CLASS_NAME, "event-home__item")

    # Collect links for all competitors
    urls = []
    for competitor in competitors:
        link = competitor.find_element(By.CSS_SELECTOR, "a[href*='/participants/']")
        href = link.get_attribute("href")
        urls.append(href)

    # Collect data for each competitor
    data = pd.DataFrame()
    for url in urls:
        browser.get(url)
        name = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "personal-info__name"))
            ).text
        bio = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "personal-info__detail"))
            ).text
        gender = bio.split("|")[0].strip()
        age = re.findall(r"\d+", bio)[0]
        chip = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Chip time')]/following-sibling::div//span"))
            ).text
        try:
            swim = WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.XPATH, get_xpath_active("leg", 1)))
                ).text
            bike = WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.XPATH, get_xpath_active("leg", 2)))
                ).text
            run = WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.XPATH, get_xpath_active("leg", 3)))
                ).text
            t1 = WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.XPATH, get_xpath_active("transition", 1)))
                ).text
            t2 = WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.XPATH, get_xpath_active("transition", 2)))
                ).text
        except:
            temp = pd.DataFrame(
                {"Name": name,
                "Gender": gender,
                "Age": age,
                "Total": chip},
                index=[0]
                )
        else:
            temp = pd.DataFrame(
                {"Name": name,
                "Gender": gender,
                "Age": age,
                "Swim": swim,
                "T1": t1,
                "Bike": bike,
                "T2": t2,
                "Run": run,
                "Total": chip},
                index=[0]
                )
        
        if data.empty:
            data = temp
        else:
            data = pd.concat([data, temp]).reset_index(drop=True)
    
    browser.quit()
    return data


def get_xpath_active(type, i):
    """Fetches XPATH for desired split"""
    if type == "leg":
        return f"""
        //ul[@class='summary-result-list']/li[{i}]
        //span[contains(text(), 'Split time')]/../../div[contains(@class, 'result-cell-content')]
        """
    elif type == "transition":
        return f"""
        //ul[@class='transition-result-list']/li[{i}]
        //div[@class='transition-stage-result__split-time']
        """