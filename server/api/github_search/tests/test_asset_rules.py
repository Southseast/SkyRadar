# coding: utf-8
# @File        : test_asset_rules.py
# @Author      : NanMing
# @Date        : 2026/7/1
# @Description : Tests configurable GitHub search asset extraction rules.

from api.github_search.assets import AssetExtractor, merge_asset_rules


class FakeTldExtract:
    def __call__(self, target):
        parts = str(target).split(".")
        if len(parts) >= 2:
            return type("ExtractResult", (), {"domain": parts[-2], "suffix": parts[-1]})()
        return type("ExtractResult", (), {"domain": "", "suffix": ""})()


def test_asset_extractor_uses_configurable_rules():
    extractor = AssetExtractor(
        FakeTldExtract(),
        rules_provider=lambda: [
            {
                "name": "AWS Access Key",
                "type": "secret",
                "pattern": r"AKIA[0-9A-Z]{16}",
                "enabled": True,
            },
            {
                "name": "Disabled email",
                "type": "email",
                "pattern": r"ops@example\.com",
                "enabled": False,
            },
        ],
    )

    assert extractor.get_affect_assets("key = AKIA1234567890ABCDEF ops@example.com") == [
        {"type": "secret", "value": "akia1234567890abcdef"}
    ]


def test_asset_extractor_keeps_builtin_validation_for_ip_and_email():
    extractor = AssetExtractor(
        FakeTldExtract(),
        rules_provider=lambda: [
            {"name": "IP", "type": "ip", "pattern": r"(\d+\.\d+\.\d+\.\d+)", "enabled": True},
            {
                "name": "Email",
                "type": "email",
                "pattern": r"[\w.-]+@[\w.-]+",
                "enabled": True,
            },
        ],
    )

    assert extractor.get_affect_assets("999.999.999.999 admin@example.com") == [
        {"type": "email", "value": "admin@example.com"}
    ]


def test_merge_asset_rules_excludes_deleted_builtin_rules():
    rules = merge_asset_rules(
        [
            {
                "_id": "email",
                "name": "Email",
                "type": "email",
                "pattern": "@",
                "enabled": False,
                "builtin": True,
                "deleted": True,
            }
        ]
    )

    assert {rule["_id"] for rule in rules} == {"domain", "ip"}
