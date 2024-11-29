import pytest
import requests
import json

# @pytest.fixture
def test_sign_up():
    url = "http://localhost:3003/sign_up"
    data = {
        "firstname": "John",
        "lastname": "Doe",
        "email": "john.doe@example.com",
        "password": "password123",
        "username": "john_doe"
    }

    response = requests.post(url, json=data)
    result = response.json()

    print("result",result)
    assert result["success"] == True

test_sign_up()