import unittest
from unittest.mock import patch

from backend import setup
from test_settings_api import request


class ImageAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_text_login_never_claims_image_or_vision_readiness_and_drops_private_metadata(self):
        account={'ready':True,'installed':True,'authenticated':True,'code':'ready',
                 'extra_credits_allowed':False,'private_identity':'never-return-this'}
        with patch('backend.antigravity.antigravity_status',return_value=account) as probe:
            status,value=await request('POST','/api/settings/image-access',headers={'x-setup-token':setup.TOKEN})
        self.assertEqual(status,200)
        probe.assert_called_once_with(refresh=True)
        self.assertTrue(value['account']['ready'])
        self.assertFalse(value['ready'])
        self.assertEqual(value['vision'],'not_verified')
        self.assertEqual(value['image_generation'],'not_configured')
        self.assertNotIn('never-return-this',str(value))

    async def test_probe_cannot_be_triggered_by_a_foreign_site_or_without_local_token(self):
        with patch('backend.antigravity.antigravity_status') as probe:
            for headers in ({},{'x-setup-token':setup.TOKEN,'origin':'https://foreign.example'}):
                status,_=await request('POST','/api/settings/image-access',headers=headers)
                self.assertEqual(status,403)
            probe.assert_not_called()
