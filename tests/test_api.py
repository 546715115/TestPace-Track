# tests/test_api.py
import pytest
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index(client):
    response = client.get('/')
    assert response.status_code == 200

def test_get_versions(client):
    response = client.get('/api/versions')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True