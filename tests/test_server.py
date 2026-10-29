import http.client, json, threading, unittest
from http.server import ThreadingHTTPServer
from recommender.server import Handler


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path="/", body=None, headers=None, method="GET"):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        value = r.read()
        status = r.status
        heads = dict(r.getheaders())
        c.close()
        return status, value, heads

    def post(self, body, headers=None):
        return self.request(
            "/api/recommend",
            json.dumps(body),
            headers or {"Content-Type": "application/json"},
            "POST",
        )

    def test_static_headers(self):
        s, b, h = self.request()
        self.assertEqual(s, 200)
        self.assertIn(b"Paper trail", b)
        self.assertEqual(h["Cache-Control"], "no-store")
        self.assertIn("frame-ancestors 'none'", h["Content-Security-Policy"])

    def test_recommend(self):
        s, b, _ = self.post({"query": "graph neural networks"})
        self.assertEqual(s, 200)
        j = json.loads(b)
        self.assertIn("abstained", j)
        self.assertIn("not probabilities", j["notice"])

    def test_abstain(self):
        s, b, _ = self.post({"query": "zzzx qqqx"})
        self.assertEqual(s, 200)
        self.assertTrue(json.loads(b)["abstained"])

    def test_query_limits(self):
        for body in [
            {"query": "x" * 501},
            {"query": None},
            {"query": []},
            {"query": "graph", "limit": True},
            {"query": "graph", "threshold": 0},
        ]:
            self.assertEqual(self.post(body)[0], 400)

    def test_json_and_size(self):
        self.assertEqual(self.request("/api/recommend", "{}", {}, "POST")[0], 415)
        self.assertEqual(
            self.request(
                "/api/recommend",
                "x" * 8193,
                {"Content-Type": "application/json"},
                "POST",
            )[0],
            413,
        )
        self.assertEqual(
            self.request(
                "/api/recommend", "{", {"Content-Type": "application/json"}, "POST"
            )[0],
            400,
        )

    def test_path_boundary(self):
        for p in [
            "/../data/citation_labels.json",
            "/data/catalog.json",
            "/api/unknown",
            "/favicon.ico",
        ]:
            self.assertEqual(self.request(p)[0], 404)

    def test_origin_and_host(self):
        self.assertEqual(
            self.post(
                {"query": "graph"},
                {"Content-Type": "application/json", "Origin": "https://example.com"},
            )[0],
            403,
        )
        self.assertEqual(self.request(headers={"Host": "example.com"})[0], 403)

    def test_catalog_count(self):
        s, b, _ = self.request("/api/catalog")
        self.assertEqual(s, 200)
        j = json.loads(b)
        self.assertGreater(j["count"], 0)
        self.assertLessEqual(len(j["examples"]), 8)


if __name__ == "__main__":
    unittest.main()
