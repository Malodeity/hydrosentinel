"""The public dashboard's AI endpoints have no login, so they are limited per visitor address."""
from unittest.mock import patch

from app.rate_limit import _PUBLIC_MAX_CALLS
from app.routes import ai as ai_routes


def test_a_visitor_is_stopped_after_the_hourly_limit_and_no_further_openai_call_is_made(client, sample_wsa):
    with patch.object(ai_routes, "call_openai", return_value="ok") as mocked:
        for _ in range(_PUBLIC_MAX_CALLS):
            assert client.get(f"/ai/wsa/{sample_wsa.id}/summary").status_code == 200
        blocked = client.get(f"/ai/wsa/{sample_wsa.id}/summary")
    assert blocked.status_code == 429
    assert mocked.call_count == _PUBLIC_MAX_CALLS  # the blocked request never reached OpenAI


def test_the_limit_is_shared_across_the_public_ai_endpoints(client, sample_wsa):
    # otherwise a script could dodge the limit by rotating between endpoints
    with patch.object(ai_routes, "call_openai", return_value="ok"):
        for _ in range(_PUBLIC_MAX_CALLS):
            client.get(f"/ai/wsa/{sample_wsa.id}/risk-explanation")
        assert client.get(f"/ai/wsa/{sample_wsa.id}/comparison").status_code == 429
