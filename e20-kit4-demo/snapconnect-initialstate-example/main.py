import os
import sys
import json
import binascii

from snapconnect import snap
from apy import ioloop_scheduler

import tornado.ioloop
from tornado import httpclient


# TODO: Replace these with values from your own Initial State account and buckets
# We want to map Initial State buckets to nodes
INITIAL_STATE_BUCKETS = {
    "xxxxxx": "enter unique Initial State bucket key here",
    "yyyyyy": "another unique Initial State bucket key here"
}
ACCESS_KEY = "enter unique access key here"
INITIAL_STATE_URL = "https://groker.initialstate.com/api/events"

SNAPCONNECT_POLL_INTERVAL = 10  # milliseconds

if sys.platform == "linux2":
    # E20 built-in bridge
    serial_conn = snap.SERIAL_TYPE_RS232
    serial_port = '/dev/snap1'
    snap_addr = None  # Intrinsic address on Exx gateways
    snap_license = None
else:
    # SS200 USB stick on Windows
    serial_conn = snap.SERIAL_TYPE_SNAPSTICK100
    serial_port = 0
    snap_addr = '\x00\x00\x20'  # SNAP Connect address from included License.dat
    cur_path = os.path.normpath(os.path.dirname(__file__))
    snap_license = os.path.join(cur_path, 'License.dat')


class InitialStateExample(object):
    def __init__(self):
        """
        Initializes an instance of InitialStateExample
        :return:
        """
        snap_rpc_funcs = {'status': self._on_status}

        # Create SNAP Connect instance. Note: we are using Tornado's scheduler.
        self.snapconnect = snap.Snap(
            license_file=snap_license,
            addr=snap_addr,
            scheduler=ioloop_scheduler.IOLoopScheduler(),
            funcs=snap_rpc_funcs
        )

        self.snapconnect.open_serial(serial_conn, serial_port)

        # Tell tornado to call SNAP connect internals periodically
        tornado.ioloop.PeriodicCallback(self.snapconnect.poll_internals, SNAPCONNECT_POLL_INTERVAL).start()

    def _on_status(self, batt, button_state, button_count):
        """
        Writes the various status values received from a node to Initial State
        :return: None
        """
        remote_addr = binascii.hexlify(self.snapconnect.rpc_source_addr())
        print batt, button_state, button_count

        try:
            headers = {
                "X-IS-AccessKey": ACCESS_KEY,
                "X-IS-BucketKey": INITIAL_STATE_BUCKETS[remote_addr],
                "Content-Type": "application/json"
            }
        except KeyError:
            print "Could not find SNAP address %s in INITIAL_STATE_BUCKETS" % remote_addr
            return

        jsonreq = [
            {"key": "batt", "value": int(batt)},
            {"key": "state", "value": int(button_state)},
            {"key": "count", "value": button_count}
        ]
        # Create a Tornado HTTPRequest
        request = httpclient.HTTPRequest(url=INITIAL_STATE_URL,
                                         method='POST',
                                         headers=headers,
                                         body=json.dumps(jsonreq))

        http_client = httpclient.AsyncHTTPClient()
        http_client.fetch(request, self._handle_request)

    @staticmethod
    def _handle_request(response):
        """
        Prints the response of a HTTPRequest
        :param response: HTTPRequest
        :return:
        """
        if response.error:
            print "Error:", response.error


def main():
    example = InitialStateExample()
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
