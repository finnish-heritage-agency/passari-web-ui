def test_login_redirect(client):
    """
    Test that all requests redirect to the login page
    """
    URLS = [
        "/web-ui/overview/",
        "/web-ui/rq/create_sip",
        "/api/list-frozen-objects"
    ]

    for url in URLS:
        result = client.get(url)
        assert result.status_code == 302
        assert "/web-ui/login?" in result.headers["Location"]
