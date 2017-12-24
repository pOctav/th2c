import mock

from tornado import gen
from tornado.iostream import StreamClosedError
from tornado.testing import AsyncTestCase, gen_test
from tornado.httpclient import HTTPRequest

from th2c.client import AsyncHTTP2Client
from th2c.connection import HTTP2ClientConnection
from th2c.stream import HTTP2ClientStream
from th2c.exceptions import RequestTimeout


class HTTP2ClientConnectionTestCase(AsyncTestCase):
    tcp_client = mock.MagicMock()

    def test_one_instance_per_host_port_secure(self):
        # same host, port, security flag
        conn1 = HTTP2ClientConnection('host', 1234, False, self.tcp_client, self.io_loop)
        conn2 = HTTP2ClientConnection('host', 1234, False, self.tcp_client, self.io_loop)
        self.assertEqual(id(conn1), id(conn2))

        # different parameter combinations
        conn1 = HTTP2ClientConnection('host', 1234, False, self.tcp_client, self.io_loop)
        conn2 = HTTP2ClientConnection('host', 1234, True, self.tcp_client, self.io_loop)
        self.assertNotEqual(id(conn1), id(conn2))

        conn1 = HTTP2ClientConnection('host', 1234, False, self.tcp_client, self.io_loop)
        conn2 = HTTP2ClientConnection('host2', 1234, False, self.tcp_client, self.io_loop)
        self.assertNotEqual(id(conn1), id(conn2))

        conn1 = HTTP2ClientConnection('host', 1234, False, self.tcp_client, self.io_loop)
        conn2 = HTTP2ClientConnection('host', 12345, False, self.tcp_client, self.io_loop)
        self.assertNotEqual(id(conn1), id(conn2))

    @gen_test
    def test_connect_timeout(self):
        connection_closed = mock.MagicMock()

        connection = HTTP2ClientConnection(
            'host', 1234, False, self.tcp_client, self.io_loop,
            connect_timeout=1,
            on_connection_closed=connection_closed
        )

        connection.connect()

        self.assertNotEqual(connection._connect_timeout_t, None)

        yield gen.sleep(1.1)

        connection_closed.assert_called_once()
        self.assertEqual(connection.timed_out, True)

    def test_connection_cleanup(self):
        connection_closed = mock.MagicMock()

        connection = HTTP2ClientConnection(
            'host', 1234, False, self.tcp_client, self.io_loop,
            on_connection_closed=connection_closed
        )

        connection.connect()

        self.assertEqual(connection.closed, False)

        exc = Exception('some error')
        connection.close(exc)

        connection_closed.assert_called_once_with(exc)
        self.assertEqual(connection.is_ready, False)
        self.assertEqual(connection.is_connected, False)
        self.assertEqual(connection.closed, True)

    def test_io_stream_error_propagates(self):
        connection_closed = mock.MagicMock()
        connection_ready = mock.MagicMock()

        connection = HTTP2ClientConnection(
            'host', 1234, False, self.tcp_client, self.io_loop,
            on_connection_closed=connection_closed,
            on_connection_ready=connection_ready,
        )

        connection.connect()

        io_stream = mock.MagicMock()
        io_stream.write.side_effect = StreamClosedError

        connection.on_connect(io_stream)

        self.assertEqual(connection.is_connected, True)

        exc = Exception('testing')
        io_stream.error = exc
        connection.on_close()

        connection_closed.assert_called_once_with(exc)

    def test_write_future_error(self):
        connection_closed = mock.MagicMock()
        connection_ready = mock.MagicMock()

        connection = HTTP2ClientConnection(
            'host', 1234, False, self.tcp_client, self.io_loop,
            on_connection_closed=connection_closed,
            on_connection_ready=connection_ready,
        )

        connection.connect()

        exc = Exception('testing write future error')

        write_future = mock.MagicMock()
        write_future.exc_info.return_value = (Exception, exc, None)

        io_stream = mock.MagicMock()

        connection.on_connect(io_stream)

        self.assertEqual(connection.is_connected, True)

        connection.on_write_done(write_future)

        connection_closed.assert_called_once_with(exc)
