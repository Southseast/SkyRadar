# coding: utf-8
# @File        : assets.py
# @Author      : NanMing
# @Date        : 2026/6/11 13:46
# @Description : Extracts and validates GitHub search asset indicators.

import re
from ipaddress import ip_address
from pathlib import Path

import tldextract


BASE_PATH = Path("server")


class AssetExtractor:
    def __init__(self, tld_extract):
        self.tld_extract = tld_extract

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

    def get_affect_assets(self, code):
        code = str(code)
        affect = []
        domain_pattern = r"(?!\-)(?:[a-zA-Z\d\-]{0,62}[a-zA-Z\d]\.){1,126}(?!\d+)[a-zA-Z\d]{1,63}"
        ip_pattern = r"(\d+\.\d+\.\d+\.\d+)"
        email_pattern = r"[\w!#$%&'*+/=?^_`{|}~-]+(?:\.[\w!#$%&'*+/=?^_`{|}~-]+)*@(?:[\w](?:[\w-]*[\w])?\.)+[\w](?:[\w-]*[\w])?"
        affect_assets = {
            "domain": list(set(re.findall(domain_pattern, code))),
            "email": list(set(re.findall(email_pattern, code))),
            "ip": list(set(re.findall(ip_pattern, code))),
        }
        for assets in affect_assets.keys():
            if len(affect_assets.get(assets)) > 100:
                affect_assets[assets] = []
                continue
            for asset in affect_assets.get(assets):
                if assets == "ip" and not self.is_ip(asset):
                    continue
                if assets == "domain" and not self.get_domain(asset):
                    continue
                if assets == "email" and not self.get_domain(asset.split("@")[-1]):
                    continue
                affect.append({"type": assets, "value": asset.replace("'", "").replace('"', "").replace("`", "").lower()})
        return affect


def default_extractor():
    return AssetExtractor(tldextract.TLDExtract(cache_dir=str(BASE_PATH / ".tldextract-cache")))
