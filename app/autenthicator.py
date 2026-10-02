import logging
import os

import streamlit as st
import streamlit_authenticator as stauth
import yaml

# Logins are written to their own file, read by the Pi's fail2ban `sports-login` jail: keep the line format in sync
LOGIN_LOG_PATH = '../log/app_logins.log'

LOGGER = logging.getLogger(__name__)
if not LOGGER.handlers:  # Streamlit can re-import this module, don't stack file handlers
    os.makedirs(os.path.dirname(LOGIN_LOG_PATH), exist_ok=True)
    handler = logging.FileHandler(LOGIN_LOG_PATH)
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False


# Address of the browser, as seen by haproxy
def client_ip():
    # haproxy adds its own X-Forwarded-For header last: earlier values come from the client and can be forged
    forwarded = st.context.headers.get_all('X-Forwarded-For')
    if forwarded:
        return forwarded[-1].split(',')[-1].strip()
    # Not behind haproxy (local run)
    return st.context.ip_address


def authenticate():

    with open('conf/accounts.yaml') as file:
        creds_auth = yaml.safe_load(file)

    authenticator = stauth.Authenticate(
        creds_auth['credentials'],
        creds_auth['cookie']['name'],
        creds_auth['cookie']['key'],
        creds_auth['cookie']['expiry_days'],
    )

    # The library keeps a failed status on later reruns, reset it so that False only means "this submit failed"
    if st.session_state.get('authentication_status') is False:
        st.session_state['authentication_status'] = None

    # The callback only fires on a successful form login, not on cookie re-authentication
    authenticator.login(
        location='main',
        callback=lambda login: LOGGER.info(f'Successful login for {login["username"]} from {client_ip()}'),
    )
    authentication_status = st.session_state['authentication_status']

    if authentication_status is False:
        LOGGER.warning(f'Failed login from {client_ip()}')
        st.error('Username/password is incorrect')
        st.stop()
    elif authentication_status is None:
        st.warning('Please enter your username and password')
        st.stop()

    return st.session_state['name']
