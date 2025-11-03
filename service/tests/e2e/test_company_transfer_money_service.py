import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SELENIUM_URL = os.getenv("SELENIUM_URL", "http://localhost:4444/wd/hub")

@pytest.mark.e2e
def test_example_dot_com_title():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Remote(command_executor=SELENIUM_URL, options=opts)

    try:
        driver.get("https://example.com")
        WebDriverWait(driver, 10).until(EC.title_contains("Example Domain"))
        h1 = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        assert "Example Domain" in driver.title
        assert h1.text != ""
    finally:
        driver.quit()
