"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman  # ✅ add this line

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"
HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)
        talisman.force_https = False  # ✅ add this line
    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ADD YOUR TEST CASES HERE ...
    def test_get_account(self):
        """It should Read a single Account"""
        account = self._create_accounts(1)[0]
        resp = self.client.get(
            f"{BASE_URL}/{account.id}", content_type="application/json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["name"], account.name)


    def test_get_account_not_found(self):
        """It should not Read an Account that is not found"""
        # 1. Send a GET request for a non-existent account ID (0)
        resp = self.client.get(f"{BASE_URL}/0")

        # 2. Assert that the server responded with 404 NOT FOUND
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        
        # 3. Optional: Verify the error message in the JSON response
        data = resp.get_json()
        self.assertIn("could not be found", data["message"])

    def test_get_account_list(self):
        """It should Get a list of Accounts"""
        self._create_accounts(5)
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 5)
 
    def test_get_account_list_empty(self):
        """It should return an empty list when no Accounts exist"""
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 0)
 
    def test_get_account_list_checks_data(self):
        """It should return Accounts with correct field values"""
        created = self._create_accounts(3)
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 3)
        # Verify each created account appears in the response
        returned_ids = {account["id"] for account in data}
        for account in created:
            self.assertIn(account.id, returned_ids)


    ######################################################################
    #  U P D A T E   T E S T   C A S E S
    ######################################################################
 
    def test_update_account(self):
        """It should Update an existing Account"""
        # create an Account to update
        test_account = AccountFactory()
        resp = self.client.post(BASE_URL, json=test_account.serialize())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        # update the account
        new_account = resp.get_json()
        new_account["name"] = "Something Known"
        resp = self.client.put(f"{BASE_URL}/{new_account['id']}", json=new_account)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        updated_account = resp.get_json()
        self.assertEqual(updated_account["name"], "Something Known")
 
    def test_update_account_not_found(self):
        """It should return 404 when updating an Account that does not exist"""
        account = AccountFactory()
        resp = self.client.put(f"{BASE_URL}/0", json=account.serialize())
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        data = resp.get_json()
        self.assertIn("could not be found", data["message"])
 
    def test_update_account_persists(self):
        """It should persist changes so a subsequent GET reflects the update"""
        account = self._create_accounts(1)[0]
        # change multiple fields
        payload = account.serialize()
        payload["name"] = "Persisted Name"
        payload["email"] = "persisted@example.com"
        resp = self.client.put(f"{BASE_URL}/{account.id}", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # re-fetch and verify
        resp = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        fetched = resp.get_json()
        self.assertEqual(fetched["name"], "Persisted Name")
        self.assertEqual(fetched["email"], "persisted@example.com")
 
    def test_update_account_returns_updated_data(self):
        """It should return the full updated Account in the response body"""
        account = self._create_accounts(1)[0]
        payload = account.serialize()
        payload["name"] = "Return Check"
        payload["phone_number"] = "555-9999"
        resp = self.client.put(f"{BASE_URL}/{account.id}", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        # id must be unchanged
        self.assertEqual(data["id"], account.id)
        # updated fields must reflect new values
        self.assertEqual(data["name"], "Return Check")
        self.assertEqual(data["phone_number"], "555-9999")

    ######################################################################
    #  D E L E T E   T E S T   C A S E S
    ######################################################################
 
    def test_delete_account(self):
        """It should Delete an Account"""
        account = self._create_accounts(1)[0]
        resp = self.client.delete(f"{BASE_URL}/{account.id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
 
    def test_delete_account_not_found_is_idempotent(self):
        """It should return 204 even when deleting a non-existent Account"""
        # DELETE is idempotent by REST convention — deleting something that
        # does not exist should not raise a 404, it should silently succeed
        resp = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
 
    def test_delete_account_removes_from_list(self):
        """It should no longer appear in the account list after deletion"""
        accounts = self._create_accounts(3)
        target = accounts[0]
        resp = self.client.delete(f"{BASE_URL}/{target.id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        # list should now contain only 2 accounts
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 2)
        remaining_ids = {a["id"] for a in data}
        self.assertNotIn(target.id, remaining_ids)
 
    def test_delete_account_get_returns_404(self):
        """It should return 404 on GET after the Account has been deleted"""
        account = self._create_accounts(1)[0]
        # confirm it exists first
        resp = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # delete it
        resp = self.client.delete(f"{BASE_URL}/{account.id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        # now GET must return 404
        resp = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
 
    def test_delete_account_response_has_no_body(self):
        """It should return an empty body with the 204 response"""
        account = self._create_accounts(1)[0]
        resp = self.client.delete(f"{BASE_URL}/{account.id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(resp.data, b"")

    def test_method_not_allowed(self):
        """It should not allow an illegal HTTP method"""
        # Calling DELETE on /accounts (which only allows GET/POST)
        resp = self.client.delete(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_security_headers(self):
        """It should return security headers"""
        response = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': 'default-src \'self\'; object-src \'none\'',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        for key, value in headers.items():
            self.assertEqual(response.headers.get(key), value)