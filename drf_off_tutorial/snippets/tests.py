import json
from rest_framework.test import APITestCase
from django.contrib.auth import authenticate
from rest_framework.test import APIRequestFactory
from django.test import TestCase
from snippets.models import Snippet
from snippets.serializers import SnippetSerializer
from rest_framework import status
from rest_framework.reverse import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory


class SnippetApiTestCase(APITestCase):
    def setUp(self):
        self.user_1 = User.objects.create(username='user_1_username')
        self.user_2 = User.objects.create(username='user_2_username')
        self.snippet_1 = Snippet.objects.create(title='Snippet_1_title', code='qwerty', owner=self.user_1)
        self.snippet_2 = Snippet.objects.create(title='Snippet_2_title', code='qwerty', owner=self.user_2)

    def test_get_all(self):
        url = reverse('snippet-list')
        request = APIRequestFactory().get(url)
        response = self.client.get(url)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        snippets = Snippet.objects.all().order_by('-created')
        serializer = SnippetSerializer(snippets, many=True, context={"request": request})
        self.assertEquals(serializer.data, response.data['results'])

    def test_get_one(self):
        snippet = Snippet.objects.last()
        url = reverse('snippet-detail', args=str(snippet.id))
        request = APIRequestFactory().get(url)
        response = self.client.get(url)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        serializer = SnippetSerializer(snippet, context={"request": request})
        self.assertEquals(serializer.data, response.data)

    def test_create_logged_in(self):
        url = reverse('snippet-list')
        count = len(Snippet.objects.all())
        self.client.force_login(self.user_1)
        json_data = json.dumps({"title": "new_snippet", "code": "print('qwerty')", "highlighted": "print('qwerty')"})
        request = APIRequestFactory().post(url, json_data, content_type='application/json')
        response = self.client.post(url, json_data, content_type='application/json')
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertEquals((count + 1), len(Snippet.objects.all()))
        last_snippet = self.client.get('/snippets/').data['results'][-1]
        self.assertEquals(Snippet.objects.last().owner, self.user_1)
        self.assertEquals(SnippetSerializer(Snippet.objects.first(), context={"request": request}).data, last_snippet)

    def test_create_not_logged(self):
        url = reverse('snippet-list')
        json_data = json.dumps({"title": "new_snippet", "code": "print('qwerty')", "highlighted": "print('qwerty')"})
        response = self.client.post(url, json_data, content_type='application/json')
        self.assertContains(response, 'Authentication credentials were not provided.', status_code=403)

    def test_update_logged_in(self):
        snippet = Snippet.objects.get(pk=self.snippet_1.id)
        url = reverse('snippet-detail', args=str(snippet.id))
        self.client.force_login(self.user_1)
        resp_without_data = self.client.put(url)
        self.assertContains(resp_without_data, "This field is required.", status_code=status.HTTP_400_BAD_REQUEST)
        json_data = json.dumps({"code": "print('qwerty')", "highlighted": "print('qwerty')"})
        request = APIRequestFactory().put(url, json_data, content_type="application/json")
        resp_with_data = self.client.put(url, json_data, content_type="application/json")
        self.assertEquals(resp_with_data.status_code, status.HTTP_200_OK)
        snippet.refresh_from_db()
        snippet_data = SnippetSerializer(snippet, context={"request": request}).data
        response_data = self.client.get(url).data
        self.assertEquals(snippet_data, response_data)

    def test_update_not_logged(self):
        snippet = Snippet.objects.get(pk=self.snippet_1.id)
        url = reverse('snippet-detail', args=str(snippet.id))
        json_data = json.dumps({"code": "print('qwerty')", "highlighted": "print('qwerty')"})
        resp_with_data = self.client.put(url, json_data, content_type="application/json")
        self.assertContains(resp_with_data, 'Authentication credentials were not provided.', status_code=403)

    def test_update_not_owner(self):
        snippet = Snippet.objects.get(pk=self.snippet_1.id)
        url = reverse('snippet-detail', args=str(snippet.id))
        self.client.force_login(self.user_2)
        json_data = json.dumps({"code": "print('qwerty')", "highlighted": "print('qwerty')"})
        resp_with_data = self.client.put(url, json_data, content_type="application/json")
        self.assertContains(resp_with_data, 'You do not have permission to perform this action.', status_code=403)

    def test_partial_update(self):
        snippet = Snippet.objects.get(pk=self.snippet_1.pk)
        self.client.force_login(self.user_1)
        url = reverse('snippet-detail', args=str(snippet.id))
        json_data = json.dumps({"title": "Snippet_updated"})
        request = APIRequestFactory().patch(url, json_data, content_type="application/json")
        resp = self.client.patch(url, json_data, content_type="application/json")
        self.assertEquals(resp.status_code, 200)
        snippet.refresh_from_db()
        snippet_data = SnippetSerializer(snippet, context={"request": request}).data
        response_data = self.client.get(url).data
        self.assertEquals(snippet_data, response_data)

    def test_partial_update_not_owner(self):
        snippet = Snippet.objects.get(pk=self.snippet_1.pk)
        self.client.force_login(self.user_2)
        url = reverse('snippet-detail', args=str(snippet.id))
        json_data = json.dumps({"title": "Snippet_updated"})
        resp = self.client.patch(url, json_data, content_type="application/json")
        self.assertContains(resp, 'You do not have permission to perform this action.', status_code=403)

    def test_delete(self):
        snippet = Snippet.objects.get(pk=self.snippet_1.id)
        url = reverse('snippet-detail', args=str(snippet.id))
        snippets_before = Snippet.objects.count()
        self.client.force_login(self.user_1)
        self.client.delete(url)
        snippets_after = Snippet.objects.count()
        self.assertEquals(snippets_before, snippets_after + 1)

    def test_pagination(self):
        for i in range(15):
            Snippet.objects.create(owner=self.user_1)
        url = reverse('snippet-list')
        response = self.client.get(url)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data['results']), 10)

    def test_highlight(self):
        snippet = Snippet.objects.get(pk=self.snippet_1.id)
        url = reverse('snippet-highlight', args=str(snippet.id))
        response = self.client.get(url)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(snippet.highlighted, response.data)


