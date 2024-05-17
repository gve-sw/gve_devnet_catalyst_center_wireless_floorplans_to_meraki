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

from typing import ClassVar, Optional

import meraki

from config.config import c


class MERAKI_API(object):
    """
    Meraki API Class, includes various methods to interact with Meraki API
    """
    _instance: ClassVar[Optional['MERAKI_API']] = None

    def __init__(self):
        """
        Initialize the Meraki class: dashboard sdk instance
        """
        self.org_id = c.ORG_ID
        self.retry_429_count = 25
        self.dashboard = meraki.DashboardAPI(api_key=c.MERAKI_API_KEY, suppress_logging=True,
                                             caller=c.APP_NAME, maximum_retries=self.retry_429_count)

        # Define network name to id mapping
        self._net_name_to_id = {}
        networks = self.dashboard.organizations.getOrganizationNetworks(self.org_id, total_pages='all')
        for network in networks:
            self.net_name_to_id[network['name']] = network['id']

    @classmethod
    def get_instance(cls):
        """
        Get Singleton instance of Meraki Class
        :return: Singleton instance of Meraki Class
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def net_name_to_id(self):
        """
        Get the net_name_to_id
        :return: The net_name_to_id dictionary
        """
        return self._net_name_to_id

    @net_name_to_id.setter
    def net_name_to_id(self, net_name_to_id: dict):
        """
        Set the net_name_to_id
        :param net_name_to_id: The net_name_to_id dict
        """
        self._net_name_to_id = net_name_to_id

    def upload_floorplan(self, network_id: str, floor_plan_config: dict) -> tuple[str | None, dict | str]:
        """
        Create Meraki Floor Plan on Network, return response or (error code, error message)
        https://developer.cisco.com/meraki/api-v1/create-network-floor-plan/
        :param network_id: Network ID
        :param floor_plan_config: Create Floor plan payload
        :return: Error Code (if relevant), Response (or Error Message)
        """
        try:
            response = self.dashboard.networks.createNetworkFloorPlan(network_id, **floor_plan_config)
            return None, response
        except meraki.APIError as e:
            return e.status, str(e)
        except Exception as e:
            # SDK Error
            return "500", str(e)

    def get_network_devices(self, network_id: str) -> tuple[str | None, dict | str]:
        """
        Get Network Devices, return response or (error code, error message)
        https://developer.cisco.com/meraki/api-v1/get-network-devices/
        :param network_id: Network ID
        :return: Error Code (if relevant), Response (or Error Message)
        """
        try:
            response = self.dashboard.networks.getNetworkDevices(network_id)
            return None, response
        except meraki.APIError as e:
            return e.status, str(e)
        except Exception as e:
            # SDK Error
            return "500", str(e)

    def update_network_devices(self, device_serial: str, device_config: dict) -> tuple[str | None, dict | str]:
        """
        Update Network Devices, return response or (error code, error message)
        https://developer.cisco.com/meraki/api-v1/update-device/
        :param device_config: New Device Config
        :param device_serial: Device Serial to Update
        :return: Error Code (if relevant), Response (or Error Message)
        """
        try:
            response = self.dashboard.devices.updateDevice(device_serial, **device_config)
            return None, response
        except meraki.APIError as e:
            return e.status, str(e)
        except Exception as e:
            # SDK Error
            return "500", str(e)


meraki_api = MERAKI_API.get_instance()  # Singleton instance of MERAKI_API
