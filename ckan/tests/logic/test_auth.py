import ckan.tests as tests
from ckan.logic import get_action
import ckan.model as model
import ckan.new_authz as new_authz
import json
from ckan.tests import StatusCodes

INITIAL_TEST_CONFIG_PERMISSIONS = {
    'anon_create_dataset': False,
    'create_dataset_if_not_in_organization': False,
    'user_create_groups': False,
    'user_create_organizations': False,
    'create_user_via_api': False,
}

new_authz.CONFIG_PERMISSIONS.update(INITIAL_TEST_CONFIG_PERMISSIONS)

class TestAction(tests.WsgiAppCase):

    @classmethod
    def setup_class(cls):
        admin_api = get_action('get_site_user')(
            {'model': model, 'ignore_auth': True}, {})['apikey']
        ## This is a mutable dict on the class level so tests can
        ## add apikeys as they go along
        cls.apikeys = {'sysadmin': admin_api, 'random_key': 'moo'}

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def _action_post(self, action, data, user, status=None):
        params='%s=1' % json.dumps(data)
        return self.app.post('/api/action/%s' % action,
                             params=params,
                             extra_environ={'Authorization': self.apikeys[user]},
                             status=status)

    def test_1_create_org(self):
        org = {'name': 'org_by_sysadmin',}
        self._action_post('organization_create', org, 'random_key', 403)
        self._action_post('organization_create', org, 'sysadmin')

    def test_2_create_users(self):
        user = {'name': 'user_no_auth',
                'password': 'pass',
                'email': 'moo@moo.com'}

        self._action_post('user_create', user, 'random_key', 403)
        res = self._action_post('user_create', user, 'sysadmin')

        self.apikeys['no_org'] = str(json.loads(res.body)['result']['apikey'])

        self._action_post('user_create', user, 'no_org', 403)

    def test_3_create_dataset_no_org(self):

        dataset = {'name': 'admin_create_no_org'}
        res = self._action_post('package_create', dataset, 'sysadmin', 200)

        dataset = {'name': 'should_not_be_created'}
        res = self._action_post('package_create', dataset, 'no_org', 403)

    def test_4_create_dataset_with_org(self):

        dataset = {'name': 'admin_create_with_org',
                   'owner_org': 'org_by_sysadmin'}
        res = self._action_post('package_create', dataset, 'sysadmin', 200)

        dataset = {'name': 'should_not_be_created2',
                   'owner_org': 'org_by_sysadmin'}
        res = self._action_post('package_create', dataset, 'no_org', 403)

    def test_5_add_user_to_org(self):

        user = {'name': 'user_as_admin',
                'password': 'pass',
                'email': 'moo@moo.com'}
        res = self._action_post('user_create', user, 'sysadmin')
        self.apikeys['with_org'] = str(json.loads(res.body)['result']['apikey'])

        member = {'username': 'user_as_admin',
                  'role': 'editor',
                  'id': 'org_by_sysadmin'}
        res = self._action_post('organization_member_create', member, 'no_org', 403)

        self._action_post('organization_member_create', member, 'sysadmin')

