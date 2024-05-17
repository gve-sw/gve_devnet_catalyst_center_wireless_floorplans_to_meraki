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

import base64
import os
import sys
import tarfile
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import PosixPath

from PIL import Image
from rich.prompt import Prompt, Text

from cat_center_api import cat_center_api
from config.config import c
from logger.logrr import lm
from meraki_api import meraki_api


def encode_image_to_base64(directory_path: PosixPath) -> str | None:
    """
    Encode the floor plan image to base64 format
    :param directory_path: Path to Export Image Directory
    :return: Base64 Encoded string (or None)
    """
    # List all files in the directory
    files = os.listdir(directory_path)
    # Filter for the JPEG image
    jpeg_file = next((file for file in files if file.endswith('.jpg')), None)
    if jpeg_file:
        # Complete path to the image
        image_path = os.path.join(directory_path, jpeg_file)

        try:
            # Open the image
            with Image.open(image_path) as img:
                # Prepare the image to be encoded
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                # Encode the image to base64
                img_base64 = base64.b64encode(buffered.getvalue())
                return img_base64.decode('utf-8')
        except Exception as e:
            lm.lnp(f"Error: Unable to base64 encode JPG: {str(e)}", level="error")
            return None
    else:
        lm.lnp(f"Error: Unable to find floor plan JPG.", level="error")
        return None


def main():
    """
    Main function to migrate Catalyst Center Wireless Floor Maps to Meraki
    """
    lm.print_start_panel(app_name=c.APP_NAME)  # Print the start info message to console
    lm.print_config_table(config_instance=c)  # Print the config table

    # Provide Catalyst Center Source Floor and Target Meraki Network
    lm.p_panel(f"Provide Catalyst Center Source Floor", title="Step 1")

    # Obtain list of all available floors to id mapping
    floors_to_id_mapping = cat_center_api.site_floor_hierachy_to_id_mapping()

    if floors_to_id_mapping and len(floors_to_id_mapping) > 0:
        # Found Floors!
        lm.lnp(f"Found the following Valid Floors: {list(floors_to_id_mapping.keys())}")
        selected_floor = Prompt.ask(Text("Select a Valid Source Floor (from the list above)", style="green"),
                                    choices=list(floors_to_id_mapping.keys()), show_choices=False)
        source_floor = floors_to_id_mapping[selected_floor]

    else:
        # No Floors found, exiting...
        lm.lnp(f"Error: No valid floors found.", level="error")
        sys.exit(-1)

    # Start Export Mapp Archive, return task id
    lm.p_panel(f"Exporting Map Archive from Catalyst Center", title="Step 2")
    export_task = cat_center_api.export_map_archive(source_floor['id'])
    if export_task:
        # Export Started, trigger while loop waiting until the export completes
        task_data = cat_center_api.get_task_result(export_task['taskId'])

        if task_data:
            # If task_data not none, we have successfully retrieved the task data! - Download Archive File
            filename = cat_center_api.download_file_by_fileid(task_data)

            # Extract the file
            if filename.endswith("tar.gz"):
                try:
                    with tarfile.open(c.ARCHIVE_PATH / filename, "r:gz") as tar:
                        folder_path = c.ARCHIVE_PATH / filename.split(".")[0]
                        tar.extractall(path=folder_path)

                        # Remove tar.gz
                        os.remove(c.ARCHIVE_PATH / filename)
                    lm.lnp(f"File extracted successfully to: {folder_path}", level="success")
                except tarfile.TarError as e:
                    lm.lnp(f"Error extracting the tar file: {e}", level="error")
                    return None

        else:
            # Unable to Export Map Archive
            lm.lnp(f"Error: Unable to Export Map Archive for Floor.", level="error")
            sys.exit(-1)
    else:
        # Unable to Export Map Archive
        lm.lnp(f"Error: Unable to Export Map Archive for Floor.", level="error")
        sys.exit(-1)

    lm.p_panel(f"Provide Meraki Network Destination Floor", title="Step 3")
    meraki_networks = list(meraki_api._net_name_to_id.keys())
    if len(meraki_networks) > 0:
        # Found Networks!
        lm.lnp(f"Found the following Networks: {meraki_networks}")
        selected_network = Prompt.ask(Text("Select an Valid Meraki Network (from the list above)", style="green"),
                                      choices=meraki_networks, show_choices=False)
        destination_network_id = meraki_api._net_name_to_id[selected_network]
    else:
        # Unable to Export Map Archive
        lm.lnp(f"Error: No Meraki networks found.", level="error")
        sys.exit(-1)

    lm.p_panel(f"Create Meraki Floor Plan on Destination Floor", title="Step 4")
    floor_plan_contents = {"name": selected_floor.split("/")[-1]}

    # Get Base64 encoded floor plan image
    image_path = folder_path / "images"
    encoded_image = encode_image_to_base64(image_path)

    if encoded_image:
        floor_plan_contents['imageContents'] = encoded_image
    else:
        sys.exit(-1)

    # Load XML Coordinate Data for map:
    xml_path = folder_path / "xmlDir" / "MapsImportExport.xml"
    tree = ET.parse(xml_path)
    root = tree.getroot()

    namespace = {'ns': 'http://importexport.cisco.com/1.0'}

    # Find the 'CivicAddress' element (building coordinates) with the namespace prefix
    civic_address = root.find('.//ns:CivicAddress', namespaces=namespace)
    civic_lat = float(civic_address.get('latitude'))
    civic_long = float(civic_address.get('longitude'))

    if civic_address is not None:
        floor_plan_contents['center'] = {'lat': civic_lat, 'lng': civic_long}
    else:
        lm.lnp(f"Error: CivicAddress element not found in XML", level="error")
        sys.exit(-1)

    # Upload Floor Plan to Meraki
    error, response = meraki_api.upload_floorplan(destination_network_id, floor_plan_contents)
    if error:
        lm.lnp(f"Error: Unable to Upload Floor Plan to Meraki: {response}", level="error")
        sys.exit(-1)
    else:
        lm.lnp(f"Successfully Uploaded Floor plan to Meraki Network: {selected_network}", level="success")

    # Associate All Devices which match mac addresses of devices within Meraki network in the XML from Catalyst Center
    floor_plan_id = response['floorPlanId']

    error, network_devices = meraki_api.get_network_devices(destination_network_id)
    mac_to_serial = {device['mac']: device['serial'] for device in network_devices}

    # Find all 'PlannedAp' elements with the namespace prefix
    planned_aps = root.findall('.//ns:PlannedAp', namespaces=namespace)

    if planned_aps:
        for ap in planned_aps:
            mac_address = ap.get('macAddress')
            if mac_address and mac_address in mac_to_serial:
                # Found a matching device in the Meraki network!
                serial = mac_to_serial[mac_address]
                lm.lnp(f"Associating Device with MAC Address: {mac_address} to Floor Plan: {floor_plan_id}",
                       level="info")
                # Associate the device to FloorPlan
                device_config = {'floorPlanId': floor_plan_id, 'lat': civic_lat, 'lng': civic_long}
                error, response = meraki_api.update_network_devices(serial, device_config)

                if error:
                    lm.lnp(
                        f"Error: Unable to Associate Device with MAC Address: {mac_address} to Floor Plan: {floor_plan_id}: {response}",
                        level="error")
                    sys.exit(-1)
                else:
                    lm.lnp(
                        f"Successfully associated device {serial} to FloorMap {floor_plan_id} at lat ({civic_lat}), lng ({civic_long})",
                        level="success")
    else:
        lm.lnp(f"Error: No PlannedAp elements found", level="error")
        sys.exit(-1)


if __name__ == '__main__':
    main()
