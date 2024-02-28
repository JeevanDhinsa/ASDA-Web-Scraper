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


def collect_nutrition(product_urls,csv_name):
    dataframes_list = []
    for p in product_urls:

        driver.get(p)

        #  Get all the information elements for the product
        try:
            WebDriverWait(driver, 10).until(
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
                nutdf1 = [item.replace(':', '') for item in nutdf1]
                nutdf1 = [item for item in nutdf1 if "negligible" not in item.lower()]
                nutdf1[0] = nutdf1[0].replace("(kJ/kcal)", "").strip()
                nutdf1[0] = nutdf1[0].replace(", kJ/kcal", "").strip()
                nutdf1[0] = nutdf1[0].replace("kJ/kcal", "").strip()
                nutdf1[0] = re.sub(r'\(\d+%\s*.*?\)', '', nutdf1[0])


                # exception case where of which saturates are on different lines
                for i in range(len(nutdf1)- 2, -1, -1):  #  Start from the second-last item down to the first item
                    if nutdf1[i] == 'of which' and 'Saturates' in nutdf1[i + 1]:
                        nutdf1[i] += ' ' + nutdf1[i + 1]  # Combine the elements
                        nutdf1.pop(i + 1)  # Remove the now redundant 'Saturates' element

                if re.search(r"\(\d", nutdf1[0]):
                    bracket = nutdf1[0].split("(",1)
                    nutdf1 = bracket + nutdf1[1:]
                
                # exception case for energy readings with /
                if "/ " in nutdf1[0] and nutdf1[0].count("/") > 1 and nutdf1[0].count("/ ") < 2:
                    nutdf1[0] = nutdf1[0].split("/ ", 1)[0]

                if nutdf1[0].count('/') == 2:
                    parts = nutdf1[0].split('/')  
                    # Extract and format the first two parts as 'Energy XXXkJ' and 'XXXkcal'
                    energy_part = parts[0].strip()  
                    kcal_part = parts[1].split()[0] + ' '  
                    # Update the list
                    nutdf1[0] = energy_part
                    nutdf1.insert(1, kcal_part) 
                elif nutdf1[0].endswith("/"):
                    # Remove the last character ("/") from the first item
                    nutdf1[0] = nutdf1[0][:-1]    
                # exception cases for punctation in energy title     
                elif re.search(r"/\s*\d", nutdf1[0]):           
                    parts = nutdf1[0].split('/')
                    nutdf1 = parts + nutdf1[1:]

                # comma 
                if nutdf1[0].count(",") > 1 :
                    first_comma = nutdf1[0].find(',')
                    second_comma = nutdf1[0].find(',', first_comma + 1)
                    nutdf1[0] = nutdf1[0][:second_comma] + nutdf1[0][second_comma+1:]
                if re.search(r",\s*\d", nutdf1[0]):
                    parts = nutdf1[0].split(',')
                    nutdf1 = parts + nutdf1[1:]

                # dash
                if nutdf1[0].count("-") > 1 :
                    first_dash = nutdf1[0].find('-')
                    second_dash = nutdf1[0].find('-', first_dash + 1)
                    nutdf1[0] = nutdf1[0][:second_dash] + nutdf1[0][second_dash+1:]
                if re.search(r"-\s*\d", nutdf1[0]):
                    parts = nutdf1[0].split('-')
                    nutdf1 = parts + nutdf1[1:]


                # Check if 'calories' is in the first item 
                if "calories" in nutdf1[0].lower():
                    # Find all occurrences of one or more digits
                    numbers = re.findall(r'\d+', nutdf1[0])
                    # Proceed only if there's exactly one number
                    if len(numbers) == 1:
                        # Find the first occurrence of one or more digits and everything after
                        match = re.search(r'\d+.*', nutdf1[0])
                        if match: 
                            # Extract the matched string (number and everything after it)
                            number_and_after = match.group()
                            nutdf1[0] = nutdf1[0][:match.start()].strip()
                            # Insert the extracted part at the next position in the list
                            nutdf1.insert(1, number_and_after)

                nutdf2 = []
                
                # Check if 'Fibre' is in any of the nutdf1 items
                fibre_present = any('fibre' in item.lower() for item in nutdf1)
                fat_present =  any('fat' in item.lower() for item in nutdf1)
                carbohydrate_present =  any('carbohydrate' in item.lower() for item in nutdf1)
                protein_present =  any('protein' in item.lower() for item in nutdf1)
                salt_present =  any('salt' in item.lower() for item in nutdf1)

                # List of saturates to check for in each item, covering all variations
                keywords = [
                    'monounsaturated', '(mono-unsaturates)', 'monounsaturates', 'Mono-unsaturates',
                    'polyunsaturated', '(polyunsaturates)', 'polyunsaturates','poly-unsaturates'
                ]

                # Check for 'monounsaturated' or 'mono-unsaturates' and 'polyunsaturated' or 'polyunsaturates'
                mono_poly_unsaturated_present = any(any(keyword.lower() in item.lower() for keyword in keywords) for item in nutdf1)

                # New titles to replace the original ones
                new_labels = ['energy kj', 'energy kcal', 'fat', 'of which saturates', 'carbohydrate', 'of which sugars', 'fibre', 'protein', 'salt'] 
                
                # Define the labels for when 'monounsaturated' or 'polyunsaturated' are present
                new_labels2 = ['energy kj', 'energy kcal', 'fat', 'of which saturates', 'of which monounsaturated', 'of which polyunsaturated', 'carbohydrate', 'of which sugars', 'fibre', 'protein', 'salt']

                # Choose the correct set of labels based on the checks
                if mono_poly_unsaturated_present:
                    chosen_labels = new_labels2
                else:
                    chosen_labels = new_labels
                if not fibre_present and 'fibre' in chosen_labels:
                    chosen_labels.remove('fibre')
                if not fat_present:
                    if 'fat' in chosen_labels:
                        chosen_labels.remove('fat')
                        if 'of which saturates' in chosen_labels:
                            chosen_labels.remove('of which saturates')

                if not carbohydrate_present:
                    if 'carbohydrate' in chosen_labels:
                        chosen_labels.remove('carbohydrate')
                        if 'of which sugars' in chosen_labels:
                            chosen_labels.remove('of which sugars')

                if not protein_present and 'protein' in chosen_labels:
                    chosen_labels.remove('protein')

                if not salt_present and 'salt' in chosen_labels:
                    chosen_labels.remove('salt')


                # Updated regex to capture more specific details from the strings, including potential guidelines amounts.
                pattern = r"^(.*?)(<\d*\.?\d+|\d*\.?\d+|Trace)(g|kJ|kcal|µg)?( \d*%?)?"

                # Processing all items
                for i, item in enumerate(nutdf1):
                    if i < len(chosen_labels):  # Apply new titles for the first 8 items
                        label = chosen_labels[i]
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
                        if i >= len(chosen_labels):  # For items beyond the first 8, include any additional details like %RI
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
                'Catergory': cat[0] if len(cat) > 0 else "N/A",
                'Subcatergory': cat[1] if len(cat) > 1 else "N/A"
                }
            
            title_df = pd.DataFrame([data1])
            

            # Combination of datasets

            nutrition_df.index = title_df.index

            product_data = pd.concat([title_df,nutrition_df],axis = 1)
            # Removing duplicate columns
            product_data = product_data.loc[:, ~product_data.columns.duplicated()]
            
            dataframes_list.append(product_data)
    
    print("finished")

    driver.quit()

    if dataframes_list:
        final_data = pd.concat(dataframes_list, ignore_index=False)
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



collect_nutrition(product_urls,"testdata.csv")
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

collect_nutrition(product_urls,"meatdata.csv")

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

collect_nutrition(product_urls,"bakerydata.csv")
# %% 
# %%  #################################################### Chilled Food ########################################################
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

    departmentlink = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".aisle__link[href*='aisle/chilled-food']"))  
    )

    department_url = []
    department_url.extend([department.get_attribute('href') for department in departmentlink])
    

    keywords = ["100-calorie-zone", "afternoon-tea", "party-decorations-accessories", "oven-trays", "meal-deals", "take-out-club-pizza-meal-deal", 
                "food-to-go-meal-deal", "lunch-ideas", "2-for-5-cooked-meats", "2-for-3-cooked-meats"]
    
    # Create a regex pattern that matches any of the keywords as whole segments
    # This pattern uses word boundaries (\b) around each keyword to ensure exact matches
    pattern = r'/(' + '|'.join([re.escape(keyword) for keyword in keywords]) + r')(?=/|$)'

    department_url = [url for url in department_url if not re.search(pattern, url)]

    # Manual sort exception 
    department_url.remove("https://groceries.asda.com/aisle/chilled-food/cheese/continental-cheese/1215660378320-1215341805721-1215341806015")
    department_url.extend(["https://groceries.asda.com/shelf/chilled-food/cheese/continental-cheese/brie-camembert/1215660378320-1215341805721-1215341806015-1215341830339",
                          "https://groceries.asda.com/shelf/chilled-food/cheese/continental-cheese/parmesan-hard-cheese/1215660378320-1215341805721-1215341806015-1215627294585",
                          "https://groceries.asda.com/shelf/chilled-food/cheese/continental-cheese/mozzarella-mascarpone/1215660378320-1215341805721-1215341806015-1215341830518",
                          "https://groceries.asda.com/shelf/chilled-food/cheese/continental-cheese/feta-halloumi-salad/1215660378320-1215341805721-1215341806015-1215341830577"])


    for d in department_url:
           
        driver.get(d)

        #Collect product urls 
        
        # Start iterating through pages to collect product URLs
        while True:
            products = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-module-name='Product List (Global Aisle)'] .co-product__anchor, \
                                                                        [data-module-name='Shelf Product List (Global Rule)'] .co-product__anchor"))
            )
            product_urls.extend([product.get_attribute('href') for product in products])

            try:
                # Check for the next page button and determine if it's the last page
                next_page_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".co-pagination__arrow--right"))
                )
                # Check if the next page button is disabled (if applicable)
                if 'disabled' in next_page_button.get_attribute('class'):
                    print("last page")
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
    

collect_nutrition(product_urls,"chilledfooddata.csv")
# %%
# %%  #################################################### Frozen Food ########################################################
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
    # Initialize an empty list to hold all product URLs (948 urls)
    product_urls = []

    departmentlink = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".aisle__link[href*='aisle/frozen-food']"))  
    )

    department_url = []
    department_url.extend([department.get_attribute('href') for department in departmentlink])
    len(department_url)

    keywords = ["3-for-10-frozen-meat", "scratch-cook-from-frozen","oven-trays", "meal-deals", "4-for-6-frozen-ready-meals","ice-cream-parlour","pies-ready-meals"]
    
    # Create a regex pattern that matches any of the keywords as whole segments
    # This pattern uses word boundaries (\b) around each keyword to ensure exact matches
    pattern = r'/(' + '|'.join([re.escape(keyword) for keyword in keywords]) + r')(?=/|$)'

    department_url = [url for url in department_url if not re.search(pattern, url)]

    # Manual sort exception 
    #department_url.remove()
    department_url.extend(["https://groceries.asda.com/aisle/frozen-food/ice-cream-parlour/view-all-ice-cream-parlour/1215338621416-1215338747181-1215685901765",
                           "https://groceries.asda.com/aisle/frozen-food/pies-ready-meals/view-all-ready-meals/1215338621416-1215338748688-1215685962175"])


    for d in department_url:
           
        driver.get(d)
        #Collect product urls 
        
        # Start iterating through pages to collect product URLs
        while True:
            products = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-module-name='Product List (Global Aisle)'] .co-product__anchor"))
            )
            product_urls.extend([product.get_attribute('href') for product in products])

            try:
                # Check for the next page button and determine if it's the last page
                next_page_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".co-pagination__arrow--right"))
                )
                # Check if the next page button is disabled (if applicable)
                if 'disabled' in next_page_button.get_attribute('class'):
                    print("last page")
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
    
collect_nutrition(product_urls,"frozenfooddata.csv")
# %%

# rerun meat and bakery to update fixed issues 

len(product_urls)

split_product_urls = [product_urls[i:i + 100] for i in range(0, len(product_urls), 100)]

product_urls10 = split_product_urls[9]


# # Calculate the split index
# split_index = len(product_urls1) // 2
# # Split the array
# product_urls11 = product_urls1[:split_index]
# product_urls12 = product_urls1[split_index:]


# df1 = pd.read_csv("bakerydata1.csv")
# df2 = pd.read_csv("bakerydata2.csv")
# df3 = pd.read_csv("bakerydata3.csv")
# df4 = pd.read_csv("bakerydata4.csv")
# df5 = pd.read_csv("bakerydata5.csv")
# df6 = pd.read_csv("bakerydata6.csv")
# df7 = pd.read_csv("bakerydata7.csv")
# df8 = pd.read_csv("bakerydata8.csv")
# df9 = pd.read_csv("bakerydata9.csv")
# df10 = pd.read_csv("bakerydata10.csv")

# df11 = pd.read_csv("chilledfooddata11.csv")
# df12 = pd.read_csv("chilledfooddata12.csv")
# df13 = pd.read_csv("chilledfooddata13.csv")
# df14 = pd.read_csv("chilledfooddata14.csv")
# df15 = pd.read_csv("chilledfooddata15.csv")
# df16 = pd.read_csv("chilledfooddata16.csv")
# df17 = pd.read_csv("chilledfooddata17.csv")
# df18 = pd.read_csv("chilledfooddata18.csv")
# df19 = pd.read_csv("chilledfooddata19.csv")
# df20 = pd.read_csv("chilledfooddata20.csv")
# df21 = pd.read_csv("chilledfooddata21.csv")
# df22 = pd.read_csv("chilledfooddata22.csv")
# df23 = pd.read_csv("chilledfooddata23.csv")
# df24 = pd.read_csv("chilledfooddata24.csv")
# df25 = pd.read_csv("chilledfooddata25.csv")
# df26 = pd.read_csv("chilledfooddata26.csv")
# df27 = pd.read_csv("chilledfooddata27.csv")
# df28 = pd.read_csv("chilledfooddata28.csv")
# df29 = pd.read_csv("chilledfooddata29.csv")
# df30 = pd.read_csv("chilledfooddata30.csv")

# # Concatenate the DataFrames
# concatenated_df = pd.concat([df1, df2, df3, df4, df5, df6, df7, df8,df9,df10], ignore_index=True)

# concatenated_df.to_csv("bakerydata.csv", index = False, encoding='utf-8-sig')

# final_data.to_csv("chilledfooddata11.csv", index = False, encoding='utf-8-sig')


# # Assuming product_urls is a list of URLs
# df = pd.DataFrame(product_urls, columns=['URL'])

# # Save to CSV
# df.to_csv("frozenproducturls.csv", index=False)

# Load from CSV
product_urls = pd.read_csv("frozenproducturls.csv")

# Convert to list
product_urls = product_urls['URL'].tolist()
