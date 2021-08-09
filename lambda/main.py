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
    if node.text == None or node.text.strip() == '':
        fields['$content'] = None
    else:
        fields['$content'] = node.text
    tag_groups = re.search("^({.*?})?(.*)$", node.tag).groups()
    if tag_groups[0] is not None:
        fields['$namespace'] = tag_groups[0][1:-1]
    else:
        fields['$namespace'] = None
    tag = tag_groups[1]

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
    # FOR TESTING LOCALLY
    # creds = Credentials(
    #    'KEY',
    #    'SECRET'
    # )

    sigv4 = SigV4Auth(creds,
                      event['service'], event['region'])

    url = host
    if event['path'] != '':
        if not event['path'].startswith("/"):
            event['path'] = "/" + event['path']
        url += event['path']

    original_headers_lower = [k.lower() for k in event['headers'].keys()]

    data = None
    headers = event['headers']
    headers['Content-Length'] = "0"
    if event['body'] is not None:
        data = base64.b64decode(event['body'], validate=True)
        headers['Content-Length'] = "{}".format(len(data))

    request = AWSRequest(
        method=event['method'], url=url, data=data, params=event['query_parameters'], headers=headers)
    sigv4.add_auth(request)
    prepped = request.prepare()

    request_headers = {}
    generated_headers = {}
    for k, v in prepped.headers.items():
        request_headers[k] = v
        if k.lower() not in original_headers_lower:
            generated_headers[k] = v

    resp_dict = None
    if event['make_request']:
        response = http.request(event['method'], prepped.url, headers=prepped.headers, body=data, retries=urllib3.Retry(
            connect=event['retries_connect'],
            read=event['retries_read'],
            redirect=event['retries_redirect'],
            status=event['retries_status'],
            other=event['retries_other'],
            backoff_factor=event['retries_backoff_factor'],
            raise_on_redirect=event['retries_raise_on_redirect'],
            raise_on_status=event['retries_raise_on_status'],
            status_forcelist=event['retries_status_forcelist'],
            respect_retry_after_header=event['retries_respect_retry_after_header']
        ))
        body = response.data
        body_base64 = base64.b64encode(body)
        is_utf_8 = True
        try:
            body.decode('utf-8')
        except UnicodeError:
            is_utf_8 = False

        mediatype, mediatype_parameters = cgi.parse_header(
            response.headers.get('content-type'))

        body_obj = None
        if is_utf_8 and mediatype.lower() == "text/xml":
            xml_root = ET.fromstring(body)
            root_tag, xml_dict = xml_node_to_json(xml_root)
            body_obj = {
                root_tag: xml_dict
            }
        elif is_utf_8 and mediatype.lower() == "application/json":
            # Decode and re-encode to ensure output consistency
            try:
                body_obj = json.loads(body)
            except Exception:
                pass

        resp_headers = {k: v for k, v in response.headers.items()}

        resp_dict = {
            'aws_request_id': response.headers.get('x-amzn-RequestId'),
            'status_code': response.status,
            'status_reason': response.reason,
            'headers': resp_headers,
            'body_base64': body_base64,
            'body_object': body_obj,
            'body_is_utf_8': is_utf_8,
            'mediatype': mediatype,
            'mediatype_parameters': mediatype_parameters
        }

    return {
        "host": host,
        "url": prepped.url,
        "headers": request_headers,
        "generated_headers": generated_headers,
        "response": resp_dict
    }


# FOR TESTING LOCALLY
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
#    "make_request": True,
#    "body": None,
#    "make_request": True,
#    'retries_connect': 3,
#    'retries_read': 3,
#    'retries_redirect': 3,
#    'retries_status': 3,
#    'retries_other': 3,
#    'retries_backoff_factor': 0.1,
#    'retries_raise_on_redirect': True,
#    'retries_raise_on_status': True,
#    'retries_status_forcelist': [400, 401]
# }, None)
