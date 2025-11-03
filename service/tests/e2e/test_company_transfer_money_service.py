import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SELENIUM_URL = os.getenv("SELENIUM_URL", "http://localhost:4444/wd/hub")

@pytest.mark.e2e
def test_example_dot_com_title():
    chrome_opts = Options()
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--no-sandbox")

    driver = webdriver.Remote(
        command_executor=SELENIUM_URL,
        options=chrome_opts,
        desired_capabilities=DesiredCapabilities.CHROME,
    )
    try:
        driver.get("https://example.com")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        assert "Example Domain" in driver.title
    finally:
        driver.quit()
