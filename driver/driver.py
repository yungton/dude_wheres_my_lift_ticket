import time

from logger import logger
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By

from GLOBALS import CHROME_DRIVER_LOCATION, RESERVATION_ATTEMPT_RETRY_INTERVAL_SECONDS, IS_STARRED


class Driver:

    def __init__(self,
                 login_url,
                 username,
                 password,
                 reservation_date):
        self.driver = webdriver.Chrome(CHROME_DRIVER_LOCATION)
        self.wait = WebDriverWait(self.driver, 5)
        self.login_url = login_url
        self.previous_url = login_url
        self.username = username
        self.password = password
        self.reservation_date = reservation_date
        self.setup()

    def setup(self):
        self.driver.maximize_window()

    def get_login_form_info(self):
        self.driver.get(self.login_url)

        username_field_id = self.driver.find_element_by_id('email')
        password_field_id = self.driver.find_element_by_id('sign-in-password')
        submit_button_class = self.wait.until(ec.visibility_of_element_located((By.CLASS_NAME, 'submit')))

        return username_field_id, password_field_id, submit_button_class

    def login(self):

        # TODO sometimes the login page asks you to check a box saying I am not a robot
        # Do a check for the robot checkbox. If it's there, click it and hit go.
        username_field_id, password_field_id, submit_button_class = self.get_login_form_info()

        username_field_id.send_keys(self.username)
        password_field_id.send_keys(self.password)
        submit_button_class.click()

        self.validate_move()

    def navigate(self, *args, **kwargs):
        identifier = kwargs.get('identifier', None)
        direction = kwargs.get('direction', None)

        try:
            if len(kwargs.keys()) != 1:
                raise ValueError('Either an identifier or direction must be supplied to navigate().')
            if direction not in ('forwards', 'back', 'refresh', None):
                raise ValueError(f'Supplied direction: {direction}. Direction must be "forward", "back", '
                                 f'"refresh", or "None"')
        except ValueError as error:
            logger.error(error)
            exit()

        if identifier is not None:
            identifier_button = self.wait.until(ec.visibility_of_element_located((By.CSS_SELECTOR, identifier)))
            identifier_button.click()
            self.validate_move()
        else:
            if direction == 'refresh':
                logger.info(f'Refreshing page "{self.driver.current_url}".')
                self.driver.refresh()
            if direction == 'forward':
                pass  # TODO: Implement
            if direction == 'back':
                pass  # TODO: Implement

    def check_availability(self):
        add_reservation_page = 'https://account.ikonpass.com/en/myaccount/add-reservations/'

        if self.driver.current_url != add_reservation_page:
            logger.info(f'Current URL must be "{add_reservation_page}" to proceed with making reservations, the '
                        f'current URL is "{self.driver.current_url}"')

        # This is the ID of the Jackson Hole Mountain Element. Jackson Hole must be the ONLY resort starred.
        # TODO: Find a better way to do this.
        if IS_STARRED:
            jackson_hole_mountain_id = 'react-autowhatever-resort-picker-section-0-item-0'
        else:
            raise Exception("The mountain is not favorited and so is not in the proper position")

        jackson_hole_mountain_element = self.wait.until(
            ec.visibility_of_element_located((By.ID, jackson_hole_mountain_id)))
        jackson_hole_mountain_element.click()

        continue_button = self.wait.until(ec.visibility_of_element_located((By.CSS_SELECTOR, 'button.sc-AxjAm')))
        continue_button.click()

        # TODO: Select proper month (Currently reservations can only be made for the current month)
        self.driver.implicitly_wait(1)
        days_elements = self.driver.find_elements_by_class_name('DayPicker-Day')

        able_to_make_reservation = False

        for day in days_elements:
            # The date value i.e. 'Jan 29 2022'
            day_value = day.get_attribute('aria-label')[4:]
            day_class = day.get_attribute('class')

            if 'unavailable' not in day_class and 'past' not in day_class and day_value == self.reservation_date:
                able_to_make_reservation = True
                logger.info(f'Reservation available for "{self.reservation_date}", attempting to reserve day.')
                day.click()

                # The day is now selected, we just need to save and complete the reservation.
                self.complete_reservation()
                return True

        if not able_to_make_reservation:
            logger.info(f'Reservation NOT available for "{self.reservation_date}", will try again in '
                        f'{RESERVATION_ATTEMPT_RETRY_INTERVAL_SECONDS} seconds.')
            return False

    def complete_reservation(self):
        save_button = self.wait.until(ec.visibility_of_element_located((By.CSS_SELECTOR, '.jxPclZ')))
        save_button.click()

        # Need to wait here for some reason... Probably because page needs to refresh after click
        time.sleep(1)

        # CONTINUE TO CONFIRM BUTTON
        review_button = self.wait.until(ec.visibility_of_element_located((By.CSS_SELECTOR,
                                                                          'button.sc-AxjAm:nth-child(1)')))
        review_button.click()

        agree_checkbox = self.wait.until(ec.visibility_of_element_located((By.CLASS_NAME, 'input')))
        agree_checkbox.click()

        print("Completing a reservation!!!")
        logger.info('completing a reservation!!!')
        time.sleep(10)
        # confirm_button = self.wait.until(ec.visibility_of_element_located((By.CSS_SELECTOR,
        #                                                                    'button.sc-AxjAm:nth-child(1)')))
        # confirm_button.click()

    def validate_move(self):
        # We give the application 5 seconds to move to the new page before timing out
        timeout_count = 0

        while self.previous_url == self.driver.current_url:
            time.sleep(1)
            timeout_count += 1
            if timeout_count == 4:
                logger.info(f'Failed to navigate from {self.previous_url}.')
                exit()

        logger.info(f'Successfully navigated from {self.previous_url} to {self.driver.current_url}.')
        self.previous_url = self.driver.current_url

    def close_driver(self):
        logger.info('Closing the Chrome WebDriver.')
        self.driver.close()
