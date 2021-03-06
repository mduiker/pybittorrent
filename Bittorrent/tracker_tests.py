import unittest
from unittest import TestCase
from unittest.mock import Mock

import tracker
from bencode import bdecode_file

from urllib.parse import urlencode

def TEST_DEFAULTS():
    return {"info_hash": "TESTINFOHASH",
            "peer_id": "TESTPEERID",
            "port": 8001,
            "uploaded": 0,
            "downloaded": 1000000,
            "left": 2000000,
            "compact": 0,
            "no_peer_id": 0,
            "event": "started"}

def send_test_params(params):
    from io import BytesIO
    params_str = urlencode(params, doseq=True)
    mock_tracker = Mock()
    mock_tracker.path = "http://localhost:8000/announce?" + params_str
    mock_tracker.client_address = ("127.0.0.1", 8001)
    output_file = BytesIO()
    tracker.handle_GET(mock_tracker, output_file)
    output_file.seek(0)
    return bdecode_file(output_file)

class TestAnnounceUrl(TestCase):

    def assert_dict_entry_type(self, dictionary, name, expected_type, expected_value=None):
        value = dictionary.get(name)
        self.assertTrue(type(value) == expected_type)
        if expected_value != None:
            self.assertTrue(value == expected_value)

    def test_response_keys(self):
        """tests that the response contains some mandatory keys"""
        #clear the peers list. 
        tracker.info_hash_to_peers.clear()
        #send a request, check these keys are in it. 
        result = send_test_params(TEST_DEFAULTS())
        self.assert_dict_entry_type(result, b"interval", int)
        self.assert_dict_entry_type(result, b"complete", int)
        self.assert_dict_entry_type(result, b"incomplete", int)
        self.assert_dict_entry_type(result, b"tracker id", bytes)

    def test_started(self):
        """tests that sending a request gets you added to the list of peers on the tracker"""
        #clear the peers list
        tracker.info_hash_to_peers.clear()

        #send a test started request
        result = send_test_params(TEST_DEFAULTS())

        #check we get no peers back
        self.assertTrue(result[b"peers"] == [])

        #check we are added to the list of peers
        self.assertTrue(tracker.info_hash_to_peers.get("TESTINFOHASH").get("TESTPEERID"))

    def test_peer_info(self):
        """tests that a second request from a different peer ID gets you the first peer back"""
        #clear the peers list. 
        tracker.info_hash_to_peers.clear()

        #send first request from one peer
        send_test_params(TEST_DEFAULTS())

        #send second params with a different peer_id to get the first peer back
        params = TEST_DEFAULTS()
        params[b"peer_id"] = "TESTPEERID2"
        result = send_test_params(params)
        
        #check we got the first peer back
        self.assertTrue(len(result[b"peers"]) == 1)
        peer = result[b"peers"][0]
        self.assertTrue(peer)
    
        #check we got the right info back
        self.assertTrue(peer[b"peer id"] == b"TESTPEERID")
        self.assertTrue(peer[b"ip"] == b"127.0.0.1")
        self.assertTrue(peer[b"port"] == 8001)
        self.assertTrue(len(peer) == 3)

    def test_numpeers(self):
        """tests getting the right number of peers back"""
        #clear the peers list. 
        tracker.info_hash_to_peers.clear()
        #add 49 peers
        for i in range(49):
            params = TEST_DEFAULTS()
            params["peer_id"] += str(i)
            send_test_params(params)

        #send without a started event
        params = TEST_DEFAULTS()
        del params["event"]
        result = send_test_params(params)

        #check we got 49 peers back
        peers = result[b"peers"]
        self.assertTrue(len(peers) == 49)

        #add another peer
        params = TEST_DEFAULTS()
        params["peer_id"] += str(50)
        send_test_params(params)

        #send without a started event
        params = TEST_DEFAULTS()
        del params["event"]
        result = send_test_params(params)

        #check we got 50 peers back
        peers = result[b"peers"]
        self.assertTrue(len(peers) == 50)

        #set numwant to 25, & check we get 25 peers back
        params = TEST_DEFAULTS()
        params["numwant"] = 25
        del params["event"]
        result = send_test_params(params)
        peers = result[b"peers"]
        self.assertTrue(len(peers) == 25)

    def test_num_complete(self):
        """tests the number of seeders and leechers"""
        tracker.info_hash_to_peers.clear()

        #send an initial request. This adds one peer to the list. 
        send_test_params(TEST_DEFAULTS())
        #send another request without an event. check the counts
        params = TEST_DEFAULTS()
        del params["event"]
        result = send_test_params(params)
        incomplete = result[b"incomplete"]
        complete = result[b"complete"]
        self.assertTrue(incomplete == 1)
        self.assertTrue(complete == 0)

        #send another request, saying we finished the torrent. Check the counts
        params = TEST_DEFAULTS()
        params["event"] = "complete"
        result = send_test_params(params)
        incomplete = result[b"incomplete"]
        complete = result[b"complete"]
        self.assertTrue(incomplete == 0)
        self.assertTrue(complete == 1)

        #send another request, another client started a download. Check the counts.. 
        params = TEST_DEFAULTS()
        params["peer_id"] = "TESTPEERID2"
        result = send_test_params(params)
        incomplete = result[b"incomplete"]
        complete = result[b"complete"]
        self.assertTrue(incomplete == 1)
        self.assertTrue(complete == 1)        

        #and completed it.. 
        params = TEST_DEFAULTS()
        params["peer_id"] = "TESTPEERID2"
        params["event"] = "complete"
        result = send_test_params(params)
        incomplete = result[b"incomplete"]
        complete = result[b"complete"]
        self.assertTrue(incomplete == 0)
        self.assertTrue(complete == 2)        


if __name__ == "__main__":
    unittest.main()
