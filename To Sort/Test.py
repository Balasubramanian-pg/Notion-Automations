import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import random

# --- Configuration ---
LINKEDIN_USERNAME = "balasubramanian.ganeshan@flipcarbon.in" # Replace with your email
LINKEDIN_PASSWORD = "Burner23!"         # Replace with your password
EXCEL_FILE_PATH = r"C:\Users\ASUS\Videos\Linkedin Automator\Linkedin Profiles.xlsx"
URL_COLUMN_NAME = "LinkedIn_URL"
NAME_COLUMN_NAME = "Name"
ROLE_COLUMN_NAME = "Role"

MESSAGE_TEMPLATE = """Hey [Dude],

Hope you're doing well! This is a bit out of the blue, but I recently checked out the [Role] and was wondering if you’d be open to referring me.

No pressure at all - just thought I’d reach out and ask. Would really appreciate any help!"""

# --- Helper Functions ---

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--lang=en-US")
    # options.add_argument("--headless") # Not recommended for LinkedIn
    # options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    # options.add_argument("user-data-dir=./chrome_profile_linkedin_auto") # Use with caution

    try:
        print("Setting up WebDriver...")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("WebDriver setup successful.")
        return driver
    except Exception as e:
        print(f"Error setting up WebDriver: {e}")
        return None

def login_to_linkedin(driver, username, password):
    print("Attempting to log in to LinkedIn...")
    driver.get("https://www.linkedin.com/login")
    try:
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "username"))
        ).send_keys(username)
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "password"))
        ).send_keys(password)
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
        ).click()
        print("Login form submitted.")
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(@class, 'feed-identity-module')] | //*[@id='global-nav-search'] | //input[contains(@placeholder, 'Search')]"))
        )
        print("Login likely successful.")
        return True
    except TimeoutException:
        print("Timeout during login. Possible CAPTCHA, incorrect credentials, or slow network/page load.")
        print("Page title:", driver.title); print("Current URL:", driver.current_url)
        # driver.save_screenshot("login_timeout.png")
        input("MANUAL INTERVENTION: Please solve CAPTCHA/login issues, then press Enter...")
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(@class, 'feed-identity-module')] | //*[@id='global-nav-search'] | //input[contains(@placeholder, 'Search')]"))
            )
            print("Login confirmed after manual intervention.")
            return True
        except TimeoutException:
            print("Still not logged in after manual intervention. Exiting.")
            return False
    except Exception as e:
        print(f"An error occurred during login: {e}")
        return False

def check_connection_status(driver, first_name):
    """Checks if already connected, pending, or can message."""
    try:
        # Check for "Pending" status text - often in the button itself or nearby
        pending_elements = driver.find_elements(By.XPATH, "//*[self::button or self::span][contains(normalize-space(.), 'Pending') or contains(@aria-label, 'Pending')]")
        if any(el.is_displayed() for el in pending_elements):
            print(f"Connection status for {first_name}: Pending")
            return "pending"

        # Check for "Message" button, often in the pvs-profile-actions
        # This indicates you are already connected.
        message_button_xpath = (
            "//div[contains(@class, 'pvs-profile-actions')]//a[contains(@href, '/messaging/thread/') or .//span[normalize-space(text())='Message']] | "
            "//div[contains(@class, 'pvs-profile-actions')]//button[contains(@aria-label, 'Message ') or .//span[normalize-space(text())='Message']]"
        )
        message_buttons = driver.find_elements(By.XPATH, message_button_xpath)
        if any(btn.is_displayed() for btn in message_buttons):
            print(f"Connection status for {first_name}: Likely already connected (Message button found).")
            return "connected"

        # Check for degree, e.g., "1st", "2nd" (less reliable as main indicator but good context)
        profile_header_text = driver.find_element(By.XPATH, "//main//section[1]//div[contains(@class, 'text-body-small')] | //main//div[contains(@class, 'pv-text-details__right-panel')]//span[contains(@class, 'distance')]").text.lower()
        if "1st" in profile_header_text and "degree" in profile_header_text:
            print(f"Connection status for {first_name}: 1st degree connection.")
            return "connected"
        
    except NoSuchElementException:
        pass # Elements for status check not found, proceed
    except Exception as e:
        print(f"Minor error during connection status check (non-critical): {e}")
    return None

def send_connection_request(driver, profile_url, first_name, role):
    print(f"\nProcessing profile: {profile_url} for {first_name}")
    driver.get(profile_url)
    try:
        WebDriverWait(driver, 20).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//main"))) # Wait for main content area
    except TimeoutException:
        print("Page did not load completely or main content not found.")
        # driver.save_screenshot(f"pageload_fail_{first_name}.png")
        return False
    time.sleep(random.uniform(2.5, 4.5)) # Allow dynamic elements to render

    try:
        status = check_connection_status(driver, first_name)
        if status == "pending":
            print(f"Skipping {first_name}: Connection request already pending.")
            return False
        if status == "connected":
            print(f"Skipping {first_name}: Already connected.")
            return False

        connect_button = None
        print(f"Attempting to find 'Connect' button for {first_name}...")

        # Attempt 1: DIRECT CONNECT BUTTON (aria-label pattern + inner text "Connect")
        # This is the most specific for the HTML you provided.
        try:
            xpath_direct_connect_aria = (
                "//button[starts-with(@aria-label, 'Invite ') and "
                "contains(@aria-label, ' to connect') and "
                ".//span[normalize-space(text())='Connect']]"
            )
            print(f"  Trying XPath 1 (Aria-label 'Invite...' + Span 'Connect'): {xpath_direct_connect_aria}")
            connect_button = WebDriverWait(driver, 12).until(
                EC.element_to_be_clickable((By.XPATH, xpath_direct_connect_aria))
            )
            print(f"  SUCCESS: Found 'Connect' button for {first_name} using XPath 1.")
        except TimeoutException:
            print(f"  INFO: XPath 1 (Aria-label 'Invite...') failed for {first_name}.")
            # Attempt 2: GENERIC DIRECT CONNECT BUTTON (within profile actions, text "Connect", avoid "Follow/Message")
            try:
                xpath_direct_connect_generic = (
                    "//div[contains(@class, 'pvs-profile-actions')]//button"
                    "[.//span[normalize-space(text())='Connect'] and "
                    "not(contains(@aria-label, 'Follow')) and "
                    "not(contains(@aria-label, 'Message')) and "
                    "not(contains(@aria-label, 'Pending')) and "
                    "not(contains(normalize-space(.), 'Pending')) and " # Check span text for Pending too
                    "not(contains(@aria-label, 'Remove connection'))]"
                )
                print(f"  Trying XPath 2 (Generic in actions + Span 'Connect'): {xpath_direct_connect_generic}")
                connect_button = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, xpath_direct_connect_generic))
                )
                print(f"  SUCCESS: Found 'Connect' button for {first_name} using XPath 2.")
            except TimeoutException:
                print(f"  INFO: XPath 2 (Generic in actions) failed for {first_name}.")
                # Attempt 3: "MORE" MENU -> "Connect"
                try:
                    xpath_more_button = (
                        "//div[contains(@class, 'pvs-profile-actions')]//button"
                        "[contains(@aria-label, 'More actions') or .//span[normalize-space(text())='More'] or "
                        ".//li-icon[@type='overflow-horizontal-ios-medium'] or .//li-icon[@type='overflow-web-ios-medium']]"
                    )
                    print(f"  Trying XPath 3 ('More...' button): {xpath_more_button}")
                    more_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, xpath_more_button))
                    )
                    driver.execute_script("arguments[0].click();", more_button) # JS click sometimes helps with overlays
                    # more_button.click()
                    print(f"  Clicked 'More...' button for {first_name}.")
                    time.sleep(random.uniform(1.0, 2.0))

                    xpath_connect_in_dropdown = (
                        "//div[@role='menuitem'][.//span[normalize-space(text())='Connect'] and "
                        "not(contains(., 'Remove connection')) and not(contains(., 'Follow'))]"
                    )
                    print(f"  Trying XPath 3b ('Connect' in dropdown): {xpath_connect_in_dropdown}")
                    connect_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, xpath_connect_in_dropdown))
                    )
                    print(f"  SUCCESS: Found 'Connect' in 'More...' dropdown for {first_name}.")
                except TimeoutException:
                    print(f"  INFO: XPath 3 ('More...' menu route) failed for {first_name} (Timeout).")
                except NoSuchElementException:
                    print(f"  INFO: XPath 3 ('More...' menu route) failed for {first_name} (NoSuchElement).")
                except ElementClickInterceptedException:
                    print(f"  INFO: XPath 3 ('More...' menu route) click intercepted for {first_name}.")


        if not connect_button:
            print(f"  FAILURE: Could NOT find any 'Connect' button/option for {first_name} at {profile_url} after all attempts. Skipping.")
            # driver.save_screenshot(f"no_connect_btn_{first_name}.png")
            return False

        print(f"Clicking 'Connect' button/option for {first_name}...")
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", connect_button) # Scroll into view
            time.sleep(0.5)
            connect_button.click()
        except ElementClickInterceptedException:
            print(f"  WARN: Click on Connect button was intercepted. Trying JavaScript click for {first_name}.")
            driver.execute_script("arguments[0].click();", connect_button)

        print(f"  Clicked 'Connect' for {first_name}.")
        time.sleep(random.uniform(1.5, 2.5))

        # --- Step 2: Click "Add a note" ---
        try:
            add_note_button_xpath = "//button[@aria-label='Add a note'] | //button[.//span[normalize-space(text())='Add a note']]"
            print(f"  Trying 'Add a note' button: {add_note_button_xpath}")
            add_note_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, add_note_button_xpath))
            )
            add_note_button.click()
            print(f"  Clicked 'Add a note' for {first_name}.")
            time.sleep(random.uniform(0.8, 1.5))
        except TimeoutException:
            print(f"  INFO: 'Add a note' button not found for {first_name}. Modal might be different or allow note directly.")

        # --- Step 3: Paste the customized message ---
        try:
            message_area_xpath = "//textarea[@name='message' or @id='custom-message' or contains(@aria-label, 'message')]"
            print(f"  Trying message text area: {message_area_xpath}")
            message_area = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, message_area_xpath))
            )
            custom_message = MESSAGE_TEMPLATE.replace("[Dude]", first_name).replace("[Role]", role)
            message_area.clear()
            message_area.send_keys(custom_message)
            print(f"  Pasted message for {first_name}: '{custom_message[:35].replace('\n', ' ')}...'")
            time.sleep(random.uniform(0.5, 1.0))
        except TimeoutException:
            print(f"  FAILURE: Message text area not found for {first_name}. Cannot send personalized note.")
            # driver.save_screenshot(f"no_msg_area_{first_name}.png")
            try:
                close_button_xpath = "//button[@aria-label='Dismiss'] | //button[contains(@class, 'artdeco-modal__dismiss')]"
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, close_button_xpath))).click()
                print(f"  Closed modal for {first_name} as message area was not found.")
            except:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE) # Try ESC
            return False

        # --- Step 4: Click "Send" ---
        try:
            send_button_xpath = (
                "//button[@aria-label='Send now'] | //button[@aria-label='Send invitation'] | "
                "//button[.//span[normalize-space(text())='Send'] and not(contains(@class,'cancel')) and not(@aria-label='Cancel')]"
            )
            print(f"  Trying 'Send' button: {send_button_xpath}")
            send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, send_button_xpath))
            )
            send_button.click()
            print(f"  SUCCESS: Connection request SENT to {first_name} for role {role} at {profile_url}.")
            time.sleep(random.uniform(1,2))
            return True
        except TimeoutException:
            print(f"  FAILURE: 'Send' button not found for {first_name} after adding note.")
            # driver.save_screenshot(f"no_send_btn_{first_name}.png")
            try:
                dismiss_button_xpath = "//button[@aria-label='Dismiss'] | //button[contains(@class, 'artdeco-modal__dismiss')]"
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, dismiss_button_xpath))).click()
                print(f"  Closed modal for {first_name} after failing to send.")
            except:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE) # Try ESC
            return False

    except ElementClickInterceptedException as e:
        print(f"  ERROR: Click was intercepted for {first_name} at {profile_url}: {e}")
        # driver.save_screenshot(f"click_intercepted_{first_name}.png")
        return False
    except NoSuchElementException as e:
        print(f"  ERROR: Element not found for {first_name} at {profile_url}: {e}")
        # driver.save_screenshot(f"no_such_element_{first_name}.png")
        return False
    except TimeoutException as e:
        print(f"  ERROR: Timeout occurred for {first_name} at {profile_url}: {e}")
        # driver.save_screenshot(f"timeout_error_{first_name}.png")
        return False
    except Exception as e:
        print(f"  ERROR: An unexpected error occurred for {first_name} at {profile_url}: {e}")
        # driver.save_screenshot(f"unexpected_error_{first_name}.png")
        return False

# --- Main Script ---
if __name__ == "__main__":
    if "your_linkedin_email@example.com" in LINKEDIN_USERNAME or "your_linkedin_password" in LINKEDIN_PASSWORD:
        print("ERROR: Please update LINKEDIN_USERNAME and LINKEDIN_PASSWORD.")
        exit()

    driver = None
    try:
        driver = setup_driver()
        if not driver: exit()
        if not login_to_linkedin(driver, LINKEDIN_USERNAME, LINKEDIN_PASSWORD): exit()

        print("Login successful. Reading Excel file...")
        try:
            df = pd.read_excel(EXCEL_FILE_PATH)
            required_cols = [URL_COLUMN_NAME, NAME_COLUMN_NAME, ROLE_COLUMN_NAME]
            if not all(col in df.columns for col in required_cols):
                print(f"Excel file must contain columns: {', '.join(required_cols)}")
                exit()
        except FileNotFoundError:
            print(f"Error: Excel file not found at {EXCEL_FILE_PATH}"); exit()
        except Exception as e:
            print(f"Error reading Excel file: {e}"); exit()

        successful_requests = 0
        failed_profiles_details = []
        print(f"\nStarting to process {len(df)} profiles...\n")

        for index, row in df.iterrows():
            profile_url = str(row.get(URL_COLUMN_NAME, "")).strip()
            first_name = str(row.get(NAME_COLUMN_NAME, "")).strip()
            target_role = str(row.get(ROLE_COLUMN_NAME, "")).strip()

            print(f"\n--- Processing Profile {index + 1}/{len(df)} ---")
            if not profile_url or not profile_url.startswith("http"):
                print(f"Skipping row {index+2}: Invalid or missing LinkedIn URL ('{profile_url}').")
                failed_profiles_details.append({'url': profile_url, 'name': first_name, 'reason': 'Invalid URL'})
                continue
            if not first_name:
                print(f"Skipping row {index+2} (URL: {profile_url}): Missing 'Name'.")
                failed_profiles_details.append({'url': profile_url, 'name': first_name, 'reason': 'Missing Name'})
                continue
            # Role is important for the message, but we could proceed without it if template handles it
            if not target_role and "[Role]" in MESSAGE_TEMPLATE:
                print(f"Skipping row {index+2} (URL: {profile_url}, Name: {first_name}): Missing 'Role' for message template.")
                failed_profiles_details.append({'url': profile_url, 'name': first_name, 'reason': 'Missing Role for template'})
                continue
            
            if send_connection_request(driver, profile_url, first_name, target_role):
                successful_requests += 1
                print(f"--- RESULT: Successfully processed {first_name} at {profile_url} ---")
            else:
                print(f"--- RESULT: Failed to process or skipped {first_name} at {profile_url} ---")
                failed_profiles_details.append({'url': profile_url, 'name': first_name, 'reason': 'Connection process failed/skipped'})
            
            # CRITICAL: Long and randomized delay
            # For real use: random.uniform(120, 300)  (2 to 5 minutes)
            delay_time = random.uniform(45, 75) # ADJUST FOR REAL USE!
            print(f"Waiting for {delay_time:.0f} seconds before next profile...")
            time.sleep(delay_time)

            # MAX_REQUESTS_PER_SESSION = 5 # Example limit
            # if successful_requests >= MAX_REQUESTS_PER_SESSION:
            #     print(f"Reached processing limit of {MAX_REQUESTS_PER_SESSION} successful requests.")
            #     break

        print("\n--- Script Finished ---")
        print(f"Total successful requests sent: {successful_requests}")
        if failed_profiles_details:
            print("\nProfiles that failed or were skipped:")
            for item in failed_profiles_details:
                print(f"- URL: {item['url']}, Name: {item['name']}, Reason: {item['reason']}")

    except KeyboardInterrupt:
        print("\n--- Script interrupted by user (Ctrl+C) ---")
    except Exception as e:
        print(f"An UNEXPECTED CRITICAL error occurred in the main script: {e}")
        # if driver: driver.save_screenshot("main_script_critical_error.png")
    finally:
        if driver:
            print("Closing browser...")
            driver.quit()
            print("Browser closed.")