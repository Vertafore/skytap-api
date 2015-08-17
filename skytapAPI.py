"""
Copyright 2014 Vertafore Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import json
import time
import requests
import collections


#region Utility Functions
def fibonacci():
    """
    Generator for Fibonacci numbers.
    """
    a, b = 1, 1
    while True:
        yield a
        a, b = b, a + b


def poll(tries, initial_delay, retry_list, api_function, *args, **kwargs):
    """
    Poll an api object with fibonacci back off.
    Requires the api object to return a response object.
    """
    fibs = fibonacci()
    time.sleep(initial_delay)
    status_code = None
    for n in range(tries):
        r = api_function(*args, **kwargs)
        status_code = r.status_code
        if status_code in retry_list:
            polling_time = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
            delay = next(fibs)
            print("{}. Sleeping for {} seconds.".format(polling_time, delay))
            time.sleep(delay)
        else:
            return r
    raise ExceededRetries("Failed poll {} within {} tries.\nStatus Code: {}".format(api_function, tries, status_code))
# endregion


class ExceededRetries(StopIteration):
    pass


class AbstractDataProvider():
    """A list of methods that data providers should implement or extend."""

    def __init__(self, base_url, username=None, password=None):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password

    def request(self, request_type, path, params=None, data=None, files=None, response_type='json',
                response_codes=None, api_version='v1'):
        """
        Handles requests for each api call to a data provider
        and returns the expected data. If the request fails, print debugging information.
        """

        # to avoid the Mutable Default Argument trap
        if response_codes is None:
            response_codes = [requests.codes.ok]

        if api_version == 'v1':
            headers = {'content-type': 'application/json', 'accept': 'application/json'}
        elif api_version == 'v2':
            headers = {'content-type': 'application/json', 'accept': 'application/vnd.skytap.api.v2+json'}
            path = 'v2/{}'.format(path)
        else:
            raise ValueError('Unknown API Version "{}"'.format(api_version))

        path = path.rstrip('/')
        url = '{}/{}'.format(self.base_url, path)
        if data:
            data = json.dumps(data)
        r = requests.request(request_type, url, auth=(self.username, self.password),
                             headers=headers, params=params, data=data, files=files)
        if r.status_code not in response_codes:
            r.raise_for_status()
        if response_type == 'json':
            return r.json()
        elif response_type == 'content':
            return r.content
        elif response_type == 'text':
            return r.text
        elif response_type == 'response':
            return r
        else:
            pass  # no response type specified or implemented.


class SkytapAPI(AbstractDataProvider):
    """
    Interacts with the Skytap RESTful API.
    """
    def __init__(self, base_url, username, password):
        super().__init__(base_url, username, password)

    #region Class Methods

    # Skytap api endpoints
    @classmethod
    def users(cls, user_id):
        return 'users/{}'.format(user_id)

    @classmethod
    def configs(cls, config_id):
        return 'configurations/{}'.format(config_id)

    @classmethod
    def publish_set(cls, config_id, publish_set_id):
        return '{}/publish_sets/{}'.format(cls.configs(config_id), publish_set_id)

    @classmethod
    def department(cls, department_id):
        return 'departments/{}'.format(department_id)

    @classmethod
    def departments(cls, count, offset):
        return 'departments?count={}&offset={}'.format(count, offset)

    @classmethod
    def department_users(cls, department_id, count, offset):
        return '{}/users?count={}&offset={}'.format(cls.department(department_id), count, offset)

    @classmethod
    def vms(cls, config_id, vm_id):
        return '{}/vms/{}'.format(cls.configs(config_id), vm_id)

    @classmethod
    def networks(cls, config_id, network_id):
        return '{}/networks/{}'.format(cls.configs(config_id), network_id)

    @classmethod
    def projects(cls, project_id):
        return 'projects/{}'.format(project_id)

    @classmethod
    def project_configurations(cls, project_id, configuration_id):
        return '{}/configurations/{}'.format(cls.projects(project_id), configuration_id)

    @classmethod
    def project_project_templates(cls, project_id):
        return '{}/templates'.format(cls.projects(project_id))

    @classmethod
    def interfaces(cls, config_id, vm_id, interface_id):
        return '{}/interfaces/{}'.format(cls.vms(config_id, vm_id), interface_id)

    @classmethod
    def services(cls, config_id, vm_id, interface_id, service_id):
        return '{}/services/{}'.format(cls.interfaces(config_id, vm_id, interface_id), service_id)

    @classmethod
    def vpns(cls, vpn_id):
        return 'vpns/{}'.format(vpn_id)

    @classmethod
    def template(cls, template_id):
        return 'templates/{}'.format(template_id)

    @classmethod
    def ips(cls, ip_id):
        return 'ips/{}'.format(ip_id)
    # endregion

    # region Public IP Resource
    def get_ips(self, ip_id=''):
        path = self.ips(ip_id)
        return self.request('get', path)
    # endregion

    # region Configuration Resource
    def get_config(self, config_id=''):
        """
        Get all configurations. If config id is specified, get a particular configuration.
        """
        path = self.configs(config_id)
        return self.request('get', path)

    def create_config(self, template_id):
        """
        Create a configuration. Takes mandatory template id as a parameter.
        """
        path = self.configs('')
        data = {'template_id': template_id}
        return self.request('post', path, data=data)

    def delete_config(self, config_id):
        """
        Delete an existing configuration.
        Does not return
        """
        path = self.configs(config_id)
        # noinspection PyTypeChecker
        self.request('delete', path, response_type=None)

    def update_config(self, config_id, attr, value):
        """
        Update an existing configuration.
        """
        path = self.configs(config_id)
        params = {attr: value}
        return self.request('put', path, params)

    def config_restart_multiselect(self, config_id, vm_list):
        """
        Restart multiple VMs in a config
        :param config_id:
        :param vm_list:
        :return:
        """
        path = self.configs(config_id)
        d = {"runstate": "running", "multiselect": "{}".format(vm_list)}
        params = d
        return self.request('put', path, params)

    def config_shutdown_multiselect(self, config_id, vm_list):
        """
        Shutdown multiple VMs in a config
        :param config_id:
        :param vm_list:
        :return:
        """
        path = self.configs(config_id)
        d = {"runstate": "stopped", "multiselect": "{}".format(vm_list)}
        params = d
        return self.request('put', path, params)
    #endregion
    #region templates
    def get_template(self, template_id):
        """
        :param template_id:
        :return:
        """
        path = self.template(template_id)
        return self.request('get', path)

    def template_create_multiselect(self, config_id, vm_list):
        """
        Create a template from a list of VMs
        :param config_id:
        :param vm_list:
        :return:
        """
        path = self.template('')
        params = {"configuration_id": "{}".format(config_id), "vm_instance_multiselect": "{}".format(vm_list)}
        return self.request('post', path, params)

    def update_template(self, template_id, attr, value):
        """
        Update a value in the template
        :param template_id:
        :param attr:
        :param value:
        :return:
        """
        path = self.template(template_id)
        params = {attr: value}
        return self.request('put', path, params)

    def delete_template(self, template_id):
        """
        Delete an existing template.
        Does not return
        """
        path = self.template(template_id)
        # noinspection PyTypeChecker
        self.request('delete', path, response_type=None)

    #endregion

    #region User Resource
    def get_user(self, user_id=''):
        """
        Gets all users. If user id is specified, gets a particular user.
        """
        path = self.users(user_id)
        return self.request('get', path)

    def add_user(self, first_name, last_name, login_name, email, title='', account_role='standard_user',
                 time_zone='Pacific Time (US & Canada)', can_export='false', can_import='false',
                 has_public_library='false', sso_enabled='true'):
        """
        Add a new user. Required fields are login_name, email, fist name and last name
        """

        params = locals().copy()
        del params['self']

        path = self.users('')

        return self.request('post', path, params)

    def update_user(self, user_id, attr, value):
        """
        Update a user attribute
        Update a user attribute
        """
        path = self.users(user_id)
        params = {attr: value}
        return self.request('put', path, params)
    #endregion

    #region Department Resource
    def get_departments(self, count=100, offset=0):
        """
        Get the department
        """
        path = self.departments(count, offset)
        return self.request('get', path)

    def get_department(self, department_id=''):
        """
        Get the department
        """
        path = self.department(department_id)
        return self.request('get', path)

    def get_department_users(self, department_id, count=100, offset=0):
        """
        Get the department users
        """
        path = self.department_users(department_id, count, offset)
        return self.request('get', path)

    def add_user_to_department(self, user_id, department_id):
        """
        Add a user to a department
        :param user_id:
        :param department_id:
        :return:
        """
        path = '{}/users/{}'.format(self.department(department_id), user_id)
        return self.request('post', path)

    def set_department_limits(self, department_id, svm_hours=None, concurrent_svms=None, storage=None,
                              concurrent_vms=None):
        path = '{}/quotas'.format(self.department(department_id))
        data = [{'id': 'svm_hours',         'limit': svm_hours},
                  {'id': 'concurrent_svms',   'limit': concurrent_svms},
                  {'id': 'storage',           'limit': storage},
                  {'id': 'concurrent_vms',    'limit': concurrent_vms}]

        return self.request('put', path, data=data, api_version='v2')

    def set_department_description(self, department_id, description):
        path = self.department(department_id)
        params = {'description': description}
        return self.request('put', path, params=params, api_version='v2')

    def get_department_usage(self, department_id):
        path = '{}/quotas'.format(self.department(department_id))
        return self.request('get', path)

    #endregion

    #region VPN Resource
    def get_vpn(self, vpn_id=''):
        """
        Get VPN
        :param vpn_id:
        :return:
        """
        path = self.vpns(vpn_id)
        return self.request('get', path)
    #endregion

    #region Publish Set Resource
    def get_publish_set(self, config_id, publish_set=''):
        """
        Get the publish set
        :param config_id:
        :param publish_set:
        :return:
        """
        path = self.publish_set(config_id, publish_set)
        return self.request('get', path)

    def delete_publish_set(self, config_id, publish_set):
        """
        Delete the publish set
        :param config_id:
        :param publish_set:
        :return:
        """
        path = self.publish_set(config_id, publish_set)
        # noinspection PyTypeChecker
        self.request('delete', path, response_type=None)
    #endregion

    #region VM Resource
    def get_vm(self, config_id, vm_id=''):
        """
        Get all vms for a configuration. If a vm id is specified, get a particular vm.
        """
        path = self.vms(config_id, vm_id)
        return self.request('get', path)

    def update_vm(self, config_id, vm_id, attr, value):
        """
        Update an existing configuration.
        """
        path = self.vms(config_id, vm_id)
        params = {attr: value}
        return self.request('put', path, params)
    #endregion

    #region Publish Service Resource
    def get_published_service(self, config_id, vm_id, interface_id, service_id=''):
        """
        Gets all published services. If service id is specified, get a particular service.
        """
        path = self.services(config_id, vm_id, interface_id, service_id)
        return self.request('get', path)

    def delete_published_service(self, config_id, vm_id, interface_id, service_id):
        """
        Delete a published service on a Skytap VM.
        """
        path = self.services(config_id, vm_id, interface_id, service_id)
        retry_codes = [requests.codes.conflict, requests.codes.locked]
        response_codes = [requests.codes.ok, requests.codes.conflict, requests.codes.locked]
        poll(10, 0, retry_codes, self.request, 'delete', path, response_codes=response_codes, response_type='response')

    def add_published_service(self, config_id, vm_id, interface_id, service_id):
        """
        Add a published service to a Skytap VM.
        """
        path = self.services(config_id, vm_id, interface_id, '')
        params = {'port': service_id}
        return self.request('post', path, params)
    #endregion

    #region Network Interface Resource
    def get_interface(self, config_id, vm_id, interface_id=''):
        """
        Get all interfaces for a configuration. If an interface id is specified, get a particular interface.
        """
        path = self.interfaces(config_id, vm_id, interface_id)
        return self.request('get', path)

    def create_interface(self, config_id, vm_id):
        """
        Create a nic on a VM in a configuration.
        This API is undocumented in Skytap documentation
        """
        path = self.interfaces(config_id, vm_id, '')
        return self.request('post', path)

    def attach_interface(self, config_id, vm_id, interface_id, network_id):
        """
        Attach a nic to an existing network. Defaults to first network in Configuration.
        This API is undocumented in Skytap documentation
        """
        path = self.interfaces(config_id, vm_id, interface_id)
        params = {'network_id': network_id}
        return self.request('put', path, params)
    #endregion

    #region Network Resource
    def get_network(self, config_id, network_id=''):
        """
        Get all networks for a configuration. If a network id is specified, get a particular network.
        """
        path = self.networks(config_id, network_id)
        return self.request('get', path)
    #endregion

    #region Project Resource
    def get_project(self, project_id=''):
        """
        get projects
        :param project_id:
        :return:
        """
        path = self.projects(project_id)
        return self.request('get', path)

    def get_project_configurations(self, project_id, configuration_id=''):
        """
        get configurations in a project
        :param project_id:
        :param configuration_id:
        :return:
        """
        path = self.project_configurations(project_id, configuration_id)
        return self.request('get', path)

    def get_project_templates(self, project_id):
        """
        :param project_id:
        :param template_id:
        :return:
        """
        path = self.project_project_templates(project_id)
        return self.request('get', path)


    def add_configuration_to_project(self, project_id, configuration_id):
        """
        Add a configuration to a project
        :param project_id:
        :param configuration_id:
        :return:
        """
        path = self.project_configurations(project_id, configuration_id)
        return self.request('post', path)

    def add_template_to_project(self, project_id, template_id):
        """
        Add a template to a project
        :param template_id:
        :param project_id:
        :return:
        """
        path = '{}/templates/{}'.format(self.projects(project_id), template_id)
        return self.request('post', path)
    #endregion

    pass # End of file so the region comment will close properly in PyCharm
