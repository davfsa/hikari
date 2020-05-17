#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright © Nekokatt 2019-2020
#
# This file is part of Hikari.
#
# Hikari is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hikari is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Hikari. If not, see <https://www.gnu.org/licenses/>.
import http

import pytest

from hikari import errors
from hikari.internal import codes


class TestHikariError:
    def test_repr(self):
        class ErrorImpl(errors.HikariError):
            def __str__(self):
                return "program go boom!"

        inst = ErrorImpl()

        assert repr(inst) == "ErrorImpl('program go boom!')"


class TestGatewayError:
    def test_init(self):
        err = errors.GatewayError("boom")
        assert err.reason == "boom"

    def test_str(self):
        err = errors.GatewayError("boom")
        assert str(err) == "boom"


class TestGatewayClientClosedError:
    def test_init(self):
        err = errors.GatewayClientClosedError("blah")
        assert err.reason == "blah"


class TestGatewayConnectionClosedError:
    def test_init_valid_reason(self):
        err = errors.GatewayServerClosedConnectionError(codes.GatewayCloseCode.UNKNOWN_OPCODE, "foo")
        assert err.close_code == codes.GatewayCloseCode.UNKNOWN_OPCODE.value
        assert err.reason == "foo"

    def test_init_valid_close_code(self):
        err = errors.GatewayServerClosedConnectionError(codes.GatewayCloseCode.UNKNOWN_OPCODE)
        assert err.close_code == codes.GatewayCloseCode.UNKNOWN_OPCODE.value
        assert err.reason.endswith(f" ({codes.GatewayCloseCode.UNKNOWN_OPCODE.name})")

    def test_init_invalid_close_code(self):
        err = errors.GatewayServerClosedConnectionError(69)
        assert err.close_code == 69
        assert err.reason.endswith(" (69)")

    def test_init_no_close_code(self):
        err = errors.GatewayServerClosedConnectionError()
        assert err.close_code is None
        assert err.reason.endswith(" (no reason)")


class TestGatewayInvalidTokenError:
    def test_init(self):
        err = errors.GatewayInvalidTokenError()
        assert err.close_code == codes.GatewayCloseCode.AUTHENTICATION_FAILED


class TestGatewayInvalidSessionError:
    @pytest.mark.parametrize("can_resume", (True, False))
    def test_init(self, can_resume):
        err = errors.GatewayInvalidSessionError(can_resume)
        assert err.close_code is None


class TestGatewayMustReconnectError:
    def test_init(self):
        err = errors.GatewayMustReconnectError()
        assert err.close_code is None


class TestGatewayNeedsShardingError:
    def test_init(self):
        err = errors.GatewayNeedsShardingError()
        assert err.close_code == codes.GatewayCloseCode.SHARDING_REQUIRED


class TestGatewayZombiedError:
    def test_init(self):
        err = errors.GatewayZombiedError()
        assert err.reason.startswith("No heartbeat was received")


@pytest.mark.parametrize(
    ("type", "expected_status", "expected_status_name"),
    [
        (errors.BadRequest, http.HTTPStatus.BAD_REQUEST, "Bad Request"),
        (errors.Unauthorized, http.HTTPStatus.UNAUTHORIZED, "Unauthorized"),
        (errors.Forbidden, http.HTTPStatus.FORBIDDEN, "Forbidden"),
        (errors.NotFound, http.HTTPStatus.NOT_FOUND, "Not Found"),
        (
            lambda u, h, pl: errors.ClientHTTPErrorResponse(u, http.HTTPStatus.TOO_MANY_REQUESTS, h, pl),
            http.HTTPStatus.TOO_MANY_REQUESTS,
            "Too Many Requests",
        ),
        (
            lambda u, h, pl: errors.ServerHTTPErrorResponse(u, http.HTTPStatus.INTERNAL_SERVER_ERROR, h, pl),
            http.HTTPStatus.INTERNAL_SERVER_ERROR,
            "Internal Server Error",
        ),
        (
            lambda u, h, pl: errors.HTTPErrorResponse(u, http.HTTPStatus.CONTINUE, h, pl),
            http.HTTPStatus.CONTINUE,
            "Continue",
        ),
    ],
)
class TestHTTPClientErrors:
    def test_init(self, type, expected_status, expected_status_name):
        ex = type("http://foo.bar/api/v69/nice", {"foo": "bar"}, b"body")

        assert ex.status == expected_status
        assert ex.url == "http://foo.bar/api/v69/nice"
        assert ex.headers == {"foo": "bar"}
        assert ex.raw_body == b"body"

    def test_str_if_unicode_bytestring(self, type, expected_status, expected_status_name):
        ex = type("http://foo.bar/api/v69/nice", {"foo": "bar"}, b"body")

        assert str(ex) == f"{expected_status} {expected_status_name}: body"

    def test_str_if_not_unicode_bytestring(self, type, expected_status, expected_status_name):
        ex = type("http://foo.bar/api/v69/nice", {"foo": "bar"}, b"\x1f\x0f\xff\xff\xff")

        assert str(ex) == f"{expected_status} {expected_status_name}: b'\\x1f\\x0f\\xff\\xff\\xff'"

    def test_str_if_payload(self, type, expected_status, expected_status_name):
        ex = type("http://foo.bar/api/v69/nice", {"foo": "bar"}, {"code": 0, "message": "you broke it"})

        assert str(ex) == f"{expected_status} {expected_status_name}: {{'code': 0, 'message': 'you broke it'}}"