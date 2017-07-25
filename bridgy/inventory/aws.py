from inventory.source import InventorySource, Instance
from config import Config

import boto3
import placebo


class AwsInventory(InventorySource):

    @property
    def name(self): return 'aws'

    def __init__(self):
        session = boto3.Session(
            aws_access_key_id=Config['aws']['access_key_id'],
            aws_secret_access_key=Config['aws']['secret_access_key'],
            aws_session_token=Config['aws']['session_token'],
            region_name=Config['aws']['region']
        )
        self.pill = placebo.attach(
            session, data_path=Config.inventoryDir(self.name))

        self.client = session.client('ec2')

    def update(self):
        self.__ec2(stub=False)

    def instances(self, stub=True):
        data = self.__ec2(stub=stub)

        instances = []
        for reservation in data['Reservations']:
            for instance in reservation['Instances']:

                # try to find the best dns/ip address to reach this box
                address = None
                if instance['PublicDnsName']:
                    address = instance['PublicDnsName']
                elif instance['PrivateIpAddress']:
                    address = instance['PrivateIpAddress']

                # try to find the best field to match a name against
                name = None
                if 'Tags' in instance.keys():
                    for tagDict in instance['Tags']:
                        if tagDict['Key'] == 'Name':
                            name = tagDict['Value']
                            break

                if name == None:
                    if instance['PublicDnsName']:
                        name = instance['PublicDnsName']
                    elif instance['PrivateDnsName']:
                        name = instance['PrivateDnsName']

                # take note of this instance
                if name != None and address != None:
                    instances.append(Instance(name, address))

        return instances

    def __ec2(self, tag=None, value=None, stub=True):
        filters = []
        if value:
            filters.append({
                'Name': 'tag:' + tag,
                'Values': [value]
            })

        if stub:
            self.pill.playback()
            data = self.client.describe_instances(Filters=filters)
        else:
            self.pill.record()
            data = self.client.describe_instances(Filters=filters)
            self.pill.stop()
        return data
