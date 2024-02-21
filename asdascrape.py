import selenium
import time
import traceback
import re
import pandas as pd
import numpy as np
from collections import Counter
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException


def collect_nutrittion(product_urls,csv_name):
    dataframes_list = []
    for p in product_urls:

        driver.get(p)

        #  Get all the information elements for the product
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "pdp-description-reviews__nutrition-cell"))
            )
            element_present = True
        except TimeoutException:
            element_present = False

        if element_present:

            title = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "pdp-main-details__title"))
            )
            print(title.text)
            categories = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".asda-link.asda-link--primary.breadcrumb__link"))
            )
            
            weight = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "pdp-main-details__weight"))
            )
            
            cost = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "pdp-main-details__price"))
            )
            print(cost.text)
            nutrition = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "pdp-description-reviews__nutrition-table-cntr"))
            )
            
            # Extracting catergories

            cat_text = [c.text for c in categories]
            cat = []
            for text in cat_text:
                parts = text.replace("breadcrumb", "").strip().split('/')
                titles = [part.strip() for part in parts if part.strip()]
                cat.extend(titles)
            cat = cat[:2]


            #  Extracting nutrition data
            for i in nutrition:
                nutdf1 = i.text.strip().split("\n")
                nutdf1 = nutdf1[1:]

                # exception case where of which saturates are on different lines
                for i in range(len(nutdf1)- 2, -1, -1):  #  Start from the second-last item down to the first item
                    if nutdf1[i] == 'of which' and 'Saturates' in nutdf1[i + 1]:
                        nutdf1[i] += ' ' + nutdf1[i + 1]  # Combine the elements
                        nutdf1.pop(i + 1)  # Remove the now redundant 'Saturates' element

                # exception case for energy readings with /
                if nutdf1[0].count('/') == 2:
                    parts = nutdf1[0].split('/')  
                    # Extract and format the first two parts as 'Energy XXXkJ' and 'XXXkcal'
                    energy_part = parts[0].strip()  
                    kcal_part = parts[1].split()[0] + ' '  
                    # Update the list
                    nutdf1[0] = energy_part
                    nutdf1.insert(1, kcal_part)  
                if '/' in nutdf1[0]:
                    nutdf1[0] = nutdf1[0].replace('/', '')

                nutdf2 = []

                # New titles to replace the original ones
                new_labels = ['energy kj', 'energy kcal', 'fat', 'of which saturates', 'carbohydrate', 'of which sugars', 'fibre', 'protein', 'salt']   

                # Updated regex to capture more specific details from the strings, including potential guidelines amounts.
                pattern = r"^(.*?)(<\d*\.?\d+|\d*\.?\d+|Trace)(g|kJ|kcal|µg)?( \d*%?)?"

                # Processing all items
                for i, item in enumerate(nutdf1):
                    if i < len(new_labels):  # Apply new titles for the first 8 items
                        label = new_labels[i]
                    else:  # Keep the original title for items beyond the first 8
                        match = re.match(r"^(.*?)( \d+µg \d+%?)", item)  # Match items
                        if match:
                            name, extra = match.groups()
                            label = name.strip()
                            item = f"{name}{extra}"  # Reconstruct the item with necessary parts for processing below
                        else:
                            label = item.split()[0]  # Default to using the first word as the title for unmatched patterns
                    
                    match = re.match(pattern, item)
                    if match:
                        name, amount, unit, guideline = match.groups()
                        amount_with_unit = f"{amount}{unit}" if unit else amount
                        if i >= len(new_labels):  # For items beyond the first 8, include any additional details like %RI
                            amount_with_unit += guideline if guideline else ""
                        nutdf2.append((label, amount_with_unit))


            # Creating a dataFrame from the nutrition data

            nutrition_df = pd.DataFrame(nutdf2).transpose()

            if not nutrition_df.empty:
                nutrition_df.columns = nutrition_df.iloc[0]
                nutrition_df = nutrition_df[1:]
                #nutrition_df.rename(columns=lambda x: re.sub(r'\s*\((g)\)$', '', x).lower(), inplace=True)

            # Create a dataframe from the other data

            data1 = {
                'Supermarket': "ASDA",
                'Title': title.text + " " + weight.text,
                'Cost': re.sub(r'[a-zA-Z]|\\|\n', '', cost.text),
                'Catergory': cat[0],
                'Subcatergory': cat[1]
                }
            
            title_df = pd.DataFrame([data1])
            

            # Combination of datasets

            nutrition_df.index = title_df.index

            product_data = pd.concat([title_df,nutrition_df],axis = 1)
            
            dataframes_list.append(product_data)
    
    print("finished")

    driver.quit()

    if dataframes_list:
        final_data = pd.concat(dataframes_list, ignore_index=True)
    else:
        print("No data frames to concatenate. The list is empty.")

    
    # Export to CSV
    final_data.to_csv(csv_name, index = False, encoding='utf-8-sig')
    
# Initiate firefox and access website
driver = webdriver.Firefox()
driver.get("https://groceries.asda.com/sitemap/")

# %% ################################################### Fruit, Veg & Flowers #################################################### 


# Use headless mode 
options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(options=options)
driver.get("https://groceries.asda.com/sitemap/")

# Reject cookies
reject = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, "//button[@id='onetrust-reject-all-handler']"))  
)

driver.execute_script("arguments[0].click();", reject)

# Wait for the page to load and if the dept link is there click it
try:

    # Initialize an empty list to hold all product URLs
    product_urls = []

    departmentlink = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".dept__link[href*='fruit-veg-flowers']"))  
    )

    department_url = []
    department_url.extend([department.get_attribute('href') for department in departmentlink])
    department_url.pop(-2)
    
    for d in department_url:
           
        driver.get(d)

        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "View All"))  
            )
            view_present = True
        except TimeoutException:
            view_present = False

        if view_present:
            viewall = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "View All"))  
            )

            driver.execute_script("arguments[0].click();", viewall)

        #Collect product urls
        
        # Start iterating through pages to collect product URLs
        while True:
            products = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-module-name='Product List (Global Aisle)'] .co-product__anchor,\
                                                       [data-module-name='Extra Special Fruit & Veg Department Spotlight - Produce'] .co-product__anchor"))
            )
            product_urls.extend([product.get_attribute('href') for product in products])

            try:
                # Check for the next page button and determine if it's the last page
                next_page_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".co-pagination__arrow--right"))
                )
                # Check if the next page button is disabled (if applicable)
                if 'disabled' in next_page_button.get_attribute('class'):
                    break
                else:
                    driver.execute_script("arguments[0].click();", next_page_button)
            except NoSuchElementException:
                print("Reached the last page or next page button not found.")
                break
            except TimeoutException:
                print("Timeout waiting for the next page button.")
                break

    # remove duplicates       
    product_urls = list(set(product_urls))
    
except Exception as e:
    print(f"An error occurred: {e}")
    traceback.print_exc() 
    driver.quit()



collect_nutrittion(product_urls,"testdata.csv")
# %%
# %% #################################################### Meat, Poultry & Fish ########################################################

# Use headless mode 
options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(options=options)
driver.get("https://groceries.asda.com/sitemap/")


# Reject cookies
reject = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, "//button[@id='onetrust-reject-all-handler']"))  
)

driver.execute_script("arguments[0].click();", reject)


# Wait for the page to load and if the dept link is there click it
try:
    # Initialize an empty list to hold all product URLs
    product_urls = []

    departmentlink = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".aisle__link[href*='meat-poultry-fish']"))  
    )

    department_url = []
    department_url.extend([department.get_attribute('href') for department in departmentlink])
    
    keywords = ["chicken-turkey", "beef", "bacon-sausages-gammon", "pork", "lamb", "extra-special-meat-fish", "duck-game-venison", 
                "sliced-cooked-meats", "chicken-turkey-pieces", "continental-meats-pate", "snacking-hot-dogs", "extra-special-cooked-meat", "view-all-fish"]
    
    department_url = [url for url in department_url if any(keyword in url for keyword in keywords)]
   
    for d in department_url:
           
        driver.get(d)

        #Collect product urls (1137 urls)
        
        # Start iterating through pages to collect product URLs
        while True:
            products = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-module-name='Product List (Global Aisle)'] .co-product__anchor"))
            )
            product_urls.extend([product.get_attribute('href') for product in products])

            try:
                # Check for the next page button and determine if it's the last page
                next_page_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".co-pagination__arrow--right"))
                )
                # Check if the next page button is disabled (if applicable)
                if 'disabled' in next_page_button.get_attribute('class'):
                    break
                else:
                    driver.execute_script("arguments[0].click();", next_page_button)
            except NoSuchElementException:
                print("Reached the last page or next page button not found.")
                break
            except TimeoutException:
                print("Timeout waiting for the next page button.")
                break

    # remove duplicates       
    product_urls = list(set(product_urls))
    
except Exception as e:
    print(f"An error occurred: {e}")
    traceback.print_exc() 
    driver.quit()

collect_nutrittion(product_urls,"meatdata11.csv")

# %%
# %% #################################################### Bakery ########################################################

# Use headless mode 
options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(options=options)
driver.get("https://groceries.asda.com/sitemap/")


# Reject cookies
reject = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, "//button[@id='onetrust-reject-all-handler']"))  
)

driver.execute_script("arguments[0].click();", reject)


# Wait for the page to load and if the dept link is there click it
try:
    # Initialize an empty list to hold all product URLs (1074 urls)
    product_urls = []
    
    len(product_urls)

    departmentlink = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".aisle__link[href*='bakery']"))  
    )

    department_url = []
    department_url.extend([department.get_attribute('href') for department in departmentlink])
    
    keywords = ["view-all-extra-special-bakery", "view-all-in-store-bakery", "view-all-wraps-bagels-pittas-naans", "bread-rolls", "view-all-scones-teacakes-fruit-loaves", "view-all-crumpets-muffins-pancakes", 
                "view-all-cakes", "view-all-desserts-cream-cakes", "view-all-cake-bars-slices-tarts", "view-all-croissants-brioche-on-the-go", "food-to-go-meal-deal"]
    
    # Create a regex pattern that matches any of the keywords as whole segments
    # This pattern uses word boundaries (\b) around each keyword to ensure exact matches
    pattern = r'/(' + '|'.join([re.escape(keyword) for keyword in keywords]) + r')(?=/|$)'

    department_url = [url for url in department_url if re.search(pattern, url)]

    # Manual sort exception 
    department_url.remove("https://groceries.asda.com/aisle/bakery/in-store-bakery/bread-rolls/1215686354843-1215686354846-1215686354865")
    department_url.append("https://groceries.asda.com/dept/bakery/bread-rolls/1215686354843-1215686354847")

    for d in department_url:
           
        driver.get(d)

        #Collect product urls 
        
        # Start iterating through pages to collect product URLs
        while True:
            products = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-module-name='Product List (Global Aisle)'] .co-product__anchor,\
                                                                        [data-module-name='Food To Go Meal Deal - Sandwiches Spotlight'] .co-product__anchor,\
                                                                        [data-module-name='Food To Go Meal Deal - Salad & Sushi Spotlight'] .co-product__anchor,\
                                                                        [data-module-name='Food To Go Meal Deal - Snacks Spotlight'] .co-product__anchor,\
                                                                        [data-module-name='Food To Go Meal Deal - Sweet Treat Spotlight'] .co-product__anchor,\
                                                                        [data-module-name='Sandwich Fillers Spotlight'] .co-product__anchor"))
            )
            product_urls.extend([product.get_attribute('href') for product in products])

            try:
                # Check for the next page button and determine if it's the last page
                next_page_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".co-pagination__arrow--right"))
                )
                # Check if the next page button is disabled (if applicable)
                if 'disabled' in next_page_button.get_attribute('class'):
                    break
                else:
                    driver.execute_script("arguments[0].click();", next_page_button)
            except NoSuchElementException:
                print("Reached the last page or next page button not found.")
                break
            except TimeoutException:
                print("Timeout waiting for the next page button.")
                break

    # remove duplicates       
    product_urls = list(set(product_urls))

except Exception as e:
    print(f"An error occurred: {e}")
    traceback.print_exc() 
    driver.quit()

collect_nutrittion(product_urls12,"bakerydata12.csv")
# %% 


# # Calculate chunk size and remainder
# chunk_size, remainder = divmod(len(product_urls), 4)

# # Split the list into 4 arrays, adjusting for the remainder
# product_urls1 = product_urls[:chunk_size + (1 if remainder > 0 else 0)]
# product_urls2 = product_urls[len(product_urls1):len(product_urls1) + chunk_size + (1 if remainder > 1 else 0)]
# product_urls3 = product_urls[len(product_urls1) + len(product_urls2):len(product_urls1) + len(product_urls2) + chunk_size + (1 if remainder > 2 else 0)]
# product_urls4 = product_urls[len(product_urls1) + len(product_urls2) + len(product_urls3):]


# # Calculate the split index
# split_index = len(product_urls1) // 2
# len(product_urls12)
# # Split the array
# product_urls11 = product_urls1[:split_index]
# product_urls12 = product_urls1[split_index:]