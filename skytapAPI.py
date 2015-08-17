import os
import skytapAPI
import ast
import json
import pprint
from reporting import SCE_SVM_App_Usage as sce_usage


skytap_user = os.environ['SKYTAP_USER']
skytap_api_key = os.environ['SKYTAP_API_KEY']
api = skytapAPI.SkytapAPI('https://cloud.skytap.com', skytap_user, skytap_api_key)

departments = api.get_department()

sce = sce_usage.svms_per_app()
department_svms = {}
sce_svms = 0
for app in sce:
    svms = 0
    if sce_usage.departments[app] in department_svms:
        svms = department_svms[sce_usage.departments[app]]
    svms += sce[app]
    department_svms[sce_usage.departments[app]] = svms
    sce_svms += sce[app]

data = {}
data['departments'] = []

for department in departments:
    usage = api.get_department_usage(department['id'])
    svms = 0
    for use in usage:
        if use['id'] == 'concurrent_svms':
            svms = use['usage']
    if department['name'] in department_svms:
        svms += department_svms[department['name']]

    description = ast.literal_eval(department['description'])
    department_name = department['name']
    if department_name == 'TSO':
        svms -= sce_svms
    users = []
    department_users = api.get_department_users(department['id'])
    for user in department_users:
        users.append(user['email'])
    data['departments'].append({'name': department_name, 'vp': description['VP'], 'quota': description['Quota'],
                                'used': svms, 'users': users})

print(json.dumps(data))
