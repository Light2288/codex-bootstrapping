#!/usr/bin/env python3
"""Read and update generic Keychain passwords without placing secrets in argv."""

from __future__ import print_function

import argparse
import ctypes
import sys


ERR_SEC_ITEM_NOT_FOUND = -25300
NOT_FOUND_EXIT = 44


class KeychainError(RuntimeError):
    """Raised when the macOS Keychain APIs cannot complete an operation."""


class KeychainNotFound(KeychainError):
    """Raised when no matching generic password exists."""


class SecurityKeychain(object):
    """Minimal ctypes wrapper for generic-password Keychain Services calls."""

    def __init__(self):
        if sys.platform != "darwin":
            raise KeychainError("macOS Security.framework is unavailable")
        try:
            self.security = ctypes.CDLL(
                "/System/Library/Frameworks/Security.framework/Security"
            )
            self.core_foundation = ctypes.CDLL(
                "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
            )
        except OSError as error:
            raise KeychainError("could not load macOS Security.framework: {0}".format(error))
        self._configure_functions()

    def _configure_functions(self):
        self.security.SecKeychainFindGenericPassword.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_char_p,
            ctypes.c_uint32,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self.security.SecKeychainFindGenericPassword.restype = ctypes.c_int32
        self.security.SecKeychainAddGenericPassword.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_char_p,
            ctypes.c_uint32,
            ctypes.c_char_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self.security.SecKeychainAddGenericPassword.restype = ctypes.c_int32
        self.security.SecKeychainItemModifyAttributesAndData.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        self.security.SecKeychainItemModifyAttributesAndData.restype = ctypes.c_int32
        self.security.SecKeychainItemDelete.argtypes = [ctypes.c_void_p]
        self.security.SecKeychainItemDelete.restype = ctypes.c_int32
        self.security.SecKeychainItemFreeContent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.security.SecKeychainItemFreeContent.restype = ctypes.c_int32
        self.core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
        self.core_foundation.CFRelease.restype = None

    @staticmethod
    def _encoded(value):
        return value.encode("utf-8")

    def _raise_for_status(self, status, operation):
        if status == ERR_SEC_ITEM_NOT_FOUND:
            raise KeychainNotFound("Keychain item was not found")
        if status != 0:
            raise KeychainError("{0} failed with OSStatus {1}".format(operation, status))

    def _find(self, service, account):
        encoded_service = self._encoded(service)
        encoded_account = self._encoded(account)
        password_length = ctypes.c_uint32()
        password_data = ctypes.c_void_p()
        item = ctypes.c_void_p()
        status = self.security.SecKeychainFindGenericPassword(
            None,
            len(encoded_service),
            encoded_service,
            len(encoded_account),
            encoded_account,
            ctypes.byref(password_length),
            ctypes.byref(password_data),
            ctypes.byref(item),
        )
        self._raise_for_status(status, "Keychain lookup")
        try:
            password = ctypes.string_at(password_data, password_length.value)
        finally:
            self.security.SecKeychainItemFreeContent(None, password_data)
        return password, item

    def _release_item(self, item):
        if item and item.value:
            self.core_foundation.CFRelease(item)

    def get(self, service, account):
        password, item = self._find(service, account)
        try:
            return password
        finally:
            self._release_item(item)

    def set(self, service, account, password):
        encoded_service = self._encoded(service)
        encoded_account = self._encoded(account)
        password_buffer = ctypes.create_string_buffer(password)
        password_pointer = ctypes.cast(password_buffer, ctypes.c_void_p)
        try:
            _ignored, item = self._find(service, account)
        except KeychainNotFound:
            item = ctypes.c_void_p()
            status = self.security.SecKeychainAddGenericPassword(
                None,
                len(encoded_service),
                encoded_service,
                len(encoded_account),
                encoded_account,
                len(password),
                password_pointer,
                ctypes.byref(item),
            )
            try:
                self._raise_for_status(status, "Keychain create")
            finally:
                self._release_item(item)
            return
        try:
            status = self.security.SecKeychainItemModifyAttributesAndData(
                item,
                None,
                len(password),
                password_pointer,
            )
            self._raise_for_status(status, "Keychain update")
        finally:
            self._release_item(item)

    def delete(self, service, account):
        _ignored, item = self._find(service, account)
        try:
            status = self.security.SecKeychainItemDelete(item)
            self._raise_for_status(status, "Keychain delete")
        finally:
            self._release_item(item)


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("check", "get", "set", "delete"))
    parser.add_argument("--service", required=True)
    parser.add_argument("--account", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    arguments = parse_arguments(argv)
    keychain = SecurityKeychain()
    if arguments.operation == "check":
        return 0
    if arguments.operation == "get":
        sys.stdout.buffer.write(keychain.get(arguments.service, arguments.account))
        return 0
    if arguments.operation == "set":
        password = sys.stdin.buffer.read()
        if not password:
            raise KeychainError("credential input was empty")
        keychain.set(arguments.service, arguments.account, password)
        return 0
    keychain.delete(arguments.service, arguments.account)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeychainNotFound as error:
        print("Keychain helper failed: {0}".format(error), file=sys.stderr)
        sys.exit(NOT_FOUND_EXIT)
    except KeychainError as error:
        print("Keychain helper failed: {0}".format(error), file=sys.stderr)
        sys.exit(1)
