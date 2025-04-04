"""Functions to retrieve, clean, and visualise triathlon race data"""

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


def to_timedelta(df):
    """Returns leg columns converted to timedelta"""
    return df.astype({"Swim": "timedelta64[s]",
                      "T1": "timedelta64[s]",
                      "Bike": "timedelta64[s]",
                      "T2": "timedelta64[s]",
                      "Run": "timedelta64[s]",
                      "Total": "timedelta64[s]"})


def get_histograms(df, title):
    """Provides histograms for each leg of given race"""
    import matplotlib.pyplot as plt
    import random

    # Convert to timedelta and then seconds
    df_timedelta = to_timedelta(df)
    df_seconds = df_timedelta.apply(lambda col: col.dt.total_seconds() if col.dtype == "timedelta64[s]" else col)
    
    fig, ax = plt.subplots(nrows=6, ncols=1, figsize=(8, 12))
    columns = ["Swim", "T1", "Bike", "T2", "Run", "Total"]
    for i, column in enumerate(columns):
        # Drop outliers
        Q1 = df_seconds[column].quantile(0.25)
        Q3 = df_seconds[column].quantile(0.75)
        IQR = Q3 - Q1
        df_seconds[column] = df_seconds[column][(df_seconds[column] > (Q1 - 1.5*IQR))
                                                & (df_seconds[column] < (Q3 + 1.5*IQR))]

        # Use Freedman-Diaconis rule to determine number of bins
        bw = 2 * IQR * len(df_seconds)**(-1/3)
        bins = int((df_seconds[column].max() - df_seconds[column].min()) / bw)
        # Adjust
        bins = int(3 * bins)

        # Generate random colors for each chart
        color = (random.random(), random.random(), random.random())

        # Plot histogram for each leg
        ax[i].hist(
            df_seconds[column],
            bins=bins,
            color=color
            )
        
        # Convert x-axis labels from seconds to minutes for non-transition legs
        if column != "T1" and column != "T2":
            interval = 60
            xmax = df_seconds[column].max() + interval
            xmin = df_seconds[column].min() - interval
            count = int((xmax - xmin) / interval)  # Determine optimal number of ticks
            xmin_pos = int(xmin / interval) + 1
            # Determine positions of each tick
            positions = [x * interval for x in range(xmin_pos, xmin_pos + count + 1)]
            if xmax < 6060:
                if len(positions) > 75:  # Label every seven ticks if tons of ticks
                    labels = tick_setter(7, positions)
                elif len(positions) > 50:  # Label every five ticks if many ticks
                    labels = tick_setter(5, positions)
                elif len(positions) > 20:  # Label every three ticks if too many ticks
                    labels = tick_setter(3, positions)
                elif len(positions) > 10: # Two for moderate number of ticks
                    labels = tick_setter(2, positions)
                else:  # Otherwise label every tick
                    labels = tick_setter(1, positions)
            else:  # Means dealing w/ 3 digit tickers
                if len(positions) > 75:  # Label every ten ticks if tons of ticks
                    labels = tick_setter(10, positions)
                elif len(positions) > 50:  # Label every seven ticks if many ticks
                    labels = tick_setter(7, positions)
                elif len(positions) > 20:  # Label every five ticks if too many ticks
                    labels = tick_setter(5, positions)
                elif len(positions) > 10: # Three for moderate number of ticks
                    labels = tick_setter(3, positions)
                else:  # Otherwise label every tick
                    labels = tick_setter(1, positions)
            #fig.autofmt_xdate()
            ax[i].set_xticks(positions)
            ax[i].set_xticklabels(labels)
            ax[i].set_xlabel("Minutes")
        else:
            ax[i].set_xlabel("Seconds")
        
        ax[i].set_title(column)
        ax[i].set_ylabel("Athlete Count")

    fig.suptitle(title)

    plt.tight_layout()
    plt.show()


def tick_setter(spacing, positions):
    """Fetches tick spacing"""
    return [f"{x // 60}:{x % 60:02}" if i % spacing == 0 else " " for i, x in enumerate(positions)]


def get_position(df):
    """Gets position data for each competitor after each leg in the race"""
    # Make a copy of data and drop rows without complete leg splits
    df = df.copy()
    df.dropna(inplace=True)
    
    # Convert splits to timedelta
    df = to_timedelta(df)
    
    # For each split column calculate the athlete's position in the race after that split 
    columns = ["Swim", "T1", "Bike", "T2", "Run", "Total"]
    for i, column in enumerate(columns):
        # Find their cumulative time at that point in time
        if f"Overall Time {i}" in df.columns:
            df[f"Overall Time {i+1}"] = df[column] + df[f"Overall Time {i}"]
        else:
            df[f"Overall Time {i+1}"] = df[column]
        # Then sort and find their place at that point in the race
        df.sort_values(by=f"Overall Time {i+1}", inplace=True)
        df.reset_index(drop=True, inplace=True)
        df[f"Position {i+1}"] = df.index + 1
        # Determine gap time to leader
        df[f"Gap Time {i+1}"] = df[f"Overall Time {i+1}"] - df[f"Overall Time {i+1}"].min()
        df[f"Gap Time {i+1}"] = df[f"Gap Time {i+1}"].dt.total_seconds().astype(int)
    # Do same calculation for final time which was already provided
    df["Final Time"] = df.pop("Total")
    df.sort_values(by="Final Time", inplace=True)
    df.reset_index(drop=True, inplace=True)
    df["Final Position"] = df.index + 1
    df["Final Gap"] = df["Final Time"] - df[f"Final Time"].min()
    df["Final Gap"] = df["Final Gap"].dt.total_seconds().astype(int)

    # Drop split columns 
    df.drop(columns=["Swim", "T1", "Bike", "T2", "Run"], inplace=True)

    return df


def get_place_chart(df, competitor):
    """Creates chart that shows how places changed throughout the race for a given competitor"""
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker

    # Set up overall chart
    fig, ax = plt.subplots()
    df = df.copy()
    df.set_index("Name", inplace=True)
    positions = ["Position 1", "Position 2", "Position 3", "Position 4", "Final Position"]
    gaps = ["Gap Time 1", "Gap Time 2", "Gap Time 3", "Gap Time 4", "Final Gap"]

    # For each split, normalize the gaps such that the position matches the gap time
    for i, gap in enumerate(gaps):
        position = df[positions[i]].loc[df.index == competitor].values[0]
        df[gap] = (df[gap] - df[gap].min()) / (df[gap].max() - df[gap].min())
        if df[gap].loc[df.index == competitor].values[0] == 0:
            # If leading, scale competitor to correct position and last place to last position
            df[gap] = df[gap] * len(df) + position
        else:
            scale = position / df[gap].loc[df.index == competitor]
            df[gap] = scale.iloc[0] * df[gap]

    # Transpose so that each column is on the x-axis and each competitor is on the y-axis
    df[gaps].loc[df.index != competitor].T.plot(ax=ax, style="o-", color="lightgrey", legend=None)

    # Graph the competitor's chart
    df[gaps].loc[df.index == competitor].T.plot(ax=ax, style="bo-", legend=None)

    # Determine minimum and maximum y-axis
    comp_loc = df[positions].loc[df.index == competitor]
    min_pos = comp_loc.min().min()
    max_pos = comp_loc.max().max()
    if min_pos < 5:
        ax.set_ylim(min_pos, max_pos + 5)
    elif max_pos > len(df) - 5:
        ax.set_ylim(min_pos - 5, max_pos)
    else:
        ax.set_ylim(min_pos - 5, max_pos + 5)
    
    # Calculate position changes
    pos_t1 = comp_loc["Position 1"].values[0] - comp_loc["Position 2"].values[0]
    pos_bike = comp_loc["Position 2"].values[0] - comp_loc["Position 3"].values[0]
    pos_t2 = comp_loc["Position 3"].values[0] - comp_loc["Position 4"].values[0]
    pos_r = comp_loc["Position 4"].values[0] - comp_loc["Final Position"].values[0]
    positions = ["Run", f"T1 ({pos_t1})", f"Bike ({pos_bike})", f"T2 ({pos_t2})", f"Swim ({pos_r})"]

    # Set up title and y-axis label
    ax.set_title(competitor)
    ax.set_ylabel("Place")

    # Turn off extra ticks
    ax.set_xticks(range(len(positions)))
    ax.set_xticklabels(positions)

    # Change label colors based on positions
    labels = ax.get_xticklabels()
    pos_values = [pos_t1, pos_bike, pos_t2, pos_r]
    change_label(labels, pos_values)

    # Turn on grid and put top positions at top
    ax.grid()
    ax.invert_yaxis()

    # Ensure y-axis tickers are integers
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    
    plt.show()


def change_label(labels, values):
    """Changes label green if improve place, red if lose places"""
    for i, label in enumerate(labels[1:]):
        if values[i] > 0:
            label.set_color("green")
        elif values[i] < 0:
            label.set_color("red")


def lin_reg(df, leg):
    """Plots linear regression between a leg in race and total time"""
    import numpy as np
    import random
    from sklearn.linear_model import LinearRegression
    from sklearn.feature_selection import r_regression
    import matplotlib.pyplot as plt

    # Assign data 
    x = np.array(df[leg].dt.total_seconds())
    y = np.array(df.Total.dt.total_seconds())
    color = (random.random(), random.random(), random.random())  # Random color

    # Train model
    model = LinearRegression()
    model.fit(x[:,np.newaxis], y)

    # Create line of best fit
    xfit = np.linspace(x.min() - 100, x.max() + 100, len(x))
    yfit = model.predict(xfit[:,np.newaxis])

    # Plot line of best fit and data
    plt.plot(xfit, yfit, color=color,
             label=f"{leg} Correlation: {r_regression(x[:,np.newaxis], y)[0]:.2f}")
    plt.plot(x, y, 'o', color=color)


def race_leg_imp(df, race_name):
    """Calculates and plots leg importance for each leg of triathlon race"""
    import matplotlib.pyplot as plt

    # Convert and clean data
    df = to_timedelta(df)
    df.dropna(inplace=True)

    # Calculate and plot regression for each leg
    legs = ["Run", "T1", "Bike", "T2", "Swim"]
    for leg in legs:
        lin_reg(df, leg)

    # Show legend and plot labels
    plt.legend();
    ax = plt.gca()
    ax.set_title(f"{race_name} Leg Importance")
    ax.set_xlabel("Leg Time (seconds)")
    ax.set_ylabel("Total Time (seconds)")
    plt.show()