class Credentials:
    def __init__(self):
        self.influx_url = "https://influx.xxx"
        self.influx_org = "xxxx"
        self.influx_token = "xxxxx"
        self.influx_bucket = "xxxx"
        # Obtain windows sid using "wmic useraccount get name,sid" in non-elevated command prompt
        self.windows_sid = 'S-xxxxx'


credentials = Credentials()
