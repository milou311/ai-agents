from aaos.identity import get_identity_manager, IdentityManager
from pathlib import Path
import json


def test_introduce():
    im = get_identity_manager()
    text = im.introduce()
    assert im.identity.name in text
    assert im.identity.version in text


def test_self_model_has_tools():
    im = get_identity_manager()
    model = im.self_model(include_runtime=True)
    assert "name" in model
    assert "capabilities" in model
    assert "tools" in model["capabilities"]
    assert "whoami" in model["capabilities"]["tools"] or len(model["capabilities"]["tools"]) >= 1


def test_custom_identity_file(tmp_path: Path):
    p = tmp_path / "id.json"
    p.write_text(
        json.dumps({"name": "Ops", "name_en": "Ops", "version": "5.2"}),
        encoding="utf-8",
    )
    im = IdentityManager(config_path=p)
    assert im.identity.name == "Ops"
    assert im.identity.version == "5.2"
    assert "Ops" in im.introduce("en")
