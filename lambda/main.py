import boto3
import base64
import urllib3
import json
import re
import xml.etree.ElementTree as ET
import cgi
from botocore.auth import SigV4Auth
from botocore.credentials import Credentials
from botocore.awsrequest import AWSRequest

session = boto3.Session()
http = urllib3.PoolManager()


def xml_node_to_json(node):
    fields = {"@"+k: v for k, v in node.attrib}
    if len(node) == 0:
        fields['$content'] = node.text
    tag_groups = re.search("^({.*?})?(.*)$", node.tag).groups()
    if len(tag_groups) > 1:
        fields['$namespace'] = tag_groups[0][1:-1]
        tag = tag_groups[1]
    else:
        tag = tag_groups[0]

    for child in node:
        child_tag, child_fields = xml_node_to_json(child)
        if child_tag in fields:
            if isinstance(fields[child_tag], list):
                fields[child_tag].append(child_fields)
            else:
                fields[child_tag] = [fields[child_tag], child_fields]
        else:
            fields[child_tag] = child_fields
    return tag, fields


def lambda_handler(event, context):
    client = boto3.client(event['service'], region_name=event['region'])
    host = client._endpoint.host
    if event['host'] is not None:
        host = event['host']

    creds = session.get_credentials()
    # Credentials(
    #    'KEY_ID',
    #    'KEY_SECRET'
    # )

    sigv4 = SigV4Auth(creds,
                      event['service'], event['region'])

    url = host
    if event['path'] != '':
        if not event['path'].startswith("/"):
            event['path'] = "/" + event['path']
        url += event['path']

    data = None
    headers = event['headers']
    if event['body'] is not None:
        data = base64.b64decode(event['body'], validate=True)
        headers['Content-Length'] = "{}".format(len(data))
    headers['Content-Length'] = "0"

    request = AWSRequest(
        method=event['method'], url=url, data=data, params=event['query_parameters'], headers=headers)
    sigv4.add_auth(request)
    prepped = request.prepare()

    resp_dict = None
    if event['make_request']:
        response = http.request(
            event['method'], prepped.url, headers=prepped.headers, body=data)
        body = response.data
        body_base64 = base64.b64encode(body)
        is_utf_8 = True
        try:
            body.decode('utf-8')
        except UnicodeError:
            is_utf_8 = False

        mediatype, mediatype_options = cgi.parse_header(
            response.headers.get('content-type'))

        body_json = None
        if is_utf_8 and mediatype.lower() == "text/xml":
            xml_root = ET.fromstring(body)
            root_tag, xml_dict = xml_node_to_json(xml_root)
            body_json = json.dumps({
                root_tag: xml_dict
            })

        resp_dict = {
            'request_id': response.headers.get('x-amzn-RequestId'),
            'status': response.status,
            'reason': response.reason,
            'headers': response.headers,
            'body_base64': body_base64,
            'body_json': body_json,
            'body_is_utf_8': is_utf_8,
            'mediatype': mediatype,
            'mediatype_options': mediatype_options
        }

    return {
        "host": host,
        "url": prepped.url,
        "headers": prepped.headers._dict,
        "response": resp_dict
    }


# lambda_handler({
#    "service": "ec2",
#    "region": "us-east-1",
#    "method": "GET",
#    "host": None,
#    "path": "",
#    "query_parameters": {
#        "Action": "DescribeRegions",
#        "Version": "2013-10-15"
#    },
#    "headers": {},
#    "body": None,
#    "make_request": True
# }, None)
