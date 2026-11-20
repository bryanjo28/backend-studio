import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from fastapi.testclient import TestClient
from api.app import create_app


class APITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.client = TestClient(create_app(self.root))

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def create(self):
        return self.client.post('/api/projects', json={'slug': 'test-video', 'title': 'Test'})

    def test_create_duplicate_and_persistence(self):
        self.assertEqual(self.create().status_code, 201)
        self.assertEqual(self.create().status_code, 409)
        self.assertEqual(self.client.get('/api/projects').json()[0]['slug'], 'test-video')
        self.assertTrue((self.root/'projects/test-video/story/shots.json').exists())

    def test_slug_and_unknown_config(self):
        self.assertEqual(self.client.post('/api/projects', json={'slug': '../escape', 'title': 'x'}).status_code, 422)
        self.create()
        self.assertEqual(self.client.patch('/api/projects/test-video/config', json={'voiceover': '../secret'}).status_code, 422)

    def test_upload_and_download(self):
        self.create()
        r = self.client.post('/api/projects/test-video/assets', data={'category':'characters'}, files={'file': ('hero.png', b'example-image', 'image/png')})
        self.assertEqual(r.status_code, 201)
        asset = r.json()
        self.assertEqual(self.client.get(asset['url']).content, b'example-image')
        self.assertEqual(len(self.client.get('/api/projects/test-video/assets').json()), 1)
        r = self.client.post('/api/projects/test-video/assets', files={'file': ('evil.js', b'code')})
        self.assertEqual(r.status_code, 422)

    def test_story_timing(self):
        self.create()
        story = {'duration':2, 'shots':[{'id':'s001','start':0,'end':2}]}
        self.assertEqual(self.client.put('/api/projects/test-video/story', json=story).status_code, 200)
        story['shots'][0]['start'] = 1
        self.assertEqual(self.client.put('/api/projects/test-video/story', json=story).status_code, 422)

    def test_jfif_all_image_categories(self):
        self.create()
        for category in ('characters','backgrounds','props'):
            response=self.client.post('/api/projects/test-video/assets',data={'category':category},files={'file':('image.JFIF',b'jpeg-fixture','image/jpeg')})
            self.assertEqual(response.status_code,201)
            asset=response.json()
            self.assertEqual(self.client.get(asset['url']).status_code,200)
            self.assertEqual(self.client.get(asset['url']).headers['content-type'],'image/jpeg')
            story={'duration':2,'shots':[{'id':'s001','start':0,'end':2,'visual':{'background':asset['path'],'foreground':asset['path']}}]}
            self.assertEqual(self.client.put('/api/projects/test-video/story',json=story).status_code,200)
        self.assertEqual(len(self.client.get('/api/projects/test-video/assets').json()),3)

    def test_empty_render_rejected(self):
        self.create()
        self.assertEqual(self.client.post('/api/projects/test-video/jobs', json={'kind':'preview'}).status_code, 409)

    def test_frontend_resources_and_empty_story(self):
        self.create()
        self.assertEqual(self.client.get('/api/projects/test-video/jobs').json(), [])
        detail = self.client.get('/api/projects/test-video').json()
        self.assertFalse(detail['has_scene'])
        self.assertFalse(detail['has_narration'])
        self.assertEqual(detail['title'], 'Test')
        self.assertEqual(self.client.get('/api/projects/test-video/story').status_code, 200)
        self.assertEqual(self.client.put('/api/projects/test-video/story', json={'duration':0,'shots':[]}).status_code, 200)

    def test_existing_artifacts_available_after_restart(self):
        self.create()
        video = self.root/'projects/test-video/build/video_silent.mp4'
        video.write_bytes(b'video')
        detail = self.client.get('/api/projects/test-video').json()
        self.assertTrue(detail['has_full_render'])
        self.assertTrue(any(url.endswith('video_silent.mp4') for url in detail['artifacts']))

    def test_private_file_not_served(self):
        self.create()
        p = self.root/'projects/test-video/input/secret.env'
        p.write_text('private')
        self.assertEqual(self.client.get('/api/projects/test-video/files/input/secret.env').status_code, 404)

    def test_delete_uploaded_asset_and_protect_scene_reference(self):
        self.create()
        asset=self.client.post('/api/projects/test-video/assets',data={'category':'backgrounds'},files={'file':('background.png',b'image','image/png')}).json()
        story={'duration':2,'shots':[{'id':'s001','start':0,'end':2,'visual':{'background':asset['path']}}]}
        self.client.put('/api/projects/test-video/story',json=story)
        self.assertEqual(self.client.delete('/api/projects/test-video/assets',params={'path':asset['path']}).status_code,409)
        self.client.put('/api/projects/test-video/story',json={'duration':0,'shots':[]})
        self.assertEqual(self.client.delete('/api/projects/test-video/assets',params={'path':asset['path']}).status_code,204)
        self.assertEqual(self.client.get(asset['url']).status_code,404)
        self.assertEqual(self.client.get('/api/projects/test-video/assets').json(),[])
        self.assertEqual(self.client.delete('/api/projects/test-video/assets',params={'path':'../config.json'}).status_code,404)
        self.assertEqual(self.client.delete('/api/projects/test-video/assets',params={'path':'config.json'}).status_code,404)

    def test_delete_narration_clears_assignment(self):
        self.create()
        asset=self.client.post('/api/projects/test-video/assets',data={'category':'voiceover'},files={'file':('voice.wav',b'audio','audio/wav')}).json()
        self.assertEqual(self.client.delete('/api/projects/test-video/assets',params={'path':asset['path']}).status_code,204)
        self.assertIsNone(self.client.get('/api/projects/test-video').json()['config']['voiceover'])

    def test_delete_during_render_is_rejected(self):
        self.create()
        asset=self.client.post('/api/projects/test-video/assets',files={'file':('a.png',b'image','image/png')}).json()
        self.client.patch('/api/projects/test-video/config',json={'renderer':'remotion'})
        self.client.put('/api/projects/test-video/story',json={'duration':2,'shots':[{'id':'s001','start':0,'end':2}]})
        with patch('concurrent.futures.ThreadPoolExecutor.submit'):
            self.client.post('/api/projects/test-video/jobs',json={'kind':'preview'})
            self.assertEqual(self.client.delete('/api/projects/test-video/assets',params={'path':asset['path']}).status_code,409)

    def test_remotion_readiness_and_dispatch(self):
        self.create()
        response = self.client.patch('/api/projects/test-video/config',json={'renderer':'remotion'})
        self.assertEqual(response.status_code,200)
        story={'duration':2,'shots':[{'id':'s001','start':0,'end':2,'visual':{'title':'Hello','motion':'push-in'}}]}
        self.assertEqual(self.client.put('/api/projects/test-video/story',json=story).status_code,200)
        self.assertTrue(self.client.get('/api/projects/test-video').json()['has_scene'])
        with patch('concurrent.futures.ThreadPoolExecutor.submit') as submit:
            response=self.client.post('/api/projects/test-video/jobs',json={'kind':'preview','end':2})
            self.assertEqual(response.status_code,202)
            command=submit.call_args.args[2]
            self.assertIn('render-remotion.mjs', ' '.join(command))

    def test_remotion_rejects_invalid_assets_and_motion(self):
        self.create()
        for visual in ({'background':'../../secret.png'},{'background':'https://example.com/a.png'},{'motion':'invalid'},{'dim':2}):
            story={'duration':2,'shots':[{'id':'s001','start':0,'end':2,'visual':visual}]}
            self.assertEqual(self.client.put('/api/projects/test-video/story',json=story).status_code,422)


if __name__ == '__main__':
    unittest.main()
