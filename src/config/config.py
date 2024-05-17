#!/usr/bin/env python3
"""
Copyright (c) 2024 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

__author__ = "Trevor Maco <tmaco@cisco.com>"
__copyright__ = "Copyright (c) 2024 Cisco and/or its affiliates."
__license__ = "Cisco Sample Code License, Version 1.1"

import pathlib
from typing import ClassVar, Optional

from dotenv import dotenv_values


class Config:
    """
    Config class to handle all environment variables and settings for application
    """
    _instance: ClassVar[Optional['Config']] = None

    # PATHS - Adjust as necessary
    DIR_PATH: ClassVar[pathlib.Path] = pathlib.Path(__file__).parents[2]
    SRC_PATH: ClassVar[pathlib.Path] = pathlib.Path(__file__).parents[1]
    ARCHIVE_PATH: ClassVar[pathlib.Path] = pathlib.Path(__file__).parents[1] / 'map_archive_exports'

    README_FILE_PATH: ClassVar[str] = str(pathlib.Path(__file__).parents[2] / 'README.md')
    ENV_FILE_PATH: ClassVar[str] = str(pathlib.Path(__file__).parents[0] / '.env')

    # App Config
    APP_NAME: ClassVar[str] = 'Catalyst Center Wireless Floor Maps to Meraki'
    APP_VERSION: ClassVar[str] = '1.0.0'

    def __init__(self):
        # Load only the variables defined in the .env file
        self.env_vars = dotenv_values(self.ENV_FILE_PATH)
        for key, value in self.env_vars.items():
            setattr(self, key, value)

    @classmethod
    def get_instance(cls):
        """
        Singleton instance of the Config class
        :return: Config instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reload_config(cls):
        """
        Reload the Config instance
        :return: Config instance
        """
        cls._instance = None  # Reset the singleton instance
        return cls.get_instance()

    @property
    def CAT_CENTER_BASE_URL(self):
        """
        Catalyst Center Base URL for API Calls
        :return: Base URL
        """
        cat_center_ip = getattr(self, 'CAT_CENTER_IP', 'default_ip')  # Use a default value or handle it appropriately
        return f"https://{cat_center_ip}"


c = Config.get_instance()  # Singleton instance of Config
