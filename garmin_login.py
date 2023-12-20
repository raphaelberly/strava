import garminconnect
import yaml


tokenstore = '~/.garminconnect'

# Read tokens from config
secrets = yaml.safe_load(open('conf/secrets.yaml'))

# Log in
garmin = garminconnect.Garmin(secrets['garmin']['email'], secrets['garmin']['password'])
garmin.login()

# Save tokens for next login
garmin.garth.dump(tokenstore)
