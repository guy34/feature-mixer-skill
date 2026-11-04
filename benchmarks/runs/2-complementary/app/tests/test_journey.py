"""Journey and dependency tests across all slices."""

import ast
import os
import sys

from tests.helpers import AppTestCase

PKG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fileshare")


class JourneyTests(AppTestCase):
    def test_upload_preview_share_open_revoke(self):
        """features: M01, M02, M04, M07, M08, M09, M10
        acceptance: AC13
        expect: register, upload, list, preview, share with a password, recipient opens and downloads, owner revokes, link dies
        level: journey"""
        owner = self.client()
        self.assertEqual(owner.register("owner").status, 201)
        fid = owner.upload("report.csv", b"a,b\n1,2\n").json()["id"]
        self.assertEqual([f["id"] for f in owner.request("GET", "/api/files").json()["files"]], [fid])
        self.assertEqual(owner.request("GET", f"/api/files/{fid}/preview").json()["first_lines"], ["a,b", "1,2"])
        link = owner.request("POST", f"/api/files/{fid}/links",
                             json_body={"expires_in_hours": 48, "password": "pw-1234"}).json()
        recipient = self.client()
        self.assertEqual(recipient.request("GET", link["url"]).status, 200)  # the share page
        pw = {"X-Link-Password": "pw-1234"}
        shared = recipient.request("GET", f"/api/share/{link['token']}", headers=pw).json()
        self.assertEqual(shared["preview"]["first_lines"], ["a,b", "1,2"])
        self.assertEqual(recipient.request("GET", f"/api/share/{link['token']}/content", headers=pw).body, b"a,b\n1,2\n")
        self.assertEqual(owner.request("DELETE", f"/api/links/{link['token']}").status, 204)
        self.assertEqual(recipient.request("GET", f"/api/share/{link['token']}", headers=pw).status, 404)


class DependencyTests(AppTestCase):
    def test_app_imports_only_the_standard_library(self):
        """features: M01, M04, M07
        expect: every import in the fileshare package is the standard library or the package itself
        level: dependency"""
        stdlib = set(sys.stdlib_module_names)
        found = set()
        for base, _, names in os.walk(PKG):
            for n in names:
                if n.endswith(".py"):
                    tree = ast.parse(open(os.path.join(base, n), encoding="utf-8").read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            found |= {a.name.split(".")[0] for a in node.names}
                        elif isinstance(node, ast.ImportFrom) and node.level == 0:
                            found.add(node.module.split(".")[0])
        self.assertEqual(sorted(found - stdlib - {"fileshare"}), [])
