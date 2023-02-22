from dataclasses import dataclass
import numpy as np
import requests
import sys
from .config import config

@dataclass
class Api:
    plan_id: None
    headers: None
    
    def get(self, endpoint):

        if endpoint == 'plan':
            url = f'https://{config.PREFIX}.dronedeploy.com/api/v1/plan/{self.plan_id}'
            response = requests.get(url, headers=self.headers)
            response = response.json()

            if response.get('code') is not None:
                print(response.get("message"))
                sys.exit(0)

            return response

