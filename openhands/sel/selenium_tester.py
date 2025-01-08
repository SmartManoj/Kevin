from selenium import webdriver
from selenium.webdriver.remote import remote_connection
from selenium.webdriver.remote.command import Command

from openhands.sel.selenium_session_details import session_id, url


class SessionRemote(webdriver.Remote):
    name = 'chrome'

    def start_session(self, desired_capabilities, browser_profile=None):
        w3c = True
        w3c


def create_driver(url, session_id):
    rmt_con = remote_connection.RemoteConnection(url)
    rmt_con._commands.update(
        {Command.UPLOAD_FILE: ('POST', '/session/$sessionId/file')}
    )
    options = webdriver.ChromeOptions()
    driver = SessionRemote(command_executor=rmt_con, options=options)
    driver.session_id = session_id
    return driver


driver = create_driver(url, session_id)
## import selenium keys
if __name__ == '__main__':
    print(driver.current_url)
