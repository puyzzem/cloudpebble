import json
from cloudpebble_test import CloudpebbleTestCase
from django.core.urlresolvers import reverse
from ide.models.files import TestFile, ScreenshotSet, ScreenshotFile
from django.conf import settings
from django.test.utils import override_settings
from collections import Counter

__author__ = 'joe'


class TestsTests(CloudpebbleTestCase):
    """Tests for the Tests models"""

    def setUp(self):
        self.login()

    def add_and_run_tests(self, names=None):
        url = reverse('ide:create_test_file', args=[self.project_id])
        # Insert some tests
        names = ["mytest1", "mytest2"] if names is None else names
        tests = {test['id']: test for test in
                 (json.loads(self.client.post(url, {"name": name}).content)['file'] for name in names)}
        # Start a test session
        url = reverse('ide:post_test_session', args=[self.project_id])
        result = json.loads(self.client.post(url, {}).content)['data']
        # Check that the server returns a session containing all the tests we added
        run_tests = {run['test']['id']: run['test'] for run in result['runs']}
        for test_id, test in tests.iteritems():
            self.assertEqual(test['name'], run_tests[test['id']]['name'])
        return result

    def test_get_sessions(self):
        session_data = self.add_and_run_tests()
        url = reverse('ide:get_test_sessions', args=[self.project_id])
        sessions = json.loads(self.client.get(url).content)['data']
        # Check that the list of all sessions contains the session
        self.assertEqual(sessions[0]['id'], session_data['id'])

    def test_get_session(self):
        session_data = self.add_and_run_tests()
        url = reverse('ide:get_test_session', args=[self.project_id, session_data['id']])
        session = json.loads(self.client.get(url).content)['data']
        # Check that we can get the test session
        self.assertEqual(session['id'], session_data['id'])

    def test_run_multiple(self):
        session_data1 = self.add_and_run_tests(["mytest1", "mytest2"])
        session_data2 = self.add_and_run_tests(["mytest3", "mytest4"])
        # The second session should run all four tests
        self.assertEqual(len(session_data2['runs']), 4)

    def test_get_all_runs(self):
        # Add two tests and run, then add another two tests and run
        self.add_and_run_tests(["mytest1", "mytest2"])
        self.add_and_run_tests(["mytest3", "mytest4"])
        url = reverse('ide:get_test_runs', args=[self.project_id])

        # When we get all runs, we expect to have run the first two tests twice
        # and the second two tests once
        runs = json.loads(self.client.get(url).content)['data']
        self.assertDictEqual(dict(Counter(run['test']['name'] for run in runs)), {
            'mytest1': 2,
            'mytest2': 2,
            'mytest3': 1,
            'mytest4': 1
        })

    def test_get_runs_for_session(self):
        # Add two tests and run, then add another two tests and run
        session_data1 = self.add_and_run_tests(["mytest1", "mytest2"])
        session_data2 = self.add_and_run_tests(["mytest3", "mytest4"])
        url = reverse('ide:get_test_runs', args=[self.project_id])

        # We expect each session to run all previously added tests
        runs1 = json.loads(self.client.get(url, {'session': session_data1['id']}).content)['data']
        runs2 = json.loads(self.client.get(url, {'session': session_data2['id']}).content)['data']
        self.assertEqual(len(runs1), 2)
        self.assertEqual(len(runs2), 4)

    def test_get_runs_for_test(self):
        # Add two tests and run, then add another two tests and run
        session_data1 = self.add_and_run_tests(["mytest1", "mytest2"])
        session_data2 = self.add_and_run_tests(["mytest3", "mytest4"])
        url = reverse('ide:get_test_runs', args=[self.project_id])

        # Get details for mytest1, and mytest4. mytest1 should get run twice.
        runs1 = json.loads(self.client.get(url, {'test': session_data1['runs'][0]['test']['id']}).content)['data']
        runs2 = json.loads(self.client.get(url, {'test': session_data2['runs'][-1]['test']['id']}).content)['data']
        self.assertEqual(len(runs1), 2)
        self.assertEqual(len(runs2), 1)

    def test_list_tests(self):
        # Make a collection of test files
        post_url = reverse('ide:create_test_file', args=[self.project_id])
        ids = sorted([int(json.loads(self.client.post(post_url, {"name": "mytest"+str(x)}).content)['file']['id']) for x in range(5)])

        # Get the list test files
        url = reverse('ide:get_test_list', args=[self.project_id])
        response = sorted([int(t['id']) for t in json.loads(self.client.get(url).content)['tests']])

        # Check that all IDs are present
        self.assertEqual(ids == response)