__author__ = "Liam Gornshtein"

import pickle
import os
import threading
import hashlib
import time

class User:
    def __init__(self, username, password):
        self.username = username
        self.salt = os.urandom(16)
        self.password_hash = self._hash_password(password)

    def _hash_password(self, password):
        return hashlib.sha256(self.salt + password.encode()).hexdigest()

    def verify_password(self, password):
        return self.password_hash == hashlib.sha256(
            self.salt + password.encode()
        ).hexdigest()

class UsersManager:
    def __init__(self, file_name="users.pkl"):
        self.file_name = file_name
        self.users = {}
        self.lock = threading.Lock()
        self.Load()

    def Load(self):
        if not os.path.exists(self.file_name):
            print("No users file found, starting fresh")
            self.users = {}
            return

        try:
            with open(self.file_name, "rb") as f:
                self.users = pickle.load(f)
                print(f"Loaded users: {list(self.users.keys())}")
        except Exception as e:
            print("Failed loading users file:", e)
            self.users = {}

    def Save(self):
        try:
            with open(self.file_name, "wb") as f:
                pickle.dump(self.users, f)
        except Exception as e:
            print("Failed saving users:", e)

    def SaveUser(self, username, password):
        with self.lock:
            self.users[username] = User(username, password)
            self.Save()

    def IsUserExist(self, username):
        with self.lock:
            return username in self.users

    def IsPasswordOK(self, username, password):
        with self.lock:
            if username not in self.users:
                return False
            return self.users[username].verify_password(password)