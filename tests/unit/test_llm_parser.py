from devlens.analysis.llm.parser import parse_llm_response


def test_parse_llm_response_extracts_json_from_wrapped_text() -> None:
    result = parse_llm_response(
        "Here you go "
        '{"patterns":["recursion"],"optimization_assessment":"fine","critique":"ok","confidence":0.8}'
    )

    assert result.patterns == ["recursion"]
    assert result.critique == "ok"
    assert result.confidence == 0.8
