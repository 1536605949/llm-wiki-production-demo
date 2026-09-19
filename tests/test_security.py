from llmwiki.service import LLMWikiService

def test_path_traversal_rejected(tmp_path):
    svc = LLMWikiService(str(tmp_path / "wiki"))
    svc.init()
    try:
        svc.ws.wiki_path("../../etc/passwd")
        assert False
    except ValueError:
        pass
