import getpass
import requests
import json

def getTagName():
	response = requests.get('http://169.254.169.254/latest/meta-data/instance-id')
	instance_id = response.text
	region_response = requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document')
	text = json.loads(region_text)
	region = text['region']

	ec2 = boto3.resource('ec2', region_name=region)
	instance = ec2.Instance(instance_id)
	tag = instance.tags
	name = tag[0]['Value']