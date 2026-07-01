# coding: utf-8
# @File        : assets.py
# @Author      : NanMing
# @Date        : 2026/6/11 13:46
# @Description : Extracts and validates GitHub search asset indicators.

import re
from ipaddress import ip_address
from pathlib import Path

import tldextract

from core.database import setting_col


BASE_PATH = Path("server")
ASSET_RULE_SETTING_KEY = "asset_rule"
DEFAULT_ASSET_RULES = [
    {
        "_id": "domain",
        "name": "Domain",
        "type": "domain",
        "pattern": r"(?!\-)(?:[a-zA-Z\d\-]{0,62}[a-zA-Z\d]\.){1,126}(?!\d+)[a-zA-Z\d]{1,63}",
        "enabled": True,
        "builtin": True,
    },
    {
        "_id": "email",
        "name": "Email",
        "type": "email",
        "pattern": r"[\w!#$%&'*+/=?^_`{|}~-]+(?:\.[\w!#$%&'*+/=?^_`{|}~-]+)*@(?:[\w](?:[\w-]*[\w])?\.)+[\w](?:[\w-]*[\w])?",
        "enabled": True,
        "builtin": True,
    },
    {
        "_id": "ip",
        "name": "IP",
        "type": "ip",
        "pattern": r"(\d+\.\d+\.\d+\.\d+)",
        "enabled": True,
        "builtin": True,
    },
]


def default_asset_rules():
    return [dict(rule) for rule in DEFAULT_ASSET_RULES]


def merge_asset_rules(stored_rules):
    merged = {rule["_id"]: dict(rule) for rule in DEFAULT_ASSET_RULES}
    for rule in stored_rules:
        rule = dict(rule)
        rule_id = rule.get("_id")
        if not rule_id:
            continue
        if rule.get("deleted"):
            merged.pop(rule_id, None)
            continue
        if rule_id in merged:
            merged[rule_id].update(rule)
            merged[rule_id]["builtin"] = True
        else:
            rule["builtin"] = bool(rule.get("builtin", False))
            merged[rule_id] = rule
    return list(merged.values())


def _normalize_match(match):
    if isinstance(match, tuple):
        for item in match:
            if item:
                return str(item)
        return ""
    return str(match)


class AssetExtractor:
    def __init__(self, tld_extract, rules_provider=None):
        self.tld_extract = tld_extract
        self.rules_provider = rules_provider or load_asset_rules

    def get_domain(self, target):
        result = self.tld_extract(target)
        if bool(len(result.suffix)) and bool(len(result.domain)):
            return "{}.{}".format(result.domain, result.suffix)
        return False

    def is_ip(self, ip):
        try:
            ip_address(ip)
            return True
        except ValueError:
            return False

    def is_valid_asset(self, asset_type, value):
        if asset_type == "ip":
            return self.is_ip(value)
        if asset_type == "domain":
            return bool(self.get_domain(value))
        if asset_type == "email":
            return "@" in value and bool(self.get_domain(value.split("@")[-1]))
        return True

    def get_affect_assets(self, code):
        code = str(code)
        affect = []
        for rule in self.rules_provider():
            if not rule.get("enabled", True):
                continue
            asset_type = str(rule.get("type") or "").strip().lower()
            pattern = rule.get("pattern")
            if not asset_type or not pattern:
                continue
            try:
                matches = re.findall(pattern, code)
            except re.error:
                continue
            values = sorted({sanitize_asset_value(_normalize_match(match)) for match in matches})
            values = [value for value in values if value]
            if len(values) > 100:
                continue
            for asset in values:
                if not self.is_valid_asset(asset_type, asset):
                    continue
                affect.append({"type": asset_type, "value": asset})
        return affect


def sanitize_asset_value(value):
    return str(value).replace("'", "").replace('"', "").replace("`", "").lower()


def load_asset_rules():
    rules = list(setting_col.find({"key": ASSET_RULE_SETTING_KEY}, {"key": 0}).sort("type", 1))
    return merge_asset_rules(rules)


def default_extractor():
    return AssetExtractor(tldextract.TLDExtract(cache_dir=str(BASE_PATH / ".tldextract-cache")))
