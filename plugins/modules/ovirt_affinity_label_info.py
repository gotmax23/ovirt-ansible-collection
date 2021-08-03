#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 Red Hat, Inc.
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
---
module: ovirt_affinity_label_info
short_description: Retrieve information about one or more oVirt/RHV affinity labels
version_added: "1.0.0"
author: "Ondra Machacek (@machacekondra)"
description:
    - "Retrieve information about one or more oVirt/RHV affinity labels."
    - This module was called C(ovirt_affinity_label_facts) before Ansible 2.9, returning C(ansible_facts).
      Note that the M(@NAMESPACE@.@NAME@.ovirt_affinity_label_info) module no longer returns C(ansible_facts)!
notes:
    - "This module returns a variable C(ovirt_affinity_labels), which
       contains a list of affinity labels. You need to register the result with
       the I(register) keyword to use it."
options:
    name:
        description:
            - "Name of the affinity labels which should be listed."
        type: str
    vm:
        description:
            - "Name of the VM, which affinity labels should be listed."
        type: str
    host:
        description:
            - "Name of the host, which affinity labels should be listed."
        type: str
extends_documentation_fragment: @NAMESPACE@.@NAME@.ovirt_info
'''

EXAMPLES = '''
# Examples don't contain auth parameter for simplicity,
# look at ovirt_auth module to see how to reuse authentication:

# Gather information about all affinity labels, which names start with C(label):
- @NAMESPACE@.@NAME@.ovirt_affinity_label_info:
    name: label*
  register: result
- ansible.builtin.debug:
    msg: "{{ result.ovirt_affinity_labels }}"

# Gather information about all affinity labels, which are assigned to VMs
# which names start with C(postgres):
- @NAMESPACE@.@NAME@.ovirt_affinity_label_info:
    vm: postgres*
  register: result
- ansible.builtin.debug:
    msg: "{{ result.ovirt_affinity_labels }}"

# Gather information about all affinity labels, which are assigned to hosts
# which names start with C(west):
- @NAMESPACE@.@NAME@.ovirt_affinity_label_info:
    host: west*
  register: result
- ansible.builtin.debug:
    msg: "{{ result.ovirt_affinity_labels }}"

# Gather information about all affinity labels, which are assigned to hosts
# which names start with C(west) or VMs which names start with C(postgres):
- @NAMESPACE@.@NAME@.ovirt_affinity_label_info:
    host: west*
    vm: postgres*
  register: result
- ansible.builtin.debug:
    msg: "{{ result.ovirt_affinity_labels }}"
'''

RETURN = '''
ovirt_affinity_labels:
    description: "List of dictionaries describing the affinity labels. Affinity labels attributes are mapped to dictionary keys,
                  all affinity labels attributes can be found at following url: http://ovirt.github.io/ovirt-engine-api-model/master/#types/affinity_label."
    returned: On success.
    type: list
'''

import fnmatch
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.@NAMESPACE@.@NAME@.plugins.module_utils.ovirt import (
    check_sdk,
    create_connection,
    get_dict_of_struct,
    ovirt_info_full_argument_spec,
    search_by_name,
)


def main():
    argument_spec = ovirt_info_full_argument_spec(
        name=dict(default=None),
        host=dict(default=None),
        vm=dict(default=None),
    )
    module = AnsibleModule(argument_spec)
    check_sdk(module)
    if module.params['fetch_nested'] or module.params['nested_attributes']:
        module.deprecate(
            "The 'fetch_nested' and 'nested_attributes' are deprecated please use 'follow' parameter",
            version='2.0.0',
            collection_name='ovirt.ovirt'
        )

    try:
        auth = module.params.pop('auth')
        connection = create_connection(auth)
        affinity_labels_service = connection.system_service().affinity_labels_service()
        labels = []
        all_labels = affinity_labels_service.list()
        if module.params['name']:
            labels.extend([
                l for l in all_labels
                if fnmatch.fnmatch(l.name, module.params['name'])
            ])
        if module.params['host']:
            hosts_service = connection.system_service().hosts_service()
            if search_by_name(hosts_service, module.params['host']) is None:
                raise Exception("Host '%s' was not found." % module.params['host'])
            labels.extend([
                label
                for label in all_labels
                for host in connection.follow_link(label.hosts)
                if fnmatch.fnmatch(hosts_service.service(host.id).get().name, module.params['host'])
            ])
        if module.params['vm']:
            vms_service = connection.system_service().vms_service()
            if search_by_name(vms_service, module.params['vm']) is None:
                raise Exception("Vm '%s' was not found." % module.params['vm'])
            labels.extend([
                label
                for label in all_labels
                for vm in connection.follow_link(label.vms)
                if fnmatch.fnmatch(vms_service.service(vm.id).get().name, module.params['vm'])
            ])

        if not (module.params['vm'] or module.params['host'] or module.params['name']):
            labels = all_labels

        result = dict(
            ovirt_affinity_labels=[
                get_dict_of_struct(
                    struct=l,
                    connection=connection,
                    fetch_nested=module.params.get('fetch_nested'),
                    attributes=module.params.get('nested_attributes'),
                ) for l in labels
            ],
        )
        module.exit_json(changed=False, **result)
    except Exception as e:
        module.fail_json(msg=str(e), exception=traceback.format_exc())
    finally:
        connection.close(logout=auth.get('token') is None)


if __name__ == '__main__':
    main()
