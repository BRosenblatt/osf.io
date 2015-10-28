# -*- coding: utf-8 -*-
import httplib as http
import urlparse

import mock
from nose.tools import *  # noqa (PEP8 asserts)

from website.addons.base.testing.base import OAuthAddonTestCaseMixin
from website.util import api_url_for, web_url_for

from tests.factories import AuthUserFactory


class OAuthAddonAuthViewsTestCaseMixin(OAuthAddonTestCaseMixin):

    @property
    def Provider(self):
        raise NotImplementedError()

    def test_oauth_start(self):
        url = api_url_for(
            'oauth_connect',
            service_name=self.ADDON_SHORT_NAME
        )
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.FOUND)
        redirect_url = urlparse.urlparse(res.location)
        redirect_params = urlparse.parse_qs(redirect_url.query)
        provider_url = urlparse.urlparse(self.Provider().auth_url)
        provider_params = urlparse.parse_qs(provider_url.query)
        for param, value in redirect_params.items():
            if param == 'state':  # state may change between calls
                continue
            assert_equal(value, provider_params[param])

    def test_oauth_finish(self):
        url = web_url_for(
            'oauth_callback',
            service_name=self.ADDON_SHORT_NAME
        )
        with mock.patch.object(self.Provider, 'auth_callback') as mock_callback:
            mock_callback.return_value = True
            res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        name, args, kwargs = mock_callback.mock_calls[0]
        assert_equal(kwargs['user']._id, self.user._id)

    def test_delete_external_account(self):
        url = api_url_for(
            'oauth_disconnect',
            external_account_id=self.external_account._id
        )
        res = self.app.delete(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        self.user.reload()
        for account in self.user.external_accounts:
            assert_not_equal(account._id, self.external_account._id)
        assert_false(self.user.external_accounts)

    def test_delete_external_account_not_owner(self):
        other_user = AuthUserFactory()
        url = api_url_for(
            'oauth_disconnect',
            external_account_id=self.external_account._id
        )
        res = self.app.delete(url, auth=other_user.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

class OAuthAddonConfigViewsTestCaseMixin(OAuthAddonTestCaseMixin):

    def test_import_auth(self):
        ea = self.ExternalAccountFactory()
        self.user.external_accounts.append(ea)
        self.user.save()

        node = ProjectFactory(creator=self.user)
        url = node.api_url_for('{0}_import_auth'.format(self.ADDON_SHORT_NAME))
        res = self.app.put_json(url, {
            'external_account_id': ea._id
        })
        assert_equal(res.status_code, http.OK)
        assert_in('result', res.json)
        node_settings = node.get_addon(self.ADDON_SHORT_NAME)
        assert_equal(node_settings.external_account._id, ea._id)

    def test_import_auth_invalid_account(self):
        pass

    def test_import_auth_cant_write_node(self):
        pass

    def test_set_config(self):
        pass

    def test_get_config(self):
        pass

    def test_account_list(self):
        pass

    def test_folder_list(self):
        pass

    def test_root_folder(self):
        pass

    def test_deauthorize_node(self):
        pass
