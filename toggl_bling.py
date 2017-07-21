#!/usr/bin/python
import requests
import json
import datetime
import getpass
import sys
import yaml
from os.path import expanduser
from requests.auth import HTTPBasicAuth

toggl_things = []
config = {}

def main():  
    date_from = ""
    date_to = ""
    email = config['toggl']['email']
    toggl_workspace_id = config['toggl']['workspace_id']
    api_token = config['toggl']['api_token']
    api_path = config['toggl']['api_path']

    # Get date to import from args - should be yyyy-mm-dd format
    date_from = str(sys.argv[1])

    if len(sys.argv) > 2:
        date_to = str(sys.argv[2])

    if date_from == "today":
        date_from = str(datetime.date.today())

    if date_from == "yesterday":
        date_from = str(datetime.date.today() - datetime.timedelta(1))

    # Validate date string
    try:
        datetime.datetime.strptime(date_from, '%Y-%m-%d')

        if date_to == "":
            date_to = date_from

    except ValueError:
        raise ValueError("Incorrect date format expected YYYY-MM-DD 'today' or 'yesterday'")
        return

    api_url = "https://www.toggl.com/reports/api/v2{}?user_agent={}&workspace_id={}&since={}&until={}".format(api_path, email, toggl_workspace_id, date_from, date_to)

    # Got here with no exceptions
    headers = {
        "content-type": "application/json",
    }

    r = requests.get(api_url,
        headers=headers,
        auth=HTTPBasicAuth(api_token, "api_token")
    )

    stuff = json.loads(r.text)
    items = stuff['data']

    for thing in items:
        task_id = thing['id']
        desc = thing['description']
        start = thing['start']
        dur_mins = round(thing['dur'] / 1000 / 60)
        client = thing['client']
        project = thing['project']

        toggl_things.append({
            'client': client,
            'project': project,
            'description': desc,
            'start': start,
            'duration': dur_mins,
        })

    if len(toggl_things) > 0:
        print("\n\n==== SUMMARY for {} to {} ====".format(date_from, date_to))

        for thing in toggl_things:
            print("{} at {} mins at {}".format(thing['description'], thing['duration'], thing['start']))

        send_yn = raw_input("\nSend to bling? ")

        if (send_yn == "y"):
            send_to_bling()
        else:
            print("Aborted.")
            return
    else:
        print("Nothing to process, aborting.")
        return


def send_to_bling():
    user = config['bling']['ldap_user']
    user_pw = getpass.getpass('Bling password: ')

    base_url = config['bling']['base_url']
    billing_agent_project_id = config['bling']['billing_agent_project_id']
    rate_id = config['bling']['rate_id']

    api_endpoint = base_url + config['bling']['endpoint']

    headers = {
        'content-type': 'application/x-www-form-urlencoded',
    }

    for item in toggl_things:
        payload = {
            'username': user,
            'password': user_pw,
            'project_id': billing_agent_project_id,
            'task_id': '',
            'type_id': rate_id,
            'date': item['start'],
            'time': item['duration'],
            'time_client': item['duration'],
            'details': item['description'],
        }

        p = requests.post(api_endpoint, data = payload, headers = headers)

        if p.status_code != 200:
            sys.exit("[HTTP {}] when sending bling for {}".format(p.status_code, item['description']))            
        else:
            print("Logged {} at {} mins at {}    [OK]".format(item['description'], item['duration'], item['start']))


if __name__ == '__main__':
    # Load config from dotfile
    config_path = expanduser("~/.config/toggl_bling/config.yml")
    config = yaml.safe_load(open(config_path))
    main()
